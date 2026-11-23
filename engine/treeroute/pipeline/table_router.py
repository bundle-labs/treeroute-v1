"""The neighbour pass of the table option: one router pass of the neighbour kind over a table's rows.

Owner ruling U (the owner rulings file, section U: U3 the donor-row median fallback, U4 the strict pool);
design in SPEC_TABLE_MODE.md 3.8 and 4.0-4.4. Orchestration only: every rule is its approved module's. The pool,
the drop set, Z, the local fit, the trees-off and the dense answer matrix are route/neighbour.py's (the neighbour
kind's module); the scalers are route/kinds.py's; owner ruling G1 is pipeline/stages.py's; the links are
layer/links.py's; the GLS weights are fit/weights.py's. This module feeds them the pass's arrays and checks what
it hands over.

One pass (NeighbourPass), on one FitContext (its bank cut is the pass's HORIZON, signed R14), one tree-answer
store, one lead's table:
  1  candidates: ctx.router_rows(every train row present at the lead) (train rows with a valid label at or before
     the cut, logged with the lead); owner ruling G1 on them (stages.drop_missing_context; the kept rows' log twin;
     the rows left out saved under context_missing/);
  2  the scored rows' issue days from the lead table's key_issue column (asserted: target day minus the lead); the
     context, its router rows and its feature pool must be at the pass's lead (R11), so features of one lead never
     meet the issue days of another;
  3  the context scalers on the candidates (route.kinds.router_standardisation), applied to both sides;
  4  Z on the candidates (route.neighbour.pool_feature_z), applied to both sides;
  5  per PART (the decision surface: one part per fold, R13; every other pass: one part): the part's c, GLS model
     and fallback median (the donor-row median of the part's bank DonorRows, U3); the constant assert: every row
     a per-pass constant is fitted on is dated at or before the horizon (G-FITCUT);
  6  the pools of the part's rows (route.neighbour.neighbour_pools: the strict pool of U4 and the drop set), fixed
     before any solve and shared by every arm;
  7  the dense answer matrix of each table kind over every candidate and scored row (route.neighbour.dense_answers,
     after the store builds them), one kind at a time, after a RAM wait (owner ruling Q1);
  8  per arm: the kernel (_route_neighbour_grid on the decision surface, _route_neighbour_at at one point), with the
     arm's link of y (the part's c) and, for a GLS arm, the candidates' weights (fit.weights.weights_for_rows);
  9  the saved pools (pools_<pass>.parquet: the scored row, its pool's row ids in pool order, the drop set, the
     fallback flag) and a RoutedPass (pipeline/router.py's record: link-space predictions, trees-off per link);
 10  on the decision surface, G-PLUMB (layer.decide.check_plumbing): each link's trees-off against an independent
     closed-form ridge of the same pool (owner item O10; the pair keeps its grid name trees_off_equals_normal, with
     a neighbour note), and the R14 base point's column against a one-point solve at it.
No partial pass is checkpointed; a resumed run recomputes the pass and its write-once outputs must be equal.
"""
# Provenance for the module: SPEC_TABLE_MODE.md 3.8, 4.0, 4.4; SPEC_NEIGHBOUR.md 1-7; route/neighbour.py (the
# kernels); pipeline/router.py RoutedPass (the pass record the run state reads); OWNER_RULINGS_2026-09-28.md G1;
# OWNER_RULINGS_2026-10-06.md U3, U4, Q1.

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.shapes import Link
from treeroute.errors import RefusedError
from treeroute.layer import arms as LA
from treeroute.layer.links import link_forward
from treeroute.report import metrics as M
from treeroute.route import kinds as RK

from . import router as PR
from . import stages as ST

NEIGHBOUR_PLUMB_NOTE = ("G-PLUMB for the neighbour kind (owner item O10): pair 1 keeps its grid name "
                        "trees_off_equals_normal but compares the neighbour trees-off with an independent closed-form "
                        "ridge of [intercept, context] on the same pool at the R14 base point; the kind has no normal")
POOLS_FILE = "pools_%s.parquet"


class NeighbourPassRefusal(RefusedError):
    """A neighbour pass refused (fail loudly)."""


@dataclass
class PassPart:
    """One part of a pass: its scored rows (indices into the pass's scored rows), its c (log_c's, or None), its GLS
    weight model (or None), its fallback donor rows (DonorRows at or before the pass's cut) and, on the decision
    surface, its fold index and group."""
    name: str
    score_index: np.ndarray
    c: Optional[float]
    model: Any
    fallback_donor: Any
    fold: Optional[int] = None


