"""The heavy steps of a table run (SPEC_TABLE_MODE.md 3.7): TableRunState, the run state of the table option.

Owner ruling U1 (the owner rulings file, section U). A table run is the grid run's steps on a ROW GRID (each
sample row is the engine unit; package/table.py, labels/rows.py), so most of pipeline/passes.py's RunState runs
UNCHANGED here and is inherited: the per-group bank checkpoints (fit_bank, keyed with the table data manifest
through the pipeline's census_step), the bank stacks and their release, the fitctx log parts, G1's log twins and
saved rows, the adoption manifest and its read-back, the pre-clip table, the decision arms and the GLS record.
Only what reads grid steps, normals or the per-unit router is replaced:
  - build_pool: the nowcast pool filled from the lead-0 table (no own-history block: R17 is empty);
  - fit: the fit-cut bank and the inner-cut bank (L6 b) through FitContext, c, R36 tolerances, the donor-row
    median (U3), the cut's GLS weight model (R25, as grids) and, for the decision surface, one c, one fallback
    median and one GLS model per fold (signed R13, R25; FitContext.donor_rows_outside, weight_models_for_folds);
  - the passes route through pipeline/table_router.NeighbourPass (the neighbour kind of U3 / U4);
  - leave_out_score_context: owner ruling S1 with the gate on the neighbour kind (it reads context) and years
    from days;
  - hit_tolerance (R32 neighbour: against the donor-row median), the strata (a string stratum scored per value,
    owner item O18) and the report's verdict lines: the reference is the donor-row median (signed R34, G-DECIDE;
    report.metrics.REFERENCE_DONOR_ROW_MEDIAN), the neighbour trees-off printed beside;
  - owner ruling V1 (decline_to_donor_median, gated on R12's router kind): the decision's N2 compares every arm
    with the donor-row median (each surface row its fold's median, the U3 fallback, N5), and a declined nowcast
    adopts that median (base__donor_median), so the check and the fallback are one object;
  - the grid table helpers (_build_tables, _pass_tables) refuse: no grid step helper is reachable in a table run;
  - V6 b (PLAN_V6B.md E3): the donor-only groups (derived.json 'R18:donor_only': no test row) train trees and lend
    rows like every group; the decision logs how many surface folds are donor-only and verdict.json records them
    (donor_only_record); n_groups stays the scored count.
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.7, 3.8, 3.10, 5.11, 5.12; pipeline/passes.py (the grid bodies
# copied where a line reads grid steps); APP_PLAN.md R13, R24, R25, R31-R34; OWNER_RULINGS_2026-10-06.md U1, U3, S1,
# V1 (:103).

import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import split as SP
from treeroute.derive.shapes import CutKind, Link
from treeroute.fit.context import FitContext
from treeroute.fit.pool import open_pool
from treeroute.fit.tables import TreeAnswerStore
from treeroute.fit.weights import weight_model_for_cut, weight_model_record, weight_models_for_folds
from treeroute.labels.vault import lock_adoption
from treeroute.layer import arms as LA
from treeroute.layer import decide as LD
from treeroute.layer.links import c_for_cut, c_for_cut_against_plan, clip_to_legal
from treeroute.report import metrics as M
from treeroute.runs.atomic import read_json

from . import passes as P
from . import record as REC
from . import router as PR
from . import stages as ST
from .passes import PassRefusal, RunState, _write_parquet_once
from .table_router import NeighbourPass, PassPart

PHASE = P.PHASE
PHASE_T = P.PHASE_T
FOLD_GLS_FILE = "gls_weight_models_folds.json"
REFERENCE_COLUMN = M.BASELINE_PREFIX + "donor_median"
# Provenance: OWNER_RULINGS_2026-10-06.md:103 (ruling V1, 2026-10-19).
V1_RULE = ("owner ruling V1 (the owner rulings file, section V): for the neighbour kind, every decline (nowcast and every "
           "lead) falls back to the donor-row median (R34), and every guard or decline comparison uses that same "
           "donor-row median as its baseline, so the check and the fallback are one object")
V1_DECLINED_ADOPTED = "donor_median"
DONOR_ONLY_KEY = "donor_only_groups"


def donor_only_record(derived: Mapping[str, Any]) -> Dict[str, Any]:
    """V6 b: the donor-only groups of a table run from derived.json's 'R18:donor_only' (groups, count, train rows,
    surface rows, rule); an empty record when the entry is absent or empty."""
    entry = derived.get("R18:donor_only")
    if entry is None:
        return {"groups": [], "count": 0, "train_rows": 0, "surface_rows": 0, "rule": None}
    groups = [str(g) for g in entry.value]
    return {"groups": groups, "count": len(groups),
            "train_rows": int(sum(int(v) for v in (entry.inputs.get("train_rows") or {}).values())),
            "surface_rows": int(sum(int(v) for v in (entry.inputs.get("surface_rows") or {}).values())),
            "rule": entry.inputs.get("rule")}


def years_of_days(days: np.ndarray) -> np.ndarray:
    """The calendar year of each day ordinal."""
    import datetime as _dt

    distinct, inverse = np.unique(np.asarray(days, dtype=np.int64), return_inverse=True)
    years = np.array([_dt.date.fromordinal(int(d)).year for d in distinct.tolist()], dtype=np.int64)
    return years[np.asarray(inverse).reshape(-1)]


def corrector_coverage(bank: Any) -> Dict[str, Any]:
    """How many trees and groups of a bank have no corrector (bank.correctors[i] is None when tree i had too few
    out-of-bag rows, fit/bank.py Bank). Groups listed in sorted order."""
    groups = np.asarray(bank.tree_group, dtype=object)
    none = np.asarray([c is None for c in bank.correctors], dtype=bool)
    names = sorted(set(groups.tolist()))
    without = [str(g) for g in names if none[groups == g].all()]
    partial = [str(g) for g in names if none[groups == g].any() and not none[groups == g].all()]
    return {"trees": int(none.size), "trees_without_corrector": int(none.sum()), "groups": len(names),
            "groups_without_corrector": without, "groups_partly_without_corrector": partial,
            "min_oob_rows": int(K.CORRECTOR_MIN_OOB_ROWS)}


class TableRunState(RunState):
    """The in-memory state of one table run (module docstring)."""

    # ------------------------------------------------------------------ the pool (step 3-5)
    def build_pool(self, need_inner: bool = True) -> None:
        p = self.p
        t0 = time.time()
        self.derived = p.derived
        kind = getattr(self.derived["R12"].value, "value", self.derived["R12"].value)
        if kind != PR.KIND_NEIGHBOUR:
            raise PassRefusal("U3", "a table run routes the neighbour kind only; derived.json's R12 is %r" % kind)
        self.kind = PR.KIND_NEIGHBOUR
        self.vg = p._vault(p.folder)
        self.labels = self.vg.labels
        self.lists = self.derived["R18:units"].value
        self.groups = tuple(sorted(self.lists.bank))
        data = p.table
        self.data = data
        rows = np.asarray(data.row_ids, dtype=object)
        self.row_pos = {str(r): i for i, r in enumerate(rows.tolist())}
        self.bank_units = rows.tolist()
        test = np.asarray(data.is_test, dtype=bool)
        self.scored_units = rows[test].tolist()
        self.unit_group = {str(r): str(g) for r, g in zip(rows.tolist(), np.asarray(data.groups, dtype=object).tolist())}
        self.season = self.derived["R2"].value
        self.cuts = self.derived["R11"].value[0]
        self.windows = self.derived["R7"].value
        self.links = tuple(self.derived["R22"].value)
        self.legal = p.spec.legal_range
        self.ub = self.legal[1] if np.isfinite(self.legal[1]) else None
        self.history_filled, self.history_donor_mean, self.history_inner = {}, None, None
        self._beat("pool", "%d table rows, %d tree columns, %d context columns (lead 0)"
                   % (rows.size, len(p.spec.tree_features), len(p.spec.context)))
        self.pool = self._stack.enter_context(self.open_lead_pool("pool", 0))
        self.ctx_fit = FitContext(self.derived, p.split_sets, self.vg.grid, self.labels, self.pool, self.lists, 0,
                                  CutKind.FIT)
        self.inner_features = self.pool
        self._time("pool", t0)

    def decline_to_donor_median(self) -> bool:
        """Owner ruling V1: True for the neighbour kind (R12, read from derived.json by build_pool), never from a
        package name. Then the decision's N2, every lead's guard (D86) and every decline use the donor-row median."""
        return getattr(self, "kind", None) == PR.KIND_NEIGHBOUR

    def open_lead_pool(self, tag: str, lead: int) -> Any:
        """A context manager: a pool (fit.pool.open_pool, unchanged) over every row position, filled from the lead's
        table (NaN where the row is absent at the lead) and complete."""
        from contextlib import contextmanager

        p = self.p
        lt = p.table.leads[int(lead)]
        rows = np.arange(len(p.table.row_ids), dtype=np.int64)

        @contextmanager
        def opened():
            with open_pool(p.temp_dir, tag, rows, tuple(p.spec.tree_features), tuple(p.spec.context)) as pool:
                block = 50000
                for a0 in range(0, rows.size, block):
                    r = rows[a0:a0 + block]
                    pool.write(r, lt.tree[r].astype(np.float32),
                               lt.context[r].astype(np.float32) if p.spec.context else None)
                pool.require_complete()
                pool.lead = int(lead)          # read by NeighbourPass (R11: one lead per pass)
                yield pool
        return opened()

    def _build_tables(self, *args: Any, **kwargs: Any) -> None:
        raise P.PassRefusal("U1", "grid step helper reached in a table run (_build_tables)")

    def _check_bank(self, bank: Any, what: str) -> None:
        """RunState._check_bank, then the bank's corrector coverage, logged and kept for the records
        (corrector_coverage). A tree with fewer than C13.corrector_min_oob_rows out-of-bag rows has no corrector
        (fit/correctors.py); a group none of whose trees has one adds nothing to the corrector and placebo arms
        (FIX_REPORT.md, correctness review item 5; owner item)."""
        super()._check_bank(bank, what)
        cov = corrector_coverage(bank)
        self.__dict__.setdefault("corrector_coverage", {})[str(what)] = cov
        self.log("%s bank: %d of %d trees have no corrector (fewer than %d out-of-bag rows); %d of %d groups have "
                 "none at all" % (what, cov["trees_without_corrector"], cov["trees"], cov["min_oob_rows"],
                                  len(cov["groups_without_corrector"]), cov["groups"]))

    def _pass_tables(self, *args: Any, **kwargs: Any) -> Any:
        raise P.PassRefusal("U1", "grid step helper reached in a table run (_pass_tables)")

    # ------------------------------------------------------------------ step 6: fits
    def fit(self, need_inner: bool = True) -> None:
        p = self.p
        t0 = time.time()
        self.ctx_guard = self.ctx_fit.for_lead(0, CutKind.GUARD)
        self._beat("fits", "bank at the fit cut %d: %d groups x %d trees" % (self.cuts.fit_cut, len(self.groups),
                                                                            p.trees_per_group))
        self.donor_fit = self.ctx_fit.donor_rows("bank")
        self.bank_fit = self.fit_bank(self.donor_fit, P.BANK_FIT)
        self._check_bank(self.bank_fit, "fit-cut")
        row_group = ST.row_group_of(self.vg)
        self.store_fit = self._bank_stack(P.BANK_FIT).enter_context(
            TreeAnswerStore.from_bank(self.bank_fit, row_group, p.temp_dir, p.registry, echo=p.log))
        self.c = c_for_cut_against_plan(self.donor_fit, self.derived) if Link.LOG_C in self.links else None
        self.tol, self.tol_record = ST.guard_tolerances(self.donor_fit, self.links, self.c, self.ub, p.smoke)
        self.median_fit = M.baseline_donor_median(self.donor_fit)
        self.donor_mean_fit = ST.donor_link_means(self.donor_fit, self.links, self.c, self.ub)
        self._beat("fits", "GLS weight model (R25) at the guard cut %d" % self.cuts.guard_cut)
        self.weights = weight_model_for_cut(self.ctx_fit, self.ctx_guard, self.store_fit, self.bank_fit.tree_group,
                                            blocks=p.blocks, matrix_dir=p.temp_dir, echo=self.log)
        from treeroute.derive.derived import derived_entry

        REC.write_once_or_same(p.folder / "gls_weight_model.json", derived_entry(weight_model_record(self.weights)))
        if need_inner:
            if K.INNER_CUT_BANK_REFIT:
                self._beat("fits", "bank refit at the inner cut %d (L6 b)" % self.cuts.guard_cut)
                self.ctx_inner = FitContext(self.derived, p.split_sets, self.vg.grid, self.labels, self.pool,
                                            self.lists, 0, CutKind.GUARD)
                self.donor_inner = self.ctx_inner.donor_rows("bank_inner")
                self.bank_inner = self.fit_bank(self.donor_inner, P.BANK_INNER)
                self._check_bank(self.bank_inner, "inner-cut")
                self.store_inner = self._bank_stack(P.BANK_INNER).enter_context(
                    TreeAnswerStore.from_bank(self.bank_inner, row_group, p.temp_dir, p.registry, echo=p.log))
            else:
                self.ctx_inner = self.ctx_guard
                self.donor_inner = self.ctx_guard.donor_rows("normal_fallback")
                self.bank_inner, self.store_inner = self.bank_fit, self.store_fit
            self._fold_objects()
        self.write_log_part("setup_with_inner" if need_inner else "setup")
        self._time("fits", t0)

    def _fold_objects(self) -> None:
        """Per decision-surface fold g (signed R13, R25; SPEC_TABLE_MODE.md 3.7 fit): the guard-cut donor rows
        outside g's overlap block (FitContext.donor_rows_outside), their c (checked against 'R23:fold=<g>'), their
        donor-row median (U3's fallback on the surface, N5) and one GLS weight model (weight_models_for_folds)."""
        from treeroute.derive.rules import check_r23_matches_run

        p = self.p
        folds = tuple(self.derived["R13"].value[1])
        self.fold_donor: Dict[str, Any] = {}
        self.fold_c: Dict[str, Optional[float]] = {}
        for i, (g,) in enumerate(folds):
            left = SP.block_of_group(p.blocks, g)
            d = self.ctx_inner.donor_rows_outside("fold_donor", tuple(left), i)
            self.fold_donor[g] = d
            if Link.LOG_C in self.links:
                c = c_for_cut(d)
                key = "R23:fold=%s" % g
                if key not in self.derived:
                    raise PassRefusal("R23", "derived.json has no %s entry (plan writes one per fold when log_c is a "
                                      "link)" % key)
                check_r23_matches_run(self.derived[key], 0, int(d.cut), c, d.row_key_hash)
                self.fold_c[g] = c
            else:
                self.fold_c[g] = None
        self._beat("fits", "GLS weight models of the %d decision-surface folds (R13, R25)" % len(folds))
        self.fold_weights = weight_models_for_folds(self.ctx_fit, self.ctx_guard, self.store_fit,
                                                    self.bank_fit.tree_group, blocks=p.blocks, folds=folds,
                                                    echo=self.log)
        from treeroute.derive.derived import derived_entry

        REC.write_once_or_same(p.folder / FOLD_GLS_FILE,
                               {"R25:fold=%s" % g: derived_entry(weight_model_record(m))
                                for g, m in self.fold_weights.items()})

    # ------------------------------------------------------------------ owner ruling S1 on a table pass
    def leave_out_score_context(self, what: str, ctx: Any, lead: int, keys: np.ndarray, units: np.ndarray,
                                steps: np.ndarray, y: Optional[np.ndarray] = None, save: bool = True) -> tuple:
        """Owner ruling S1 on a table pass: the body of RunState.leave_out_score_context with the gate on the
        neighbour kind (its router reads context) and years from days. steps are the rows' target days."""
        keys = np.asarray(keys, dtype=np.int64)
        n = int(keys.size)
        bad_cell = ST.score_context_missing(ctx.features, keys) if n else None
        if bad_cell is None or not bad_cell.any():
            return np.ones(n, dtype=bool), None
        bad = bad_cell.any(axis=1)
        if bad.all():
            raise PassRefusal("S1", "%s: every one of the %d scored rows has missing or non-finite router context: "
                              "nothing is left to score" % (what, n))
        units = np.asarray(units, dtype=object)
        days = np.asarray(steps, dtype=np.int64)
        us = units.astype(str)
        lost_u, lost_n = np.unique(us[bad], return_counts=True)
        unscored = sorted(set(us.tolist()) - set(us[~bad].tolist()))
        cols = tuple(str(c) for c in ctx.features.context_columns)
        rec: Dict[str, Any] = {
            "rule": ST.S1_RULE, "pass": str(what), "lead": int(lead), "scored_rows_before": n,
            "rows_left_out": int(bad.sum()), "units_with_rows_left_out": int(lost_u.size),
            "units_unscored": unscored,
            "by_unit": {str(u): int(k) for u, k in zip(lost_u.tolist(), lost_n.tolist())},
            "by_column": {c: int(bad_cell[:, j].sum()) for j, c in enumerate(cols) if bad_cell[:, j].any()},
            "rows_file": None}
        if not save:
            return ~bad, rec
        lost = np.flatnonzero(bad)
        frame = pd.DataFrame({"unit": units[lost],
                              "group": np.asarray([self.unit_group[u] for u in units[lost].tolist()], dtype=object),
                              "time": days[lost], "year": years_of_days(days[lost]),
                              "lead": np.full(lost.size, int(lead), dtype=np.int64),
                              "issue": days[lost] - int(lead)})
        if y is not None:
            frame["y"] = np.asarray(y, dtype=np.float64)[lost]
        frame[ST.SCORE_CONTEXT_FLAG] = np.ones(lost.size, dtype=bool)
        frame["reason"] = np.full(lost.size, ST.SCORE_CONTEXT_REASON, dtype=object)
        for j, c in enumerate(cols):
            frame[ST.MISSING_PREFIX + c] = np.asarray(bad_cell[lost, j], dtype=bool)
        rec["rows_file"] = self.save_context_missing_rows("%s scored" % what, frame)
        REC.add_pass_record(self.p.folder, str(what), {k: v for k, v in rec.items() if k not in ("rule", "pass")},
                            ST.S1_RULE)
        self.log("%s: S1 left %d of %d scored row(s) out of scoring (router context missing); rows saved in %s"
                 % (what, rec["rows_left_out"], n, rec["rows_file"]))
        return ~bad, rec

    # ------------------------------------------------------------------ step 8: the decision surface
    def decision(self) -> None:
        p = self.p
        t0 = time.time()
        ctx = self.ctx_inner
        fit_cut, guard_cut = int(self.cuts.fit_cut), int(self.cuts.guard_cut)
        vu, vt, vv = self.labels.validity(guard_cut + 1, fit_cut)
        pos = np.asarray([self.row_pos[str(u)] for u in vu.tolist()], dtype=np.int64)
        train = ~np.asarray(self.data.is_test, dtype=bool)[pos]
        pick = vv & train
        self.log("decision surface (D67, R13): %d train rows dated %d..%d; %d with a valid label: %d rows scored"
                 % (int(train.sum()), guard_cut + 1, fit_cut, int((vv & train).sum()), int(pick.sum())))
        keep, s1 = self.leave_out_score_context("decision surface", ctx, 0, pos[pick], vu[pick], vt[pick])
        if s1 is not None:
            idx = np.flatnonzero(pick)
            pick = pick.copy()
            pick[idx[~keep]] = False
        surface = self.labels.decision_surface(vu[pick], vt[pick], fit_cut)
        s_keys = pos[pick]
        groups = np.asarray(self.data.groups, dtype=object)[s_keys]
        parts = []
        for i, (g,) in enumerate(tuple(self.derived["R13"].value[1])):
            sel = np.flatnonzero(groups == g)
            if sel.size:
                parts.append(PassPart(name=g, score_index=sel, c=self.fold_c[g], model=self.fold_weights[g],
                                      fallback_donor=self.fold_donor[g], fold=i))
        donor_only = set(donor_only_record(self.derived)["groups"])
        if donor_only:
            folds_d = [pt.name for pt in parts if pt.name in donor_only]
            self.log("decision surface: %d of %d folds with surface rows are donor-only groups (V6 b), %d rows: %s"
                     % (len(folds_d), len(parts), int(sum(np.asarray(pt.score_index).size for pt in parts
                                                          if pt.name in donor_only)), ", ".join(folds_d[:20])))
        tree_arms = self.decision_arms()
        npass = NeighbourPass(self, "decision surface", ctx, self.store_inner, self.bank_inner.tree_group, 0,
                              self.data.leads[0], s_keys, parts, self.tol)
        self._beat(PHASE, "neighbour router: %d tree arms on the decision surface (%d folds)" % (len(tree_arms), len(parts)))
        routed = npass.route(tree_arms, None, plumbing=True)
        pools_file = npass.save_pools(p.folder, "decision_surface")
        # each row's link inverse uses its own fold's c (signed R13)
        c_rows = self._c_of_rows(parts, s_keys.size)
        arms: List[Any] = [LD.SurfaceArm(a, self._inverse_rows(routed.predictions[LA.arm_name(a)], a.link, c_rows))
                           for a in tree_arms]
        arms += [LD.SurfaceArm(LA.trees_off_of(L), self._inverse_rows(routed.trees_off[L], L, c_rows))
                 for L in self.links]
        self.plumbing = dict(routed.plumbing)
        # owner ruling V1: the decline baseline is each row's fold median, the U3 fallback of the same pass
        v1 = self.decline_to_donor_median()
        dl = LD.DeclineBaseline(REFERENCE_COLUMN, V1_RULE, npass.fallback_median_rows()) if v1 else None
        record = LD.decide(surface, arms, routed.grid, self.legal, ctx, gls_absent_reason=None, decline_baseline=dl)
        for line in LD.decision_lines(record):
            self.log.file_only(line)
        self._save_inner(record, arms, surface)
        REC.write_once_or_same(p.folder / P.DECISION_CHECKS, {
            "g_plumb": self.plumbing, "tolerances": self.tol_record, "c": self.c, "router_kind": self.kind,
            "gls_absent_reason": None, "gls": self.gls_record(), "fold_c": dict(self.fold_c),
            "neighbour": M._json_safe(routed.records["neighbour"]), "pools_file": pools_file,
            "corrector_coverage": {k: v for k, v in sorted(getattr(self, "corrector_coverage", {}).items())
                                   if k in ("fit-cut", "inner-cut")},
            "context_missing": routed.records.get("context_missing"),
            **({"score_context_missing": s1} if s1 is not None else {}),
            "surface_rows": int(record.n_rows), "surface_sha256": record.surface_sha256,
            "candidates": len(record.candidates),
            "surface_clip": {name: {"n_rows": cc.n_rows, "n_finite": cc.n_finite, "n_below": cc.n_below,
                                    "n_above": cc.n_above, "n_nan": cc.n_nan}
                             for name, cc in sorted(record.clip.items())},
            "inner_history": None, "inner_features": "the lead-0 table pool (no history block: R17 is empty)",
            **({"decline_baseline": {"key": REFERENCE_COLUMN, "rule": V1_RULE,
                                     "mae": record.decline_baseline["mae"],
                                     "per_fold_median": {pt.name: float(pt.median) for pt in parts}}}
               if v1 else {})})
        self.write_log_part("decision")
        self.adoption = record.adoption
        self.adoption_sha = lock_adoption(record.adoption, self.labels, p.folder)
        self._manifest_adoption()
        self._time(PHASE, t0)

    def _c_of_rows(self, parts: Sequence[PassPart], n: int) -> np.ndarray:
        out = np.full(n, np.nan)
        for pt in parts:
            out[np.asarray(pt.score_index, dtype=np.int64)] = np.nan if pt.c is None else float(pt.c)
        return out

    def _inverse_rows(self, z: np.ndarray, link: Any, c_rows: np.ndarray) -> np.ndarray:
        """Link space to y units, each row with its own fold's c (only log_c reads c)."""
        z = np.asarray(z, dtype=np.float64)
        if link != Link.LOG_C:
            return ST.inverse(z, link, None, self.ub)
        out = np.empty_like(z)
        for c in np.unique(c_rows):
            sel = c_rows == c
            out[sel] = ST.inverse(z[sel], link, float(c), self.ub)
        return out

    # ------------------------------------------------------------------ step 9: the test pass
    def test_rows(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The test rows (R18's scored rows: the package's test marks, U1) as (row positions, row ids, target days)
        in row-grid order."""
        test = np.flatnonzero(np.asarray(self.data.is_test, dtype=bool))
        rows = np.asarray(self.data.row_ids, dtype=object)
        return test.astype(np.int64), rows[test], np.asarray(self.data.target_day, dtype=np.int64)[test]

    def test_labels(self, tl: Any, units: np.ndarray, days: np.ndarray) -> np.ndarray:
        y_of = pd.Series(np.asarray(tl.y, dtype=np.float64),
                         index=pd.MultiIndex.from_arrays([np.asarray(tl.unit_ids, dtype=object),
                                                          np.asarray(tl.times, dtype=np.int64)]))
        return y_of.reindex(pd.MultiIndex.from_arrays([np.asarray(units, dtype=object),
                                                       np.asarray(days, dtype=np.int64)])).to_numpy(dtype=np.float64)

    def row_keys(self, positions: np.ndarray, units: np.ndarray, days: np.ndarray) -> Dict[str, np.ndarray]:
        """The saved rows' keys: unit = the row id, group, time = the target day, year, then the package-unit column
        and every stratum column under their catalog names (T-NAMES keeps them clear of the reserved names)."""
        spec = self.p.spec
        positions = np.asarray(positions, dtype=np.int64)
        keys = {"unit": np.asarray(units, dtype=object),
                "group": np.asarray([self.unit_group[str(u)] for u in units.tolist()], dtype=object),
                "time": np.asarray(days, dtype=np.int64), "year": years_of_days(days),
                spec.package_unit_col: np.asarray(self.data.units, dtype=object)[positions]}
        for c in spec.strata:
            v = np.asarray(self.data.strata[c])[positions]
            keys[c] = v
        return keys

    def test_pass(self) -> None:
        p = self.p
        t0 = time.time()
        a = self.adoption
        point = a.best_tree_penalty if a.declined else a.penalty
        point = P.RK.GridPoint(float(point.level), None if point.ratio is None else float(point.ratio))
        self._manifest_adoption()
        tl = self.labels.open_test_labels(self.adoption_sha, 0)
        t_keys, t_units, t_days = self.test_rows()
        y = self.test_labels(tl, t_units, t_days)
        keep, s1 = self.leave_out_score_context(REC.S1_TEST_PASS, self.ctx_fit, 0, t_keys, t_units, t_days, y)
        if s1 is not None:
            t_keys, t_units, t_days, y = t_keys[keep], t_units[keep], t_days[keep], y[keep]
        self.log("test pass: %d test rows (%d with a label); tree arms at level %r ratio %r (%s)"
                 % (t_keys.size, int(np.isfinite(y).sum()), point.level, point.ratio,
                    "the best tree arm's penalty: the layer declined" if a.declined else "the adopted penalty"))
        test_arms = [LA.ArmSpec(L, tool, w, True) for L in self.links for tool in P.TREE_TOOLS for w in self.weightings()]
        test_arms += [LA.ArmSpec(L, P.PLACEBO, w, False) for L in self.links for w in self.weightings()]
        part = PassPart(name="all", score_index=np.arange(t_keys.size, dtype=np.int64), c=self.c, model=self.weights,
                        fallback_donor=self.donor_fit)
        npass = NeighbourPass(self, REC.S1_TEST_PASS, self.ctx_fit, self.store_fit, self.bank_fit.tree_group, 0,
                              self.data.leads[0], t_keys, [part], self.tol)
        routed = npass.route(test_arms, point)
        pools_file = npass.save_pools(p.folder, "test_pass")
        arms, placebos, pre = {}, {}, {}
        for spec in test_arms:
            name = LA.arm_name(spec)
            p_pre = ST.inverse(routed.predictions[name][:, 0], spec.link, self.c, self.ub)
            (placebos if spec.tool is P.PLACEBO else arms)[name] = clip_to_legal(p_pre, self.legal, False)[0]
            pre[name] = p_pre
        for L in self.links:
            off = LA.arm_name(LA.trees_off_of(L))
            off_pre = ST.inverse(routed.trees_off[L], L, self.c, self.ub)
            arms[off] = clip_to_legal(off_pre, self.legal, False)[0]
            pre[off] = off_pre
        self.test_records = routed.records
        baselines = self.common_baselines(t_keys.size, self.median_fit)
        frame = M.assemble_rows(self.row_keys(t_keys, t_units, t_days), 0, t_days, y, np.full(t_keys.size, np.nan),
                                arms, placebos, pre, baselines, self.legal)
        path = p.folder / REC.TEST_PREDS
        if path.exists():
            if not M.read_rows(path).equals(frame):
                raise PassRefusal("G-FINGERPRINT", "%s exists with other rows" % path, fix="start a new run")
        else:
            M.write_rows_once(frame, path)
        self.n_test_rows = int(len(frame))
        doc = {"fit_cut_store": self.store_fit.record(),
               "inner_cut_store": (self.store_inner.record() if getattr(self, "store_inner", None) is not None
                                   else None),
               "schedule": "one table kind's dense answer matrix per neighbour pass at a time (owner item O20)"}
        REC.write_once_or_same(p.folder / "tables.json", doc)
        REC.write_once_or_same(p.folder / "test_pass_router.json", dict(
            {"router_kind": self.kind, "records": M._json_safe(routed.records), "pools_file": pools_file},
            **({"score_context_missing": s1} if s1 is not None else {})))
        self.write_log_part("test_pass")
        self._time(PHASE_T, t0)

    def common_baselines(self, n: int, median: float) -> Dict[str, np.ndarray]:
        """R31 for the neighbour kind: predict-zero and the donor-row median (clipped, R28)."""
        return {"predict_zero": M.baseline_predict_zero(n, self.legal),
                "donor_median": clip_to_legal(np.full(n, float(median)), self.legal, False)[0]}

    def decided_levels(self) -> Dict[str, Any]:
        return {}

    # ------------------------------------------------------------------ step 12: metrics
    def hit_tolerance(self) -> Any:
        """R32 for the neighbour kind: half the fit-cut donor rows' mean absolute deviation from the donor-row median
        (report.metrics.hit_tolerance), and the declared measurement-error floor."""
        if self.hit_tol is None:
            d = self.donor_fit
            ref = np.full(np.asarray(d.y).size, float(self.median_fit))
            floor = self.p.spec.measurement_error_floor
            self.hit_tol = (M.hit_tolerance(d, ref), float(floor) if floor else None)
        return self.hit_tol

    def _strata(self, preds: pd.DataFrame, tol: float, floor: Optional[float], kind: str) -> Dict[str, Any]:
        """R34 per declared stratum, per row: a string stratum is scored per value (owner item O18); a numeric
        stratum takes the grid's quartile edges from the fit-cut donor rows with a value (report.metrics.stratum_edges),
        test rows binned right-closed. Writes per_stratum.csv."""
        p = self.p
        if not p.spec.strata:
            return {}
        tables, records = [], {}
        rows = np.asarray(self.data.row_ids, dtype=object)
        for col in sorted(p.spec.strata):
            values = np.asarray(self.data.strata[col])
            of_row = pd.Series(values, index=pd.Index(rows, dtype=object))
            v = of_row.reindex(pd.Index(preds["unit"].to_numpy(dtype=object), dtype=object)).to_numpy()
            if values.dtype == object:
                ok = np.asarray([isinstance(x, str) and x != "" for x in v.tolist()], dtype=bool)
                sub = preds[ok].reset_index(drop=True).copy()
                sub["stratum"] = np.asarray(v[ok], dtype=object)
                table = M.score_table(sub, ("stratum",), tol, floor, kind)
                table.insert(0, "stratum_column", col)
                records[col] = {"kind": "string: scored per value (O18)", "values": sorted(set(sub["stratum"].tolist())),
                                "test_rows_without_value": int((~ok).sum()), "test_rows": int(ok.sum())}
            else:
                dpos = np.asarray([self.row_pos[str(u)] for u in np.asarray(self.donor_fit.unit_ids).tolist()],
                                  dtype=np.int64)
                dv = np.asarray(values, dtype=np.float64)[dpos]
                with_value = np.isfinite(dv)
                if not with_value.any():
                    raise PassRefusal("R34", "report stratum %r has no value on any donor row" % col)
                donor = self.ctx_fit.donor_rows("stratum_edges:%s" % col)
                edges = M.stratum_edges(donor, dv)
                vv = np.asarray(v, dtype=np.float64)
                ok = np.isfinite(vv)
                sub = preds[ok].reset_index(drop=True).copy()
                sub["stratum"] = M.stratum_bins(vv[ok], edges)
                table = M.score_table(sub, ("stratum",), tol, floor, kind)
                table.insert(0, "stratum_column", col)
                for i, e in enumerate(edges):
                    table["edge_q%d" % (25 * (i + 1))] = e
                records[col] = {"edges": list(edges), "donor_rows": int(donor.y.size),
                                "test_rows_without_value": int((~ok).sum()), "test_rows": int(ok.sum())}
            tables.append(table)
        REC.write_text_once_or_same(p.folder / P.PER_STRATUM, REC.csv_text(pd.concat(tables, ignore_index=True)))
        return records

    def report(self) -> Dict[str, Any]:
        """The grid report body (pipeline/passes.py RunState.report) with the table's hit tolerance and strata and
        its own verdict lines: the reference is the donor-row median (signed R34, G-DECIDE)."""
        p = self.p
        t0 = time.time()
        folder = p.folder
        preds = M.read_rows(folder / REC.TEST_PREDS)
        unscored = REC.check_scored_units(folder)
        if unscored:
            self.log("report: %d derived scored row(s) left with no scored row by S1: %s"
                     % (len(unscored), ", ".join(unscored[:20])))
        donor_only = donor_only_record(self.derived)
        if donor_only["count"]:
            self.log("report: %d donor-only group(s) (V6 b: no test row; trees and donor rows used, nothing scored): %s"
                     % (donor_only["count"], ", ".join(donor_only["groups"][:20])))
        tol, floor = self.hit_tolerance()
        kind = p.kind
        t_group = M.score_table(preds, ("group",), tol, floor, kind)
        t_year = M.score_table(preds, ("year",), tol, floor, kind)
        t_pooled = M.score_table(preds, (), tol, floor, kind)
        for name, table in (("score_by_group.csv", t_group), (P.PER_YEAR, t_year), ("score_pooled.csv", t_pooled)):
            REC.write_text_once_or_same(folder / name, REC.csv_text(table))
        strata = self._strata(preds, tol, floor, kind)
        self._preclip(preds)
        a = self.adoption
        declined = bool(a.declined)
        v1 = self.decline_to_donor_median()
        adopted_arm = LA.trees_off_of(Link.IDENTITY) if declined else a.adopted
        adopted_col = M.ARM_PREFIX + LA.arm_name(adopted_arm)
        adopted_name = LA.arm_name(adopted_arm)
        if declined and v1:
            # owner ruling V1: a declined nowcast adopts the donor-row median, the baseline its N2 used
            adopted_col, adopted_name = REFERENCE_COLUMN, V1_DECLINED_ADOPTED
        ref_col = REFERENCE_COLUMN
        scored_cols = [c for c in preds.columns if c.startswith((M.ARM_PREFIX, M.PLACEBO_PREFIX))] + [ref_col]
        per_group = {c: M.metric_by_key(t_group, c, "mae", "group") for c in scored_cols}

        def pooled(col):
            sel = t_pooled[(t_pooled["line"] == M.LINE_POOLED) & (t_pooled["column"] == col)
                           & (t_pooled["rows_basis"] == M.ROWS_BASIS_ALL)]
            return float(sel["mae"].iloc[0])
        pairs = []
        for L in self.links:
            off = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(L))
            for w in self.weightings():
                plain = M.ARM_PREFIX + LA.arm_name(LA.ArmSpec(L, LA.Tool.PLAIN, w, True))
                corr = M.ARM_PREFIX + LA.arm_name(LA.ArmSpec(L, LA.Tool.CORRECTOR, w, True))
                plac = M.PLACEBO_PREFIX + LA.arm_name(LA.ArmSpec(L, P.PLACEBO, w, False))
                pairs += [(off, plain), (off, corr), (plac, corr)]
        band, band_records = M.band_from_pairs(per_group, pairs)
        tagged = []
        for rec in band_records:
            groups = sorted(per_group[rec["reference"]])
            dv = np.array([per_group[rec["reference"]][g] - per_group[rec["arm"]][g] for g in groups])
            tag, _ = M.contrast_tag(dv, band)
            tagged.append(dict(rec, tag=tag.value))
        verdict = M.single_verdict(per_group[ref_col], per_group[adopted_col], pooled(ref_col), pooled(adopted_col),
                                   band, declined, M.REFERENCE_DONOR_ROW_MEDIAN)
        contrast = {g: per_group[ref_col][g] - per_group[adopted_col][g] for g in per_group[ref_col]}
        block_index = dict(p.blocks.block_of_group)
        blocked = M.blocked_jackknife(contrast, {g: block_index[g] for g in contrast})
        blocked_flag = M.blocked_jackknife_flag(verdict.contrast, blocked)
        # declined: the best tree arm's own trees-off under V1 (printed beside), the identity trees-off before it
        own_link = (a.best_tree_arm.link if v1 else Link.IDENTITY) if declined else a.adopted.link
        own_off = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(own_link))
        beside = {"identity_trees_off_mae": pooled(M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(Link.IDENTITY))),
                  "adopted_link_neighbour_trees_off_mae": pooled(own_off)}
        base_rows = t_pooled[(t_pooled["line"] == M.LINE_POOLED) & (t_pooled["column_kind"] == "baseline")]
        for _, r in base_rows.iterrows():
            beside["%s_mae@%s" % (r["column"], r["rows_basis"])] = float(r["mae"])
        members = {g: "+".join(p.blocks.members[i]) for g, i in block_index.items()}
        lines = []
        for g in sorted(per_group[adopted_col]):
            sub = preds[preds["group"] == g]
            n_units = int(sub["unit"].nunique())
            lines.append({"group": g, "scored_units": n_units, "test_rows": int(len(sub)),
                          "labelled_rows": int(np.isfinite(sub["y"].to_numpy(dtype=np.float64)).sum()),
                          "overlap_block": members[g], "mae_adopted": per_group[adopted_col][g],
                          "mae_reference": per_group[ref_col][g], "contrast": contrast[g],
                          "noise_note": P.NOISE_NOTE % n_units})
        REC.write_text_once_or_same(folder / "per_group.csv", REC.csv_text(pd.DataFrame(lines)))
        jk = [dict(r, kind="band_pair") for r in tagged]
        jk.append({"kind": "single_verdict", "reference": ref_col, "arm": adopted_col,
                   "mean": verdict.contrast.mean, "se": verdict.contrast.se, "low": verdict.contrast.low,
                   "high": verdict.contrast.high, "n_groups": verdict.contrast.n_groups, "tag": verdict.tag.value})
        jk.append({"kind": "blocked_jackknife (report only)", "reference": ref_col, "arm": adopted_col,
                   "mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                   "n_groups": blocked.n_groups, "tag": "flag: group jackknife may be too narrow" if blocked_flag else ""})
        REC.write_text_once_or_same(folder / "jackknife.csv", REC.csv_text(pd.DataFrame(jk)))
        checks = read_json(folder / P.DECISION_CHECKS)
        self._guard_report(checks, strata)
        rec = {"kind": kind, "package": p.package.dataset.name, "run_fingerprint": p.fingerprint,
               "draft": p.draft.record(), "headline_eligible": not p.not_headline,
               "not_headline_reasons": list(p.not_headline),
               "listed_in_reports": list(p.spec.listed_in_reports),
               "adopted": adopted_name, "adopted_column": adopted_col, "declined": declined,
               "penalty": None if a.penalty is None else {"level": a.penalty.level, "ratio": a.penalty.ratio},
               "best_tree_arm": LA.arm_name(a.best_tree_arm),
               "best_tree_penalty": {"level": a.best_tree_penalty.level, "ratio": a.best_tree_penalty.ratio},
               "adoption_sha256": self.adoption_sha, "reference": ref_col,
               "reference_rule": M.REFERENCE_DONOR_ROW_MEDIAN,
               **({"decline_target": REFERENCE_COLUMN, "decline_rule": V1_RULE} if v1 else {}),
               "verdict": M.verdict_record(verdict), "band": band,
               "band_source": "this run's own D75 contrasts (each tree arm vs its own trees-off, each corrector vs its "
                              "placebo; R35 derives the band from the package's first headline run)",
               "band_pairs": tagged, "blocked_jackknife": {"mean": blocked.mean, "se": blocked.se,
                                                           "low": blocked.low, "high": blocked.high,
                                                           "n_blocks": blocked.n_groups, "flag": blocked_flag},
               "pooled_mae_adopted": pooled(adopted_col), "pooled_mae_reference": pooled(ref_col),
               "beside": beside, "hit_tolerance": tol, "measurement_error_floor": floor,
               "n_groups": len(per_group[adopted_col]), "groups_trained": len(self.groups),
               DONOR_ONLY_KEY: donor_only, "scored_units": len(self.scored_units),
               "test_rows": int(len(preds)), "strata": strata, "router_kind": self.kind, "gls_arms": self.gls_record(),
               "tolerances": self.tol_record, "input": "table",
               P.TIMINGS_KEY: dict(self.timings, report=round(time.time() - t0, 2))}
        if p.draft.is_draft:
            rec = dict({"DRAFT": "DRAFT: %s -- never a headline number" % p.draft.stamp}, **rec)
        path = folder / REC.VERDICT_FILE
        if path.exists():
            if P._without(read_json(path), P.TIMINGS_KEY) != P._without(rec, P.TIMINGS_KEY):
                raise PassRefusal("G-FINGERPRINT", "%s exists with another verdict" % path, fix="start a new run")
        else:
            M.write_json_once(rec, path)
        self.log("verdict: %s adopted %s vs %s: contrast %.6g [%.6g, %.6g], band %.6g, pooled MAE %.6g vs %.6g"
                 % (verdict.tag.value, rec["adopted"], ref_col, verdict.contrast.mean, verdict.contrast.low,
                    verdict.contrast.high, band, rec["pooled_mae_adopted"], rec["pooled_mae_reference"]))
        return {"verdict": verdict.tag.value, "adopted": rec["adopted"], "band": band,
                "pooled_mae_adopted": rec["pooled_mae_adopted"], "pooled_mae_reference": rec["pooled_mae_reference"],
                "draft": p.draft.is_draft, "test_rows": rec["test_rows"]}


__all__ = ["TableRunState", "years_of_days", "REFERENCE_COLUMN", "FOLD_GLS_FILE", "V1_RULE", "V1_DECLINED_ADOPTED",
           "DONOR_ONLY_KEY", "donor_only_record"]
