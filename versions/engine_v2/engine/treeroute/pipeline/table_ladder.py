"""The forecast ladder of a table run (SPEC_TABLE_MODE.md 3.9): TableLadder.

Owner rulings I1 (event leads 183 and 365 days, R10), H2-H5 and U1 (the owner rulings files, sections H, I and U).
The ORDER is the grid ladder's (pipeline/ladder.py: the lead-0 contract, then per lead its fit-cut objects, the H2
guard on its guard-cut bank, the persistence inputs, the lock, the test pass; then the ladder table), on a table's
rows: each lead L reads ITS OWN table (the lead-L file: features that already end before the issue date, U1), so
nothing is moved to an issue step (no io.apply.features_at_issue_step) and there is no own-history block.
Per lead L:
  1  the lead's vault (labels.rows.RowLabelView.for_lead: rows absent from the lead's file have no label at L;
     departure table_absent_rows) and the lead's pool (its file's features);
  2  FitContext(L, FIT): the lagtrain bank at the lead's fit cut, c (R23:lead=L), R36 tolerances, the donor-row
     median; the lead's GLS weight model only when the pinned arm is weighted (R25, R29);
  3  H2: FitContext(L, GUARD): the bank refit at the lead's guard cut; no guard row inside its label window;
  4  the N2 guard (R29) on the lead's guard surface: train rows present at L with a valid label dated after lead 0's
     guard cut up to the lead's fit cut (issued at or after the lead's guard cut: check_inner_score_rows); a guard
     row absent from the lead's file refuses (the grid reading of H4); S1; the neighbour pass on the guard bank at the
     pinned point (horizon = the lead's guard cut; fallback median from the guard bank's donor rows; c = the lead's
     fit-cut c, D63 a); the guard's baseline is the donor-row median of the guard bank's donor rows, the same
     object as the pass's fallback median (owner ruling V1; the pinned link's trees-off is printed beside);
     layer.decide.forecast_adoption (D86); the guard rows saved;
  5  persistence inputs (R31, D54 a) BEFORE the lead's lock: persistence = the newest label of the same package unit
     before the row's issue day (RowLabelView.last_label_before); damped persistence from (visit, previous visit)
     pairs per package unit with the event-month season key judged pair by pair (U-2 / D88: report.metrics'
     arithmetic) and a baseline-only normal (owner item O17);
  6  the lead's lock (labels.vault.lock_lead_adoption), before any of its test labels opens;
  7  the test pass: test rows present at L (absent ones left out, saved flagged and counted: H4), S1, the neighbour pass
     on the lead's fit-cut bank at the pinned point for layer.arms.lead_arms plus the identity trees-off (printed
     beside); baselines predict-zero, the donor-row median, persistence and damped persistence; every row saved. A
     lead whose guard fails adopts the donor-row median (base__donor_median; owner ruling V1), the baseline its guard
     used.
The lead-0 contract (G-PLUMB 'lead 0 = nowcast'): the lead path at L = 0 on lead_0's table reproduces the nowcast:
the pool equals the nowcast pool, the bank's donor rows equal the nowcast bank's inputs (so the bank is not refitted),
c, the tolerances, the donor-row median and (a weighted pin) the GLS model equal, and every assembled column equals the
nowcast's saved column. The ladder table: every lead on the rows common to all leads, each lead's verdict against the
donor-row median (signed R34) under the nowcast's band.
The twin-disagreement alarm (owner ruling AE; pipeline/ladder.py's reading): at every lead, with the pinned arm and its
twin, the lead's guard surface as the reference; the twin is routed alone, in a separate neighbour pass, on the guard
rows and on the kept test rows only when the lead can be active (its guard passed, the twin simpler); its guard MAE is
compared with the baseline the guard used (the donor-row median under V1). The alarm is locked after the lead's lock
and before its test labels open, which now open after the routing (H4 and S1 save their rows after that). Issue
batches are the calendar month of each row's issue day (target day - lead).
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.9; pipeline/ladder.py (the order, the records, the readings);
# APP_PLAN.md R10, R11, R29, R31 ("fitted on (visit, previous visit) pairs with the same season-key rule applied to
# each pair"), R34, R35; OWNER_RULINGS_2026-10-05.md H2-H5; OWNER_RULINGS_2026-10-06.md I1, U1, V1 (:103).

import datetime as _dt
import json
import time
from contextlib import ExitStack
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind, Link
from treeroute.errors import RefusedError
from treeroute.fit.context import FitContext
from treeroute.fit.tables import TreeAnswerStore
from treeroute.fit.weights import weight_model_for_cut, weight_model_record
from treeroute.labels.vault import LEAD_ADOPTION_FILE, LOCK_SUFFIX, lock_lead_adoption
from treeroute.layer import arms as LA
from treeroute.layer import decide as LD
from treeroute.layer.links import c_for_cut_against_plan, clip_to_legal
from treeroute.report import metrics as M
from treeroute.runs.atomic import dumps, read_json

from treeroute.layer import alarm as LAL

from . import alarm_pass as AP
from . import ladder as GL
from . import passes as P
from . import record as REC
from . import stages as ST
from .passes import _write_parquet_once
from .table_passes import REFERENCE_COLUMN, V1_RULE, years_of_days
from .table_router import NeighbourPass, PassPart

LADDER_DIR = GL.LADDER_DIR
PHASE_CONTRACT, PHASE_LEAD, PHASE_TABLE = GL.PHASE_CONTRACT, GL.PHASE_LEAD, GL.PHASE_TABLE
CONTRACT_FILE, LADDER_TABLE, LADDER_RECORD = GL.CONTRACT_FILE, GL.LADDER_TABLE, GL.LADDER_RECORD
GUARD_PREDS, LEAD_RECORD, ISSUE_MISSING_ROWS = GL.GUARD_PREDS, GL.LEAD_RECORD, GL.ISSUE_MISSING_ROWS
ISSUE_FLAG, ISSUE_REASON_ABSENT = GL.ISSUE_FLAG, "issue_row_absent_from_the_lead_file"
O17_NORMAL = ("damped persistence's normal (owner item O17; the neighbour kind has no normal, R15): the mean of the "
              "package unit's labels at or before the lead's fit cut in the row's event month, else the unit's "
              "all-season mean, else the donor-row mean (R15's fallback chain, used for this baseline only)")
PAIRS_RULE = ("R31 events: phi per package unit from (visit, previous visit) pairs, the previous visit being the unit's "
              "newest visit dated before the visit's issue day, both labels at or before the lead's fit cut; the U-2 / "
              "D88 rule pair by pair on the event-month key (report.metrics PHI_SHARED_MIN_LABELS / "
              "PHI_SEPARATE_MIN_LABELS); phi = the through-origin slope clipped to [0, 1], 0 when undefined")


class TableLadderRefusal(RefusedError):
    """The table ladder refused (fail loudly)."""


def table_lead_plan(derived: Mapping[str, Any]) -> Tuple[Tuple[int, ...], Mapping[int, Any]]:
    """(R10's leads in days, ascending; {lead: R11 cut pair}, lead 0 included). Refuses a lead plan not in days, a
    lead without its cut pair, a lead-0 contract that is off."""
    lp = derived["R10"].value
    unit = getattr(getattr(lp, "lead_unit", None), "value", getattr(lp, "lead_unit", None))
    if unit != "days":
        raise TableLadderRefusal("R10", "a table run's leads are in days (events), got %r" % (unit,))
    if not bool(getattr(lp, "contract_lead_zero", False)):
        raise TableLadderRefusal("R10", "the lead plan has no lead-0 contract; lead 0 always runs as the contract")
    leads = tuple(sorted(int(x) for x in lp.leads))
    cuts = {int(k): v for k, v in derived["R11"].value.items()}
    missing = [L for L in (0,) + leads if L not in cuts]
    if missing:
        raise TableLadderRefusal("R11", "leads %s have no cut pair in derived.json" % missing)
    return leads, cuts


def table_phase_names(derived: Mapping[str, Any]) -> List[str]:
    """The ladder's phases (pipeline/ladder.py's names): the lead-0 contract, one per lead, the ladder table."""
    leads, _ = table_lead_plan(derived)
    return [PHASE_CONTRACT] + [PHASE_LEAD % L for L in leads] + [PHASE_TABLE]


def _event_month(days: np.ndarray) -> np.ndarray:
    """R2's event-month key of day ordinals."""
    distinct, inverse = np.unique(np.asarray(days, dtype=np.int64), return_inverse=True)
    months = np.array([_dt.date.fromordinal(int(d)).month for d in distinct.tolist()], dtype=np.int64)
    return months[np.asarray(inverse).reshape(-1)]