def _slug(what: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(what).lower()).strip("_")


def _link_args(link: Any, c: Optional[float], ub: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    return (c if link == Link.LOG_C else None), (ub if link == Link.ARCSINE else None)


class NeighbourPass(object):
    """One neighbour pass (module docstring). state: the table run state (p, derived, links, ub, tol, kind);
    ctx: the pass's FitContext (its cut is the horizon); store and tree_group: the pass's bank's tree-answer store
    and its trees' groups; lead: the lead in days; lead_table: package/table.LeadTable of that lead; score_pos: the
    scored rows' row positions (pass order); parts: PassPart list covering every scored row once."""

    def __init__(self, state: Any, what: str, ctx: Any, store: Any, tree_group: Sequence[str], lead: int,
                 lead_table: Any, score_pos: np.ndarray, parts: Sequence[PassPart], tol: Mapping[Any, float]) -> None:
        from treeroute.route import neighbour as NB

        self.NB = NB
        self.s = state
        self.p = state.p
        self.what = str(what)
        self.ctx = ctx
        self.store = store
        self.tree_group = tuple(str(g) for g in tree_group)
        self.lead = int(lead)
        self.table = lead_table
        self.tol = dict(tol)
        self.parts = list(parts)
        self.purpose = "neighbour_pool:%s" % _slug(self.what)
        data = self.p.table
        self.data = data
        self.score_pos = np.asarray(score_pos, dtype=np.int64)
        covered = np.sort(np.concatenate([np.asarray(pt.score_index, dtype=np.int64) for pt in self.parts])) \
            if self.parts else np.zeros(0, np.int64)
        if not np.array_equal(covered, np.arange(self.score_pos.size, dtype=np.int64)):
            raise NeighbourPassRefusal("R13", "internal: %s: the parts do not cover every scored row once" % self.what)
        self._prepare()

    # ------------------------------------------------------------------ steps 1-5
    def _prepare(self) -> None:
        s, p, data, ctx = self.s, self.p, self.data, self.ctx
        # one lead throughout (R11; FIX_REPORT.md, leakage review item 2): the context, the feature pool it reads and
        # the lead table the issue days come from
        ctx_lead = int(ctx.lead)
        pool_lead = getattr(ctx.features, "lead", None)
        table_lead = getattr(self.table, "lead", None)
        for what_lead, value in (("context", ctx_lead), ("feature pool", pool_lead), ("lead table", table_lead)):
            if value is not None and int(value) != self.lead:
                raise NeighbourPassRefusal("R11", "%s: the %s is at lead %d, the pass at lead %d"
                                           % (self.what, what_lead, int(value), self.lead))
        rows = np.asarray(data.row_ids, dtype=object)
        present = np.asarray(self.table.present, dtype=bool)
        train = present & ~np.asarray(data.is_test, dtype=bool)
        raw = ctx.router_rows(tuple(rows[train].tolist()), self.purpose)
        if int(raw.lead) != self.lead:
            raise NeighbourPassRefusal("R11", "%s: the router rows are at lead %d, the pass at lead %d"
                                       % (self.what, int(raw.lead), self.lead))
        cols = tuple(ctx.features.context_columns)
        fit, self.g1, left = raw, None, None
        if cols:
            fit, self.g1, left = ST.drop_missing_context(raw, cols)
            if fit is not raw:
                s.log_g1_kept(ctx, (ST.g1_kept_log_row(ctx, "router_rows", self.purpose, raw.unit_ids, raw.times,
                                                       fit.unit_ids, fit.times),))
            if left is not None:
                self.g1["rows_file"] = s.save_context_missing_rows(self.what, left.frame(self.what, self.purpose))
        self.cand = fit
        cut = int(ctx.cut)
        cpos = np.asarray(fit.row_positions, dtype=np.int64)
        ctimes = np.asarray(fit.times, dtype=np.int64)
        if cpos.size == 0:
            raise NeighbourPassRefusal("R14", "%s: no candidate row at the cut %d" % (self.what, cut))
        if int(ctimes.max()) > cut:
            raise RK.RouteGuardError("G-FITCUT: %s: a candidate is dated after the pass's cut" % self.what)
        if (np.asarray(data.is_test, dtype=bool)[cpos]).any() or not present[cpos].all():
            raise RK.RouteGuardError("G-FITCUT: %s: a candidate is a test row or absent at lead %d" % (self.what, self.lead))
        sp = self.score_pos
        if not present[sp].all():
            raise NeighbourPassRefusal("H4", "internal: %s: a scored row is absent at lead %d" % (self.what, self.lead))
        issue = np.asarray(self.table.issue_day, dtype=np.int64)[sp]
        target = np.asarray(data.target_day, dtype=np.int64)[sp]
        if not np.array_equal(issue, target - self.lead):
            raise NeighbourPassRefusal("R11", "T-ISSUE (run time): %s: a scored row's issue day is not its target day "
                                       "minus %d" % (self.what, self.lead))
        self.issue = issue
        if sp.size and int(ctimes.max()) > int(issue.min()):
            raise RK.RouteGuardError("G-FITCUT: %s: the newest candidate (%d) is after the earliest scored issue day "
                                     "(%d)" % (self.what, int(ctimes.max()), int(issue.min())))
        self.cand_ctx = self.score_ctx = None
        self.scalers = None
        if cols:
            mean, sd = RK.router_standardisation(fit, fit.context)
            self.cand_ctx = RK.standardise_context(fit.context, mean, sd)
            sc = np.asarray(ctx.features.context(sp), dtype=np.float64)
            ST.check_score_context(sc, rows[sp], target, cols, self.what)
            self.score_ctx = RK.standardise_context(sc, mean, sd)
            self.scalers = {"mean": mean.tolist(), "sd": sd.tolist(), "rows": int(cpos.size)}
        cf = np.asarray(ctx.features.tree_features(cpos), dtype=np.float64)
        sf = np.asarray(ctx.features.tree_features(sp), dtype=np.float64)
        self.cand_z, self.score_z, zm, zs = self.NB.pool_feature_z(cf, sf, ctimes, cut)
        n_const = self.NB.constant_z_columns(self.cand_z)
        groups = np.asarray(data.groups, dtype=object)
        self.cand_arrays = {"keys": cpos, "day": ctimes, "unit": rows[cpos], "group": groups[cpos],
                            "lat": np.asarray(data.lat, dtype=np.float64)[cpos],
                            "lon": np.asarray(data.lon, dtype=np.float64)[cpos],
                            "y": np.asarray(fit.y, dtype=np.float64)}
        self.score_arrays = {"keys": sp, "unit": rows[sp], "group": groups[sp],
                             "lat": np.asarray(data.lat, dtype=np.float64)[sp],
                             "lon": np.asarray(data.lon, dtype=np.float64)[sp]}
        is_test = np.asarray(data.is_test, dtype=bool)
        for pt in self.parts:                       # the constant assert (SPEC_TABLE_MODE.md 2.3)
            d = pt.fallback_donor
            # owner ruling V1 makes this median the decline target and the guard baseline of the neighbour kind, so
            # its rows are checked by MARK as well as by date (REVIEW v1 item 2): a bank holds every row of its groups
            # (derive/table.py R18_TABLE) and only the date filter of FitContext.donor_rows keeps test rows out
            if is_test[np.asarray(d.grid_rows, dtype=np.int64)].any():
                raise RK.RouteGuardError("G-FITCUT: %s, part %s: a fallback donor row (the donor-row median's rows, "
                                         "owner ruling V1) is a test row" % (self.what, pt.name))
            newest = [int(np.asarray(d.times).max())]
            if pt.model is not None:
                newest.append(int(pt.model.cut))
            if max(newest) > cut:
                raise RK.RouteGuardError("G-FITCUT: %s, part %s: a per-pass constant was fitted on a row dated %d, after "
                                         "the pass's cut %d" % (self.what, pt.name, max(newest), cut))
            pt.median = float(M.baseline_donor_median(d))
        self.constants = {"cut": cut, "lead": self.lead, "candidates": int(cpos.size),
                          "newest_candidate_day": int(ctimes.max()),
                          "earliest_scored_issue_day": int(issue.min()) if issue.size else None,
                          "z_rows": int(cpos.size), "z_constant_columns": int(n_const),
                          "context_scalers": self.scalers,
                          "parts": {pt.name: {"c": pt.c, "median": pt.median, "fold": pt.fold,
                                              "fallback_rows": int(np.asarray(pt.fallback_donor.y).size),
                                              "fallback_newest_day": int(np.asarray(pt.fallback_donor.times).max()),
                                              "gls_model_cut": None if pt.model is None else int(pt.model.cut)}
                                    for pt in self.parts}}
        self.pools: Dict[str, Any] = {}
        self.answers: Dict[str, Any] = {}

    # ------------------------------------------------------------------ rows of one part and arm
    def _rows(self, pt: PassPart, link: Any, weighted: bool) -> Any:
        NB = self.NB
        idx = np.asarray(pt.score_index, dtype=np.int64)
        c, ub = _link_args(link, pt.c, self.s.ub)
        y_link = link_forward(self.cand_arrays["y"], link, c, ub)
        w = None
        if weighted:
            if pt.model is None:
                raise NeighbourPassRefusal("R25", "%s, part %s: a GLS arm needs the part's weight model" % (self.what, pt.name))
            from treeroute.fit.weights import weights_for_rows

            keys = self.cand_arrays["keys"]
            w = weights_for_rows(pt.model, keys, ST.zero_filled(self.ctx.features)(keys))
        fb = float(link_forward(np.asarray([pt.median], dtype=np.float64), link, c, ub)[0])
        ca, sa = self.cand_arrays, self.score_arrays
        return NB.NeighbourRows(
            cut=int(self.ctx.cut), lead=self.lead, cand_keys=ca["keys"], cand_day=ca["day"], cand_unit=ca["unit"],
            cand_group=ca["group"], cand_lat=ca["lat"], cand_lon=ca["lon"], cand_z=self.cand_z,
            cand_ctx=self.cand_ctx, cand_y_link=y_link, cand_w=w, score_keys=sa["keys"][idx],
            score_unit=sa["unit"][idx], score_issue=self.issue[idx], score_group=sa["group"][idx],
            score_lat=sa["lat"][idx], score_lon=sa["lon"][idx], score_z=self.score_z[idx],
            score_ctx=None if self.score_ctx is None else self.score_ctx[idx], score_rows=idx,
            fallback_link=np.full(idx.size, fb, dtype=np.float64))

    def _pools(self, pt: PassPart) -> Any:
        if pt.name not in self.pools:
            rows = self._rows(pt, Link.IDENTITY, False)
            self.pools[pt.name] = self.NB.neighbour_pools(rows, self.p.blocks)
        return self.pools[pt.name]

    def _answers(self, kind: str) -> Any:
        """The dense answer matrix of one table kind over every candidate and scored row (step 7); one kind is
        held at a time."""
        if kind in self.answers:
            return self.answers[kind]
        self.answers.clear()
        keys = np.unique(np.concatenate([self.cand_arrays["keys"], self.score_arrays["keys"]]))
        groups = np.asarray(self.data.groups, dtype=object)[keys]
        need = int(keys.size) * len(self.tree_group) * 4 * 2
        self.p._refuse_ram(need, "the neighbour pass %s's answer matrix (%d rows x %d trees, one table kind)"
                           % (self.what, keys.size, len(self.tree_group)), wait=True)
        feats = ST.zero_filled(self.ctx.features)
        for g in sorted(set(groups.tolist())):
            self.store.build(g, kind, keys[groups == g], feats)
        self.answers[kind] = self.NB.dense_answers(self.store, kind, keys, groups, self.tree_group)
        return self.answers[kind]

    # ------------------------------------------------------------------ steps 6-10
    def route(self, arms: Sequence[Any], point: Any = None, extra_trees_off: Sequence[Any] = (),
              plumbing: bool = False) -> PR.RoutedPass:
        """Every arm of the pass in link space: on the decision surface (point None) every grid point of R14; else
        the one point. The trees-off of every routed link and of extra_trees_off. Returns a RoutedPass."""
        NB = self.NB
        design = self.s.derived["R14"].value
        m = self.score_pos.size
        grid = tuple(RK.GridPoint(float(g.level), None if g.ratio is None else float(g.ratio)) for g in design.grid) \
            if point is None else (RK.GridPoint(float(point.level), None if point.ratio is None else float(point.ratio)),)
        out = PR.RoutedPass(grid=grid)
        records: Dict[str, Any] = {}
        kinds = []
        for a in arms:
            k = LA.table_kind(a)
            if k not in kinds:
                kinds.append(k)
        off_from: Dict[Any, np.ndarray] = {}
        for kind in kinds:
            answers = self._answers(kind)
            for a in [x for x in arms if LA.table_kind(x) == kind]:
                name = LA.arm_name(a)
                pred = np.full((m, len(grid)), np.nan)
                off = np.full(m, np.nan)
                recs = {}
                for pt in self.parts:
                    rows = self._rows(pt, a.link, a.weighting is LA.Weighting.GLS)
                    pools = self._pools(pt)
                    tol = float(self.tol[a.link])
                    if point is None:
                        ro, rec = NB._route_neighbour_grid(rows, answers, self.tree_group, self.p.blocks, design, tol,
                                                           pools=pools)
                    else:
                        ro, rec = NB._route_neighbour_at(rows, answers, self.tree_group, self.p.blocks, design, point,
                                                         tol, pools=pools)
                    idx = np.asarray(ro.row_positions, dtype=np.int64)
                    pred[idx] = np.asarray(ro.predictions, dtype=np.float64)
                    off[idx] = np.asarray(ro.trees_off, dtype=np.float64)
                    recs[pt.name] = {k: v for k, v in rec.items() if k != "per_row"}
                if not (np.isfinite(pred).all() and np.isfinite(off).all()):
                    raise NeighbourPassRefusal("G-PLUMB", "%s: arm %s left a scored row without a prediction" % (self.what, name))
                out.predictions[name] = pred
                if a.weighting is LA.Weighting.UNWEIGHTED and a.link not in off_from:
                    off_from[a.link] = off
                records[name] = recs
        for L in list(dict.fromkeys([a.link for a in arms] + list(extra_trees_off))):
            if L in off_from:
                out.trees_off[L] = off_from[L]
                continue
            off = np.full(m, np.nan)
            for pt in self.parts:
                rows = self._rows(pt, L, False)
                vals, _, _ = NB._trees_off_neighbour_pass(rows, self.p.blocks, pools=self._pools(pt))
                off[np.asarray(pt.score_index, dtype=np.int64)] = vals
            out.trees_off[L] = off
        out.records = {"neighbour": {"pass": self.what, "constants": self.constants, "g1": self.g1,
                                     "arms": records, "pools": self._pool_summary()},
                       "context_missing": self.g1}
        if plumbing:
            out.plumbing = self._plumbing(arms, out)
        return out

    def fallback_median_rows(self) -> np.ndarray:
        """Owner ruling V1 (the owner rulings file, section V): each scored row's part median (pt.median, the
        donor-row median of the part's fallback DonorRows, U3; set in _prepare), in y units, rows in pass order.
        The neighbour kind's guard and decline baseline is this same object, so the check and the fallback are one
        object. Refuses a part whose median is not set."""
        out = np.full(self.score_pos.size, np.nan)
        for pt in self.parts:
            med = getattr(pt, "median", None)
            if med is None or not np.isfinite(float(med)):
                raise NeighbourPassRefusal("V1", "internal: %s, part %s: no donor-row median" % (self.what, pt.name))
            out[np.asarray(pt.score_index, dtype=np.int64)] = float(med)
        if not np.isfinite(out).all():
            raise NeighbourPassRefusal("V1", "internal: %s: a scored row has no part median" % self.what)
        return out

    def _pool_summary(self) -> Dict[str, Any]:
        sizes, fallback, drops = [], 0, []
        for pt in self.parts:
            pools = self._pools(pt)
            for idx, d in zip(pools.index, pools.drop):
                if idx is None:
                    fallback += 1
                else:
                    sizes.append(int(idx.size))
                drops.append(len(d))
        return {"rows": int(self.score_pos.size), "rows_with_pool": len(sizes), "rows_pool_fallback": int(fallback),
                "pool_size_median": float(np.median(sizes)) if sizes else None,
                "drop_set_size_median": float(np.median(drops)) if drops else None}

    def save_pools(self, folder: Any, name: str) -> str:
        """pools_<pass>.parquet (write once; a resumed pass must save the same rows): per scored row, its row id,
        its pool's row ids in pool order (JSON), its drop groups (JSON), the fallback flag, the part."""
        from .passes import _write_parquet_once

        rows = np.asarray(self.data.row_ids, dtype=object)
        frames = []
        for pt in self.parts:
            rec = self.NB.pool_records(self._rows(pt, Link.IDENTITY, False), self._pools(pt))
            frames.append(pd.DataFrame({
                "order": np.asarray(pt.score_index, dtype=np.int64),
                "row_id": rows[np.asarray(rec["score_key"], dtype=np.int64)],
                "issue_day": self.issue[np.asarray(pt.score_index, dtype=np.int64)],
                "pool_row_ids": [json.dumps(rows[np.asarray(k, dtype=np.int64)].tolist()) for k in rec["pool_keys"]],
                "drop_groups": [json.dumps(list(d)) for d in rec["drop_groups"]],
                "pool_fallback": np.asarray(rec["pool_fallback"], dtype=bool),
                "part": np.full(len(rec["drop_groups"]), pt.name, dtype=object)}))
        frame = pd.concat(frames, ignore_index=True).sort_values("order", kind="stable").reset_index(drop=True)
        frame = frame.drop(columns=["order"])
        fname = POOLS_FILE % _slug(name)
        _write_parquet_once(frame, folder / fname)
        return fname

    # ------------------------------------------------------------------ step 10: G-PLUMB
    def _closed_form_trees_off(self, pt: PassPart, link: Any) -> np.ndarray:
        """An independent closed-form ridge of [intercept, standardised context] on each row's pool at the R14 base
        point (intercept unpenalised, the context block trace-normalised on its own columns, no jitter); the pool
        mean without context; the fallback for a row with no pool."""
        rows = self._rows(pt, link, False)
        pools = self._pools(pt)
        y = np.asarray(rows.cand_y_link, dtype=np.float64)
        has_ctx = rows.cand_ctx is not None
        a_ctx = float(K.NEIGHBOUR_CONTEXT_CENTRE)             # a_tree x ratio at level 1 = the context centre
        out = np.empty(len(pools.index))
        for i, idx in enumerate(pools.index):
            if idx is None:
                out[i] = rows.fallback_link[i]
                continue
            yy = y[idx]
            if not has_ctx:
                out[i] = float(yy.mean())
                continue
            C = np.asarray(rows.cand_ctx, dtype=np.float64)[idx]
            X = np.column_stack([np.ones(idx.size), C])
            G = X.T @ X
            nctx = C.shape[1]
            tr = float(np.trace(G[1:, 1:])) / nctx
            G[1:, 1:] += np.eye(nctx) * a_ctx * tr
            b = np.linalg.solve(G, X.T @ yy)
            out[i] = float(np.r_[1.0, np.asarray(rows.score_ctx, dtype=np.float64)[i]] @ b)
        return out

    def _plumbing(self, arms: Sequence[Any], routed: Any) -> Dict[str, Any]:
        from treeroute.layer import decide as LD

        NB = self.NB
        design = self.s.derived["R14"].value
        base = NB.neighbour_base_point(self.cand_ctx is not None)
        k = list(routed.grid).index(base)
        out: Dict[str, Any] = {"note": NEIGHBOUR_PLUMB_NOTE}
        for L in list(dict.fromkeys(a.link for a in arms)):
            plain = [a for a in arms if a.link == L and a.tool is LA.Tool.PLAIN and a.weighting is LA.Weighting.UNWEIGHTED]
            if not plain:
                continue
            a = plain[0]
            m = self.score_pos.size
            ref = np.empty(m)
            unswept = np.empty(m)
            answers = self._answers(LA.table_kind(a))
            for pt in self.parts:
                idx = np.asarray(pt.score_index, dtype=np.int64)
                ref[idx] = self._closed_form_trees_off(pt, L)
                rows = self._rows(pt, L, False)
                ro, _ = NB._route_neighbour_at(rows, answers, self.tree_group, self.p.blocks, design, base,
                                               float(self.tol[L]), pools=self._pools(pt))
                unswept[np.asarray(ro.row_positions, dtype=np.int64)] = np.asarray(ro.predictions)[:, 0]
            res = LD.check_plumbing(routed.trees_off[L], ref, routed.predictions[LA.arm_name(a)][:, k], unswept,
                                    None, None, None, None, float(self.tol[L]))
            if res.status is LD.GuardStatus.BLOCK:
                raise NeighbourPassRefusal("G-PLUMB", "%s %s: %s (%s)" % (self.what, getattr(L, "value", L), res.reason,
                                                                         res.details))
            out[getattr(L, "value", str(L))] = dict(res.details)
        return out


__all__ = ["NeighbourPass", "PassPart", "NeighbourPassRefusal", "NEIGHBOUR_PLUMB_NOTE", "POOLS_FILE"]