def _json(obj: Any) -> Any:
    return json.loads(dumps(M._json_safe(obj)))


class TableLadder(object):
    """The ladder of one table run (module docstring). state: the TableRunState after the nowcast."""

    def __init__(self, state: Any) -> None:
        self.s = state
        self.p = state.p
        self.leads, self.cuts = table_lead_plan(state.derived)
        self.longest = max(self.leads) if self.leads else None
        self.folder = self.p.folder / LADDER_DIR
        self.pinned, self.pin_point = LD.pin_of(state.adoption)
        self.data = self.p.table
        self._alarm: Optional[Dict[str, Any]] = None          # owner ruling AE: the current lead's guard-side facts

    def _log(self, msg: str) -> None:
        self.s._beat("ladder", msg)

    def _lead_dir(self, L: int):
        d = self.folder / ("lead_%d" % L)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _beside_links(self) -> Tuple[Any, ...]:
        """The identity trees-off, routed and saved beside the pinned link's (owner ruling V1: printed beside, no
        longer the decline target of the neighbour kind; the saved columns stay as they were)."""
        return () if self.pinned.link == Link.IDENTITY else (Link.IDENTITY,)

    # ------------------------------------------------------------------ the fit-cut objects of one lead
    def _objects(self, L: int, stack: ExitStack) -> Dict[str, Any]:
        s, p = self.s, self.p
        lt = self.data.leads[L]
        vault = s.labels if L == 0 else s.labels.for_lead(lt.present, L)
        pool = stack.enter_context(s.open_lead_pool("pool_lead_%d" % L, L))
        ctx_fit = FitContext(s.derived, p.split_sets, s.vg.grid, vault, pool, s.lists, L, CutKind.FIT)
        s.extra_contexts.append(("ctx_fit_lead_%d" % L, ctx_fit))
        donor = ctx_fit.donor_rows("bank")
        if L == 0:
            bank, store = s.bank_fit, s.store_fit
        else:
            self._log("lead %d: lagtrain bank at the lead's fit cut %d (%d groups x %d trees)"
                      % (L, self.cuts[L].fit_cut, len(s.groups), p.trees_per_group))
            bank = s.fit_bank(donor, "lead-%d" % L)
            s._check_bank(bank, "lead-%d" % L)
            store = stack.enter_context(TreeAnswerStore.from_bank(bank, ST.row_group_of(s.vg), p.temp_dir, p.registry,
                                                                  echo=p.log))
        c = c_for_cut_against_plan(donor, s.derived) if Link.LOG_C in s.links else None
        tol, tol_record = ST.guard_tolerances(donor, s.links, c, s.ub, p.smoke)
        median = M.baseline_donor_median(donor)
        weights = None
        if self.pinned.weighting is LA.Weighting.GLS:
            ctx_g = ctx_fit.for_lead(L, CutKind.GUARD)
            s.extra_contexts.append(("ctx_guard_gls_lead_%d" % L, ctx_g))
            weights = weight_model_for_cut(ctx_fit, ctx_g, store, bank.tree_group, blocks=p.blocks,
                                           matrix_dir=p.temp_dir, echo=p.log)
            if L > 0:
                from treeroute.derive.derived import derived_entry

                REC.write_once_or_same(self._lead_dir(L) / "gls_weight_model.json",
                                       derived_entry(weight_model_record(weights)))
        rec = {"bank": {"fingerprint": bank.manifest.bank_fingerprint, "trees": len(bank.trees),
                        "cut": int(bank.manifest.cut), "max_label_time": int(bank.manifest.max_label_time),
                        "donor_rows": int(np.asarray(donor.y).size), "donor_row_key_hash": donor.row_key_hash},
               "c": c, "tolerances": tol_record, "donor_median": median,
               "rows_absent_at_lead": int((~lt.present).sum()),
               "corrector_coverage": getattr(s, "corrector_coverage", {}).get("fit-cut" if L == 0 else "lead-%d" % L),
               "gls_weight_model": ("refit at the lead's cut (the pinned arm is weighted)" if weights is not None
                                    else "not refit (the pinned arm is unweighted, R25)")}
        return {"lead": L, "lt": lt, "vault": vault, "pool": pool, "ctx_fit": ctx_fit, "donor": donor, "bank": bank,
                "store": store, "c": c, "tol": tol, "tol_record": tol_record, "median": median, "weights": weights,
                "record": rec}

    # ------------------------------------------------------------------ the lead-0 contract
    def contract(self) -> Dict[str, Any]:
        s, p = self.s, self.p
        t0 = time.time()
        self._log("lead-0 contract: the ladder's lead path at lead 0 against the nowcast")
        cut0 = self.cuts[0]
        if (int(cut0.fit_cut), int(cut0.guard_cut)) != (int(s.cuts.fit_cut), int(s.cuts.guard_cut)):
            raise TableLadderRefusal("R11", "the lead-0 cut pair %s is not the nowcast's %s" % (cut0, s.cuts))
        t_keys, t_units, t_days = s.test_rows()
        keep, s1 = s.leave_out_score_context(REC.S1_TEST_PASS, s.ctx_fit, 0, t_keys, t_units, t_days, save=False)
        if s1 is not None:
            t_keys, t_units, t_days = t_keys[keep], t_units[keep], t_days[keep]
        now = M.read_rows(p.folder / REC.TEST_PREDS)
        if not (np.array_equal(now[M.COL_UNIT].to_numpy(dtype=object), np.asarray(t_units, dtype=object))
                and np.array_equal(now[M.COL_TIME].to_numpy(dtype=np.int64), np.asarray(t_days, dtype=np.int64))):
            raise TableLadderRefusal("G-PLUMB", "lead-0 contract: the nowcast's saved rows are not the ladder's test rows")
        with ExitStack() as stack:
            o = self._objects(0, stack)
            n_rows, bad_tree, bad_ctx = GL.Ladder._pool_gap(self._gap_host(), o["pool"], s.pool)
            if bad_tree or bad_ctx:
                raise TableLadderRefusal("G-PLUMB", "lead-0 contract: the lead-0 pool differs from the nowcast pool on %d "
                                         "rows (tree features) and %d rows (context)" % (bad_tree, bad_ctx))
            ref = s.donor_fit
            d = o["donor"]
            checks = {"row_key_hash": d.row_key_hash == ref.row_key_hash, "grid_rows": GL._same_array(d.grid_rows, ref.grid_rows),
                      "times": GL._same_array(d.times, ref.times), "y": GL._same_array(d.y, ref.y),
                      "X": GL._same_features(d.X, ref.X), "c": GL._same_float(o["c"], s.c),
                      "median": GL._same_float(o["median"], s.median_fit),
                      "tolerances": _json(o["tol_record"]) == _json(s.tol_record)}
            if o["weights"] is not None:
                from treeroute.derive.derived import derived_entry

                checks["gls_weight_model"] = s.weights is not None and \
                    _json(derived_entry(weight_model_record(o["weights"]))) == _json(derived_entry(weight_model_record(s.weights)))
            bad = sorted(k for k, ok in checks.items() if not ok)
            if bad:
                raise TableLadderRefusal("G-PLUMB", "lead-0 contract: the lead path's %s differ(s) from the nowcast's" % bad)
            arms, placebos, pre, routed = self._route(o, t_keys, [self.pinned], "lead 0 contract", o["ctx_fit"],
                                                      o["store"], o["bank"], o["weights"], o["median"], o["donor"])
            baselines = s.common_baselines(t_keys.size, o["median"])
            frame = M.assemble_rows(s.row_keys(t_keys, t_units, t_days), 0, t_days,
                                    now[M.COL_Y].to_numpy(dtype=np.float64), np.full(t_keys.size, np.nan), arms,
                                    placebos, pre, baselines, s.legal)
            o = None
        differ = [c for c in frame.columns if c not in now.columns
                  or not frame[c].reset_index(drop=True).equals(now[c].reset_index(drop=True))]
        if differ:
            raise TableLadderRefusal("G-PLUMB", "lead-0 contract FAILED: the lead path's columns %s differ from the "
                                     "nowcast's saved columns" % differ)
        rec = {"lead": 0, "pinned": LA.arm_name(self.pinned),
               "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
               "rows": int(t_keys.size), "pool_rows_compared": n_rows, "pool_identical": True,
               "fits_identical": sorted(checks), "columns_identical": [str(c) for c in frame.columns],
               "bank": GL.READINGS["lead0_bank"], "router": _json(routed.records)}
        self.folder.mkdir(parents=True, exist_ok=True)
        REC.write_once_or_same(self.folder / CONTRACT_FILE, _json(rec))
        self._log("lead-0 contract holds (%d saved columns of %d rows) in %.1f s"
                  % (len(frame.columns), t_keys.size, time.time() - t0))
        return rec

    def _gap_host(self) -> Any:
        """A host for pipeline/ladder.py Ladder._pool_gap (its body reads s.vg.grid and n only)."""
        from types import SimpleNamespace

        return SimpleNamespace(s=self.s, n=1)

    # ------------------------------------------------------------------ a neighbour pass at the pinned point
    def _route(self, o: Mapping[str, Any], keys: np.ndarray, tree_arms: Sequence[Any], what: str, ctx: Any, store: Any,
               bank: Any, weights: Any, median_donor_median: float, fallback_donor: Any,
               tol: Optional[Mapping[Any, float]] = None) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray],
                                                                   Dict[str, np.ndarray], Any]:
        s = self.s
        part = PassPart(name="all", score_index=np.arange(keys.size, dtype=np.int64), c=o["c"], model=weights,
                        fallback_donor=fallback_donor)
        npass = NeighbourPass(s, what, ctx, store, bank.tree_group, int(o["lead"]), o["lt"], keys, [part],
                              tol if tol is not None else o["tol"])
        routed = npass.route(list(tree_arms), self.pin_point, extra_trees_off=self._beside_links())
        self.last_pass = npass
        arms, placebos, pre = {}, {}, {}
        for a in tree_arms:
            nm = LA.arm_name(a)
            v = ST.inverse(routed.predictions[nm][:, 0], a.link, o["c"], s.ub)
            (placebos if a.tool is LA.Tool.PLACEBO_CORRECTOR else arms)[nm] = clip_to_legal(v, s.legal, False)[0]
            pre[nm] = v
        for Lk in dict.fromkeys((self.pinned.link,) + self._beside_links()):
            nm = LA.arm_name(LA.trees_off_of(Lk))
            v = ST.inverse(routed.trees_off[Lk], Lk, o["c"], s.ub)
            arms[nm] = clip_to_legal(v, s.legal, False)[0]
            pre[nm] = v
        return arms, placebos, pre, routed

    # ------------------------------------------------------------------ the guard (H2, R29)
    def _guard(self, o: Mapping[str, Any], stack: ExitStack) -> Tuple[Any, Dict[str, Any]]:
        s, p = self.s, self.p
        L = int(o["lead"])
        fit_cut = int(self.cuts[L].fit_cut)
        ctx = FitContext(s.derived, p.split_sets, s.vg.grid, o["vault"], o["pool"], s.lists, L, CutKind.GUARD)
        s.extra_contexts.append(("ctx_guard_lead_%d" % L, ctx))
        self._log("lead %d: guard bank refit at the lead's guard cut %d (owner ruling H2)" % (L, ctx.cut))
        donor_g = ctx.donor_rows("bank_guard")
        bank_g = s.fit_bank(donor_g, "lead-%d guard-cut" % L)
        s._check_bank(bank_g, "lead-%d guard-cut" % L)
        store_g = stack.enter_context(TreeAnswerStore.from_bank(bank_g, ST.row_group_of(s.vg), p.temp_dir, p.registry,
                                                                echo=p.log))
        first = int(s.cuts.guard_cut) + 1
        vu, vt, vv = s.labels.validity(first, fit_cut)
        pos = np.asarray([s.row_pos[str(u)] for u in vu.tolist()], dtype=np.int64)
        train = ~np.asarray(self.data.is_test, dtype=bool)[pos]
        pick = vv & train
        absent = pick & ~np.asarray(o["lt"].present, dtype=bool)[pos]
        if absent.any():
            raise TableLadderRefusal("H4", "lead %d: %d guard-surface row(s) are absent from the lead's file (first %s); "
                                     "H4 leaves out TEST rows only, and a guard row is never scored without its "
                                     "features (the grid reading, READINGS guard_issue_rows)"
                                     % (L, int(absent.sum()), vu[absent][:5].tolist()),
                                     fix="owner item: rule whether H4 also leaves such guard rows out")
        if not pick.any():
            raise TableLadderRefusal("R29", "lead %d: the guard surface holds no train row with a valid label" % L)
        issue = np.asarray(o["lt"].issue_day, dtype=np.int64)[pos[pick]]
        ctx.check_inner_score_rows(issue)
        keep, s1 = s.leave_out_score_context("lead %d guard" % L, ctx, L, pos[pick], vu[pick], vt[pick])
        if s1 is not None:
            idx = np.flatnonzero(pick)
            pick = pick.copy()
            pick[idx[~keep]] = False
        surface = o["vault"].decision_surface(vu[pick], vt[pick], fit_cut, purpose="lead_%d_guard" % L)
        g_keys = pos[pick]
        times = np.asarray(surface.times, dtype=np.int64)
        y = np.asarray(surface.y, dtype=np.float64)
        bank_newest = int(bank_g.manifest.max_label_time)
        in_window = int((times <= bank_newest).sum())
        if in_window:
            raise TableLadderRefusal("H2", "lead %d: %d guard row(s) are dated at or before the guard bank's newest label "
                                     "%d" % (L, in_window, bank_newest))
        arms, _, pre, routed = self._route(o, g_keys, [self.pinned], "lead %d guard" % L, ctx, store_g, bank_g,
                                           o["weights"], o["median"], donor_g)
        pools_file = self.last_pass.save_pools(self._lead_dir(L), "guard")
        name = LA.arm_name(self.pinned)
        off = LA.arm_name(LA.trees_off_of(self.pinned.link))
        mae_pin, mae_off = LD.surface_mae(y, arms[name]), LD.surface_mae(y, arms[off])
        v1 = s.decline_to_donor_median()
        base_rec: Dict[str, Any] = {}
        base_v = None
        if v1:
            # owner ruling V1: the guard's baseline is the pass's fallback median (the guard bank's donor rows).
            # The check (REVIEW v1 item 4): the pass has one part; its stored median is recomputed from the pass's own
            # fallback rows; and those rows' units, oldest and newest label days and cut are the ones the guard bank's
            # manifest recorded when the bank was fitted (fit/bank.py BankManifest), so the baseline and the guard's
            # trees come from the same rows
            parts = self.last_pass.parts
            base = float(parts[0].median)
            fd = parts[0].fallback_donor
            man = bank_g.manifest
            fd_times = np.asarray(fd.times, dtype=np.int64)
            fd_units = sorted(set(str(u) for u in np.asarray(fd.unit_ids).tolist()))
            same = (len(parts) == 1 and base == float(M.baseline_donor_median(fd)) and int(fd.cut) == int(man.cut)
                    and len(fd_units) == int(man.n_units) and int(fd_times.min()) == int(man.min_label_time)
                    and int(fd_times.max()) == int(man.max_label_time))
            if not same:
                raise TableLadderRefusal("G-PLUMB", "lead %d guard: the pass's fallback median is not the donor-row "
                                         "median of the rows the guard bank was fitted on (one part; median, cut, "
                                         "unit count and label days against the bank manifest; owner ruling V1)" % L)
            base_v = clip_to_legal(np.full(y.size, base), s.legal, False)[0]
            mae_base = LD.surface_mae(y, base_v)
            base_rec = {"baseline_column": REFERENCE_COLUMN, "baseline_value": base, "baseline_mae": mae_base,
                        "baseline_donor_rows": int(np.asarray(donor_g.y).size), "baseline_rule": V1_RULE}
        la = LD.forecast_adoption(s.adoption, L, mae_pin, base_rec["baseline_mae"] if v1 else mae_off, self.longest)
        units = np.asarray(surface.unit_ids, dtype=object)
        frame = pd.DataFrame({"unit": units, "group": [s.unit_group[str(u)] for u in units.tolist()],
                              "time": times, "issue": times - L, "y": y})
        for nm in sorted(arms):
            frame[M.ARM_PREFIX + nm] = arms[nm]
            frame[M.PRE_PREFIX + nm] = pre[nm]
        if v1:
            frame[REFERENCE_COLUMN] = base_v
        _write_parquet_once(frame, self._lead_dir(L) / GUARD_PREDS)
        rec = {"surface_rows": int(y.size), "score_days": [first, fit_cut], "fit_cut": fit_cut,
               "guard_cut": int(ctx.cut), "surface_sha256": str(surface.sha256), "pinned_mae": mae_pin,
               "own_trees_off_mae": mae_off, **base_rec, "passed": bool(la.guard_passed),
               "bank": "the lead's guard-cut bank (owner ruling H2)", "bank_cut": int(bank_g.manifest.cut),
               "bank_max_label_time": bank_newest, "guard_rows_in_bank_label_window": in_window,
               "corrector_coverage": getattr(s, "corrector_coverage", {}).get("lead-%d guard-cut" % L),
               "fallback_donor_rows": "the guard bank's donor rows (SPEC_TABLE_MODE.md 3.8 step 5)",
               "pools_file": "%s/lead_%d/%s" % (LADDER_DIR, L, pools_file),
               **({"score_context_missing": s1} if s1 is not None else {}),
               "router": _json(routed.records)}
        if v1:
            self._log("lead %d guard: %s MAE %.6g vs the donor-row median %.6g (MAE %.6g; V1) on %d rows; its trees-off "
                      "%.6g beside -> %s" % (L, name, mae_pin, base_rec["baseline_value"], base_rec["baseline_mae"],
                                             y.size, mae_off, "PASSES" if la.guard_passed else
                                             "FAILS: the lead adopts the donor-row median (D86, V1)"))
        else:
            self._log("lead %d guard: %s MAE %.6g vs its trees-off %.6g on %d rows -> %s"
                      % (L, name, mae_pin, mae_off, y.size,
                         "PASSES" if la.guard_passed else "FAILS: the lead adopts the decline target (D86)"))
        # owner ruling AE: the twin on the guard surface (a separate neighbour pass, only when the lead can be active)
        self._alarm = self._alarm_guard(o, la, ctx, store_g, bank_g, donor_g, g_keys, units, times, y, arms[name],
                                        (REFERENCE_COLUMN + " (the donor-row median, owner ruling V1)") if v1 else
                                        ("the pinned link's trees-off (%s)" % off),
                                        base_rec["baseline_mae"] if v1 else mae_off, str(surface.sha256))
        return la, rec

    def _alarm_guard(self, o: Mapping[str, Any], la: Any, ctx: Any, store_g: Any, bank_g: Any, donor_g: Any,
                     g_keys: np.ndarray, units: np.ndarray, times: np.ndarray, y: np.ndarray, pinned: np.ndarray,
                     baseline: str, baseline_mae: float, surface_sha256: str) -> Dict[str, Any]:
        """Owner ruling AE at lead L on its guard surface (pipeline/ladder.py Ladder._alarm_guard's reading): the
        twin's facts; when the lead can be active the twin alone in a second neighbour pass on the guard rows (the
        guard bank, the pinned point), its MAE against the guard's baseline (eligibility) and the reference gap,
        saved in ladder/lead_<L>/alarm_guard_preds.parquet."""
        s = self.s
        L = int(o["lead"])
        facts = AP.lead_twin(self.pinned, bool(la.guard_passed), s.weightings())
        out: Dict[str, Any] = {"facts": facts, "reference": None, "guard_preds_file": None,
                               "eligibility_basis": {"basis": "not computed: the lead cannot be active from its arm "
                                                              "and guard alone (no twin routed)"}}
        if not AP.may_be_active(facts):
            return out
        twin = facts["twin"]
        tname = LA.arm_name(twin)
        t_arms, _, t_pre, _ = self._route(o, g_keys, [twin], "lead %d guard alarm twin" % L, ctx, store_g, bank_g,
                                          o["weights"], o["median"], donor_g)
        t_clip, t_raw = t_arms[tname], t_pre[tname]
        mae_twin = LD.surface_mae(y, t_clip)
        facts["eligible"] = LAL.twin_eligible_lead(mae_twin, baseline_mae)
        gap = LAL.reference_gap(pinned, t_clip)
        frame = pd.DataFrame({"unit": units, "group": [s.unit_group[str(u)] for u in units.tolist()], "time": times,
                              "issue": times - L, "y": y, M.ARM_PREFIX + LA.arm_name(self.pinned): pinned,
                              M.ARM_PREFIX + tname: t_clip, M.PRE_PREFIX + tname: t_raw})
        path = self._lead_dir(L) / AP.ALARM_GUARD_PREDS
        _write_parquet_once(frame, path)
        rel = path.relative_to(self.p.folder).as_posix()
        out["guard_preds_file"] = rel
        out["eligibility_basis"] = {"basis": "the twin's MAE on the lead's guard surface at the pinned point (owner "
                                             "ruling AF2), strictly below the baseline the lead's own guard used",
                                    "ruling": "AF2", "twin_guard_mae": mae_twin,
                                    "baseline": baseline, "baseline_mae": baseline_mae}
        out["reference"] = {"surface": "lead %d guard surface" % L, "surface_sha256": surface_sha256, "file": rel,
                            "point": {"level": float(self.pin_point.level),
                                      "ratio": None if self.pin_point.ratio is None else float(self.pin_point.ratio)},
                            "rows": int(t_clip.size), "gap": gap}
        self._log("lead %d alarm: twin %s routed alone on the guard surface: MAE %.6g vs the guard baseline %.6g "
                  "(eligible: %s); reference gap %.6g on %d rows"
                  % (L, tname, mae_twin, baseline_mae, facts["eligible"], gap, t_clip.size))
        return out

    # ------------------------------------------------------------------ persistence (R31, D54 a)
    def _persistence(self, o: Mapping[str, Any], keys: np.ndarray) -> Dict[str, Any]:
        """Persistence and damped persistence inputs for the lead's test rows, read BEFORE the lead's lock."""
        s = self.s
        L = int(o["lead"])
        units = np.asarray(self.data.units, dtype=object)[keys]
        issue = np.asarray(o["lt"].issue_day, dtype=np.int64)[keys]
        y_issue, y_issue_day = s.labels.last_label_before(units, issue, "persistence_lead_%d" % L, with_days=True)
        d = o["ctx_fit"].donor_rows("damped_persistence_phi")
        dpos = np.asarray([s.row_pos[str(u)] for u in np.asarray(d.unit_ids).tolist()], dtype=np.int64)
        du = np.asarray(self.data.units, dtype=object)[dpos].astype(str)
        dday = np.asarray(d.times, dtype=np.int64)
        dy = np.asarray(d.y, dtype=np.float64)
        dmon = _event_month(dday)
        phi = self._phi(du, dday, dmon, dy, L)
        return {"y_issue": y_issue, "y_issue_day": y_issue_day, "phi": phi, "donor_units": du, "donor_days": dday, "donor_month": dmon,
                "donor_y": dy, "donor_mean": float(dy.mean())}

    def _phi(self, du: np.ndarray, dday: np.ndarray, dmon: np.ndarray, dy: np.ndarray, L: int) -> Dict[str, float]:
        out: Dict[str, float] = {}
        order = np.lexsort((dday, du))
        du, dday, dmon, dy = du[order], dday[order], dmon[order], dy[order]
        names, starts = np.unique(du, return_index=True)
        bounds = list(starts.tolist()) + [du.size]
        for k, u in enumerate(names.tolist()):
            sl = slice(bounds[k], bounds[k + 1])
            t, mo, y = dday[sl], dmon[sl], dy[sl]
            sums = {int(m): float(y[mo == m].sum()) for m in np.unique(mo).tolist()}
            counts = {int(m): int((mo == m).sum()) for m in np.unique(mo).tolist()}
            a_list, ap_list = [], []
            for i in range(t.size):
                j = int(np.searchsorted(t, int(t[i]) - L, side="left")) - 1
                if j < 0:
                    continue
                ki, kj = int(mo[i]), int(mo[j])
                yi, yp = float(y[i]), float(y[j])
                if ki == kj:
                    c = counts[ki]
                    if c < M.PHI_SHARED_MIN_LABELS:
                        continue
                    m_ = (sums[ki] - yi - yp) / (c - 2)
                    a_list.append(yi - m_)
                    ap_list.append(yp - m_)
                else:
                    ci, cj = counts[ki], counts[kj]
                    if ci < M.PHI_SEPARATE_MIN_LABELS or cj < M.PHI_SEPARATE_MIN_LABELS:
                        continue
                    a_list.append(yi - (sums[ki] - yi) / (ci - 1))
                    ap_list.append(yp - (sums[kj] - yp) / (cj - 1))
            a, ap = np.array(a_list), np.array(ap_list)
            den = float(np.sum(ap ** 2)) if ap.size else 0.0
            out[u] = float(np.clip(float(np.sum(a * ap)) / den, M.PHI_BOUNDS[0], M.PHI_BOUNDS[1])) if den > 0 else 0.0
        return out

    def _o17_normal(self, pers: Mapping[str, Any], units: np.ndarray, days: np.ndarray) -> np.ndarray:
        """Owner item O17: the baseline-only normal of each (package unit, day): the unit's event-month mean at or
        before the lead's fit cut, else its all-season mean, else the donor-row mean."""
        du, dmon, dy = pers["donor_units"], pers["donor_month"], pers["donor_y"]
        frame = pd.DataFrame({"u": du, "m": dmon, "y": dy})
        by_um = frame.groupby(["u", "m"])["y"].mean().to_dict()
        by_u = frame.groupby("u")["y"].mean().to_dict()
        months = _event_month(days)
        out = np.empty(units.size)
        for i, (u, m) in enumerate(zip(np.asarray(units, dtype=object).astype(str).tolist(), months.tolist())):
            v = by_um.get((u, int(m)))
            if v is None:
                v = by_u.get(u, pers["donor_mean"])
            out[i] = float(v)
        return out

    # ------------------------------------------------------------------ the lock
    def _lock(self, la: Any, L: int, vault: Any) -> str:
        s = self.s
        folder = self.p.folder
        name = LEAD_ADOPTION_FILE % L
        lock = folder / (name + LOCK_SUFFIX)
        if lock.is_file():
            text = dumps(LD.lead_adoption_document(la, s.adoption_sha)) + "\n"
            if (folder / name).read_bytes() != text.encode("utf-8"):
                raise TableLadderRefusal("G-LOCK", "lead %d: the locked %s differs from the adoption recomputed on resume"
                                         % (L, name), fix="start a new run")
            return read_json(lock)["sha256"]
        return lock_lead_adoption(la, s.adoption, s.adoption_sha, vault, folder)

    # ------------------------------------------------------------------ one lead
    def run_lead(self, L: int) -> Dict[str, Any]:
        s, p = self.s, self.p
        t0 = time.time()
        with ExitStack() as stack:
            o = self._objects(L, stack)
            with ExitStack() as guard_stack:
                la, guard = self._guard(o, guard_stack)
            t_keys, t_units, t_days = s.test_rows()
            present = np.asarray(o["lt"].present, dtype=bool)[t_keys]
            pers_keys = t_keys[present]
            pers = self._persistence(o, pers_keys)
            reads = s.labels.test_window_reads()
            sha = self._lock(la, L, o["vault"])
            missing = ~present
            if not present.any():
                raise TableLadderRefusal("H4", "lead %d: every test row is absent from the lead's file" % L)
            k_keys, k_units, k_days = t_keys[present], t_units[present], t_days[present]
            p_units, p_days = k_units, k_days                     # the H4-kept rows, before S1 (S1's save half)
            y_issue, pk = np.asarray(pers["y_issue"], dtype=np.float64), np.arange(pers_keys.size)
            keep, s1, s1_cells = s.score_context_compute("lead %d test pass" % L, o["ctx_fit"], L, k_keys, k_units,
                                                         k_days)
            if s1 is not None:
                k_keys, k_units, k_days, y_issue, pk = (k_keys[keep], k_units[keep], k_days[keep], y_issue[keep],
                                                        pk[keep])
            lead_arms = LA.lead_arms(self.pinned, L, self.longest)
            tree_arms = [a for a in lead_arms if a.tool is not LA.Tool.TREES_OFF]
            arms, placebos, pre, routed = self._route(o, k_keys, tree_arms, "lead %d test pass" % L, o["ctx_fit"],
                                                      o["store"], o["bank"], o["weights"], o["median"], o["donor"])
            pools_file = self.last_pass.save_pools(self._lead_dir(L), "test_pass")
            alarm = self._alarm
            self._alarm = None
            facts, ref = alarm["facts"], alarm["reference"]
            status = LAL.pass_status(bool(facts["declined"]), facts.get("simpler"), facts.get("eligible"),
                                     None if ref is None else ref.get("gap"))
            twin_v = twin_pre = None
            if status == LAL.STATUS_ACTIVE:
                # owner ruling AE: the twin alone, a second neighbour pass on the same kept rows (save_pools above
                # already wrote the lead's own pass)
                tname = LA.arm_name(facts["twin"])
                t_arms, _, t_pre, _ = self._route(o, k_keys, [facts["twin"]], "lead %d test pass alarm twin" % L,
                                                  o["ctx_fit"], o["store"], o["bank"], o["weights"], o["median"],
                                                  o["donor"])
                twin_v, twin_pre = t_arms[tname], t_pre[tname]
            punits = np.asarray(self.data.units, dtype=object)[k_keys]
            # the day of the label persistence read (the vault's own read, before the lock; -1 where none)
            prev_day = np.asarray(pers["y_issue_day"], dtype=np.int64)[pk]
            normal_t = self._o17_normal(pers, punits, k_days)
            normal_i = self._o17_normal(pers, punits, np.where(prev_day >= 0, prev_day, k_days))
            phi_rows = np.array([pers["phi"].get(str(u), 0.0) for u in punits.tolist()], dtype=np.float64)
            baselines = s.common_baselines(k_keys.size, o["median"])
            baselines.update({"persistence": M.baseline_persistence(y_issue, s.legal),
                              "damped_persistence": M.baseline_damped_persistence(normal_t, normal_i, y_issue,
                                                                                  phi_rows, s.legal)})
            # owner ruling AE: the lead's alarm, decided from these label-free predictions and locked; then the labels
            if la.guard_passed:
                ad_name = LA.arm_name(self.pinned)
                ad_col, ad_v, ad_pre = M.ARM_PREFIX + ad_name, arms[ad_name], pre[ad_name]
            elif s.decline_to_donor_median():
                ad_name, ad_col = REFERENCE_COLUMN[len(M.BASELINE_PREFIX):], REFERENCE_COLUMN
                ad_v = ad_pre = np.asarray(baselines["donor_median"], dtype=np.float64)
            else:
                ad_name = LA.arm_name(LA.trees_off_of(Link.IDENTITY))
                ad_col, ad_v, ad_pre = M.ARM_PREFIX + ad_name, arms[ad_name], pre[ad_name]
            rk = s.row_keys(k_keys, k_units, k_days)
            alarm_sha, _ = AP.run_pass_alarm(
                s, lead=L, pass_name="lead %d test pass" % L, out_dir=self._lead_dir(L),
                adoption_file=LEAD_ADOPTION_FILE % L, adoption_sha256=sha, labels=o["vault"], adopted_name=ad_name,
                adopted_column=ad_col, facts=facts, eligibility_basis=alarm["eligibility_basis"], reference=ref,
                keys={"unit": rk["unit"], "group": rk["group"], "time": rk["time"], "year": rk["year"],
                      "issue": k_days - L},
                adopted=ad_v, pre_adopted=ad_pre, twin=twin_v, pre_twin=twin_pre, cadence=None,
                guard_preds_file=alarm["guard_preds_file"])
            tl = o["vault"].open_test_labels(sha, L, alarm_sha256=alarm_sha)
            y_all = s.test_labels(tl, t_units, t_days)
            h4 = self._save_issue_missing(L, t_units[missing], t_days[missing], y_all[missing])
            y = y_all[present]
            if s1 is not None:
                s.score_context_save("lead %d test pass" % L, o["ctx_fit"], L, p_units, p_days, y, s1, s1_cells)
                y = y[keep]
            frame = M.assemble_rows(s.row_keys(k_keys, k_units, k_days), L, k_days - L, y,
                                    np.full(k_keys.size, np.nan), arms, placebos, pre, baselines, s.legal)
            path = self._lead_dir(L) / REC.TEST_PREDS
            if path.exists():
                if not M.read_rows(path).equals(frame):
                    raise TableLadderRefusal("G-FINGERPRINT", "%s exists with other rows" % path, fix="start a new run")
            else:
                M.write_rows_once(frame, path)
            v1 = s.decline_to_donor_median()
            if la.guard_passed:
                adopted_col = M.ARM_PREFIX + LA.arm_name(self.pinned)
                own_off_col = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(self.pinned.link))
            elif v1:
                # owner ruling V1: the lead adopts the donor-row median its guard compared with; the pinned link's
                # trees-off is printed beside
                adopted_col = REFERENCE_COLUMN
                own_off_col = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(self.pinned.link))
            else:
                adopted_col = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(Link.IDENTITY))
                own_off_col = adopted_col
            test = {"rows": int(len(frame)), "test_rows": int(t_keys.size), "labelled_rows": int(np.isfinite(y).sum()),
                    "issue_features_missing": h4, **({"score_context_missing": s1} if s1 is not None else {}),
                    "arms": sorted(arms), "placebos": sorted(placebos),
                    "adopted_column": adopted_col, "reference_column": REFERENCE_COLUMN,
                    **({"decline_target": REFERENCE_COLUMN, "decline_rule": V1_RULE} if v1 else {}),
                    "own_trees_off_column": own_off_col,
                    "persistence_rows_with_issue_label": int(np.isfinite(y_issue).sum()),
                    "persistence_reads_before_lock": reads, "damped_persistence": {"rule": PAIRS_RULE,
                                                                                  "normal": O17_NORMAL},
                    "pools_file": "%s/lead_%d/%s" % (LADDER_DIR, L, pools_file), "router": _json(routed.records)}
            rec = {"lead": L, "cuts": {"fit_cut": int(self.cuts[L].fit_cut), "guard_cut": int(self.cuts[L].guard_cut)},
                   "pinned": LA.arm_name(self.pinned),
                   "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
                   "adopted": LA.arm_name(la.adopted) if la.adopted is not None else None,
                   "declined_at_lead": la.adopted is None, "placebo_built": bool(la.placebo_built),
                   "adoption_file": LEAD_ADOPTION_FILE % L, "adoption_sha256": sha, "guard": guard, "test": test,
                   "fits": o["record"], "longest_lead": self.longest,
                   "issue_features_missing": h4, "rulings": GL.RULINGS}
            REC.write_once_or_same(self._lead_dir(L) / LEAD_RECORD, _json(rec))
            s.write_log_part(PHASE_LEAD % L)
            o = None
        s.extra_contexts = []
        self._log("lead %d done in %.1f s: %s adopted" % (L, time.time() - t0, rec["adopted"] or (
            "the donor-row median (V1)" if s.decline_to_donor_median() else "the decline target")))
        return {"adopted": rec["adopted"], "guard_passed": not rec["declined_at_lead"], "rows": test["rows"],
                "issue_rows_left_out": int(h4["rows_left_out"]), "seconds": round(time.time() - t0, 2)}

    def _save_issue_missing(self, L: int, units: np.ndarray, days: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Owner ruling H4 on a table (owner item O15): the test rows absent from the lead's file, left out of scoring,
        saved once as ladder/lead_<L>/issue_missing_rows.parquet with the flag and counted per unit."""
        s = self.s
        units = np.asarray(units, dtype=object)
        days = np.asarray(days, dtype=np.int64)
        n = int(units.size)
        pu = np.asarray(self.data.units, dtype=object)[np.asarray([s.row_pos[str(u)] for u in units.tolist()],
                                                                    dtype=np.int64)] if n else np.zeros(0, object)
        rec: Dict[str, Any] = {"rule": GL.H4_RULE, "reading": "a test row absent from the lead's file (owner item O15)",
                               "rows_left_out": n, "units_with_rows_left_out": len(set(pu.tolist())),
                               "by_unit": GL._counts(pu), "rows_file": None}
        if not n:
            s.log("lead %d test pass: H4: every test row is in the lead's file; none left out" % L)
            return rec
        frame = pd.DataFrame({"unit": units, "group": np.asarray([s.unit_group[str(u)] for u in units.tolist()], dtype=object),
                              "time": days, "year": years_of_days(days), "lead": np.full(n, int(L), dtype=np.int64),
                              "issue": days - int(L), "y": np.asarray(y, dtype=np.float64),
                              ISSUE_FLAG: np.ones(n, dtype=bool), "reason": np.full(n, ISSUE_REASON_ABSENT, dtype=object)})
        _write_parquet_once(frame, self._lead_dir(L) / ISSUE_MISSING_ROWS)
        rec["rows_file"] = "%s/lead_%d/%s" % (LADDER_DIR, L, ISSUE_MISSING_ROWS)
        s.log("lead %d test pass: H4 left %d test row(s) out of scoring (absent from the lead's file); saved in %s"
              % (L, n, rec["rows_file"]))
        return rec

    # ------------------------------------------------------------------ the ladder table
    def table(self) -> Dict[str, Any]:
        """Every lead on the rows common to all leads and on all its scored rows; each lead's verdict against the
        donor-row median (signed R34) under the nowcast's band (F57)."""
        s, p = self.s, self.p
        tol, floor = s.hit_tolerance()
        verdict = read_json(p.folder / REC.VERDICT_FILE)
        band = float(verdict["band"])
        frames = {0: M.read_rows(p.folder / REC.TEST_PREDS)}
        # owner ruling V1: verdict.json names the adopted column (base__donor_median when the nowcast declined)
        info = {0: {"adopted_column": verdict["adopted_column"], "declined": bool(verdict["declined"])}}
        issue_missing: Dict[str, Any] = {}
        for L in self.leads:
            frames[L] = M.read_rows(self._lead_dir(L) / REC.TEST_PREDS)
            lr = read_json(self._lead_dir(L) / LEAD_RECORD)
            info[L] = {"adopted_column": lr["test"]["adopted_column"], "declined": bool(lr["declined_at_lead"]),
                       "guard_passed": not lr["declined_at_lead"]}
            issue_missing[str(L)] = {"rows_left_out": int(lr["issue_features_missing"]["rows_left_out"]),
                                     "rows_file": lr["issue_features_missing"]["rows_file"]}

        def keys_of(f, col):
            ok = np.isfinite(f["y"].to_numpy(dtype=np.float64)) & np.isfinite(f[col].to_numpy(dtype=np.float64))
            return np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].to_numpy(dtype=object)[ok].tolist(),
                                                               f["time"].to_numpy(dtype=np.int64)[ok].tolist())],
                              dtype=object)
        common = set(M.common_rows({L: keys_of(f, info[L]["adopted_column"]) for L, f in frames.items()}).tolist())
        lines, verdicts = [], {}
        for L, f in sorted(frames.items()):
            k = np.asarray(["%s\t%d" % (u, t) for u, t in zip(f["unit"].to_numpy(dtype=object).tolist(),
                                                            f["time"].to_numpy(dtype=np.int64).tolist())], dtype=object)
            sub = f[np.isin(k, np.asarray(sorted(common), dtype=object))].reset_index(drop=True)
            for basis, frame in ((GL.ROWS_BASIS_COMMON, sub), (GL.ROWS_BASIS_ALL, f)):
                t = M.score_table(frame, (), tol, floor, p.kind)
                t = t[(t["line"] == M.LINE_POOLED) & (t["rows_basis"] == M.ROWS_BASIS_ALL)].copy()
                pinned_col = M.ARM_PREFIX + LA.arm_name(self.pinned)
                keep = t["column"].isin([info[L]["adopted_column"], REFERENCE_COLUMN, pinned_col]) | \
                    t["column_kind"].isin(("baseline", "placebo"))
                t = t[keep]
                t.insert(0, "ladder_rows", basis)
                t.insert(0, "lead", L)
                t.insert(2, "adopted", t["column"] == info[L]["adopted_column"])
                lines.append(t)
            tg = M.score_table(sub, ("group",), tol, floor, p.kind)
            ad_c = info[L]["adopted_column"]
            per_ref = M.metric_by_key(tg, REFERENCE_COLUMN, "mae", "group")
            per_ad = M.metric_by_key(tg, ad_c, "mae", "group")
            tp = M.score_table(sub, (), tol, floor, p.kind)

            def pooled(col):
                sel = tp[(tp["line"] == M.LINE_POOLED) & (tp["column"] == col) & (tp["rows_basis"] == M.ROWS_BASIS_ALL)]
                return float(sel["mae"].iloc[0])
            v = M.single_verdict(per_ref, per_ad, pooled(REFERENCE_COLUMN), pooled(ad_c), band, info[L]["declined"],
                                 M.REFERENCE_DONOR_ROW_MEDIAN)
            verdicts[L] = dict(M.verdict_record(v), adopted=ad_c, reference=REFERENCE_COLUMN,
                               guard_passed=info[L].get("guard_passed"), common_rows=int(len(sub)))
        table = pd.concat(lines, ignore_index=True)
        self.folder.mkdir(parents=True, exist_ok=True)
        REC.write_text_once_or_same(self.folder / LADDER_TABLE, REC.csv_text(table))
        rec = {"leads": list(self.leads), "lead_unit": "days", "longest_lead": self.longest, "band": band,
               "band_source": "the nowcast's band (F57: the nowcast band decides at every lead)",
               "pinned": LA.arm_name(self.pinned), "penalty": {"level": self.pin_point.level, "ratio": self.pin_point.ratio},
               "reference": REFERENCE_COLUMN, "reference_rule": M.REFERENCE_DONOR_ROW_MEDIAN,
               "common_rows": len(common), "verdicts": {str(L): v for L, v in sorted(verdicts.items())},
               "issue_rows_left_out": {"rule": GL.H4_RULE, "by_lead": issue_missing},
               "hit_tolerance": tol, "measurement_error_floor": floor, "rulings": GL.RULINGS}
        if p.draft.is_draft:
            rec = dict({"DRAFT": "DRAFT: %s -- never a headline number" % p.draft.stamp}, **rec)
        REC.write_once_or_same(self.folder / LADDER_RECORD, _json(rec))
        # owner ruling AE2: the ladder with and without the alarm (new files; the two above are unchanged)
        info_alarm = {L: {"adopted_column": v["adopted_column"], "reference_column": REFERENCE_COLUMN,
                          "declined": v["declined"]} for L, v in info.items()}
        AP.write_alarm_ladder(s, self.folder, frames, info_alarm, common, band, M.REFERENCE_DONOR_ROW_MEDIAN, tol, floor,
                              {L: _json(v) for L, v in verdicts.items()})
        return {"leads": list(self.leads), "common_rows": len(common),
                "verdicts": {str(L): v["tag"] for L, v in verdicts.items()}}

    # ------------------------------------------------------------------ the whole ladder
    def run(self, phases: Any) -> Dict[str, Any]:
        s = self.s
        out: Dict[str, Any] = {}
        s.release_bank(P.BANK_INNER, "the nowcast's decision is locked and its test pass is done; the ladder never "
                                     "reads the inner-cut bank")
        if not phases.done(PHASE_CONTRACT):
            s.p._phase = PHASE_CONTRACT
            rec = self.contract()
            s.write_log_part(PHASE_CONTRACT)
            s.extra_contexts = []
            phases.mark_done(PHASE_CONTRACT, {"pinned": rec["pinned"], "rows": rec["rows"]})
        s.release_bank(P.BANK_FIT, "the lead-0 contract is done; leads of one day or more fit their own banks")
        for L in self.leads:
            name = PHASE_LEAD % L
            if phases.done(name):
                continue
            s.p._phase = name
            phases.mark_done(name, self.run_lead(L))
        if not phases.done(PHASE_TABLE):
            s.p._phase = PHASE_TABLE
            out = self.table()
            s.write_log_part(PHASE_TABLE)
            phases.mark_done(PHASE_TABLE, out)
        return out


__all__ = ["TableLadder", "TableLadderRefusal", "table_lead_plan", "table_phase_names", "O17_NORMAL", "PAIRS_RULE"]
