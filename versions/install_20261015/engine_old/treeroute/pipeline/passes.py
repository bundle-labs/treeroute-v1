"""The heavy steps of one pipeline run (plan 4.1 steps 3-9 and 12), on a Pipeline that has loaded the
package, derived derived.json and opened its run folder (pipeline.run).

RunState holds the in-memory objects of one process (the vault, the feature pool, the banks, the
tree-answer stores) and releases every temp file on exit (the pools and the stores' memmaps: references
dropped, gc, loud delete). Nothing here decides a number: every rule is its approved module's (see
pipeline.stages), and every row-level prediction is saved (test_preds.parquet holds every arm, every
placebo, every baseline, the pre-clip values and the normal; inner_preds.parquet every decision-surface
candidate, clipped and before the clip, with the surface's labels).

Every pass routes through pipeline.router (the run's router kind, R12): the per-unit kind routes every R24
arm, the GLS-weighted ones included (route.solve's weighted solve, a new formula for the owner's review;
weights from fit.weights.weights_for_rows on the features the weight model was fitted on), with the region
fallback for short-history units; the region kind routes the unweighted arms by group and declares why its
GLS arms are absent (and fits no weight model). The forecast ladder (pipeline.ladder) runs on this state
after the report.

The inner decision (L6 b) is made as if the run stood at the INNER cut: its bank is refit at the guard
cut, and its features carry an own-history block built at the guard cut (the fallbacks of R17 read the
unit histories and the donor-row mean at the guard cut, never a label in (guard cut, fit cut]). The
test pass and the GLS weight model read the fit-cut features.

The nowcast's two banks are released as soon as nothing reads them (release_bank): the inner-cut bank and its
store when the forecast ladder starts (after the test pass's tables.json record), the fit-cut bank and its
store once the ladder's lead-0 contract is done (or found done on resume). So while a lead's guard runs, the
banks in memory are that lead's two (its fit-cut bank and its H2 guard-cut bank), as many as the nowcast's
decision holds (fit-cut and inner-cut), never four.

Per-group batching (plan R20, the pipeline's default; Pipeline(per_group=False) is the whole-frame path kept
for the byte-identity gates only): the pool is filled group by group from the picked units' column readers
built one group at a time (pipeline/stream.py GroupReaders); the GLS weight model releases each group's
donor-row table as soon as it is read (fit.tables.DropAfterRead); the banks read their donor rows' features one
group at a time (FitContext.donor_rows_lazy: fit.bank reads each group's rows alone); every router pass walks the groups with one
group's tables on disk at a time (pipeline/router.py GroupTables): its scored-unit rows are built before the
group is routed and every table of the group is dropped after it. Rows a later pass needs again are computed
again (the same bytes): the test pass recomputes the scored units' rows the weight model built, and the
forecast ladder's lead-0 contract recomputes its pinned table (and, for a weighted pin, the lead-0 weight
model's donor rows); for a weighted PLAIN pin, the contract's and every lead's pinned table also recompute the
scored units' rows that cut's weight model built. No other pass re-reads a dropped table. tables.json then
lists the nowcast stores' dropped tables and the schedule (the ladder's builds are not listed in either path).

FitContext hand-outs are logged per part as they happen: phases/setup_with_inner/ (the pool and the fits
of a process that makes the decision), phases/setup/ (a process that resumes after the lock), then
phases/decision/, phases/test_pass/, phases/report/, each fitctx_log.parquet written before its phase is
marked done (the decision's before the adoption is locked). fitctx_log.parquet at the end is their
concatenation. Owner ruling G1's log twins (stages.g1_kept_log_row: the rows a trimmed hand-out kept) are
written right after their hand-out's own row, and the fit rows G1 leaves out are saved per pass in
context_missing/<pass>.parquet (only for a pass that left a row out).
"""

import gc
import json
import re
import time
import weakref
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind, Link
from treeroute.errors import RefusedError
from treeroute.fit.bank import fit_donor_bank
from treeroute.fit.context import FitContext, log_records, season_keys_of
from treeroute.fit.pool import open_pool
from treeroute.fit.tables import DropAfterRead, TreeAnswerStore
from treeroute.fit.weights import weight_model_for_cut, weight_model_record, weights_for_rows
from treeroute.io.steps import step_bounds
from treeroute.labels.vault import ADOPTION_FILE, LOCK_SUFFIX, OPENED_FILE, lock_adoption
from treeroute.layer import arms as LA
from treeroute.layer import decide as LD
from treeroute.layer.links import c_for_cut_against_plan, clip_to_legal
from treeroute.report import metrics as M
from treeroute.route import kinds as RK
from treeroute.runs.atomic import dumps, read_json

from . import record as REC
from . import router as PR
from . import stages as ST
from .data import _years_of_steps

PLACEBO = LA.Tool.PLACEBO_CORRECTOR
BANK_FIT = "fit-cut"                               # the nowcast's banks, by the names release_bank takes
BANK_INNER = "inner-cut"
BANK_ATTRS = {BANK_FIT: ("bank_fit", "store_fit", "masks_fit"),
              BANK_INNER: ("bank_inner", "store_inner", "masks_inner")}
TREE_TOOLS = (LA.Tool.PLAIN, LA.Tool.CORRECTOR)
NOISE_NOTE = ("one group's score is noisy (%d scored units); the pooled headline and the all-group "
              "jackknife decide, never one group (R34)")
MANIFEST_ADOPTION = "manifest_adoption.json"
FITCTX_LOG = "fitctx_log.parquet"
LOG_PARTS = ("setup_with_inner", "setup", "decision", "test_pass", "report")
G1_LOG_MARK = "|g1_kept"                           # the write mark of a context's G1 log twins
# the forecast ladder's parts follow, in lead order (pipeline.ladder.log_parts)
PER_YEAR, PER_STRATUM, PRECLIP, GUARD_REPORT = "per_year.csv", "per_stratum.csv", "preclip.csv", "guard_report.json"
POOL_FILL_ROWS = K.POOL_FILL_ROWS   # rows per pool write in a per-group fill (engine constant P4.pool_fill_rows)
TABLE_SCHEDULE_RULE = ("plan R20 per-group batching: every router pass walks the groups in sorted order; a group's "
                       "scored-unit rows (and its bank rows when it is a fallback group or the kind is region) are "
                       "built right before the group is routed and every table of the group is dropped right after "
                       "it; the GLS weight model drops each group's donor-row table once read; rows a later pass "
                       "needs again are computed again (the same bytes); dropped_tables lists every table released")
DECISION_CHECKS = "decision_checks.json"
CONTEXT_MISSING_DIR = "context_missing"            # owner ruling G1: the fit rows each pass left out
TIMINGS_KEY = "timings_seconds"
NOT_RUN_GUARDS = ("the quick and deep checks of plan 5 are not built (treeroute/check): G-CADENCE, G-DERIVED "
                  "recompute, G-LINEAGE (only the feature script's sources are checked against the verdicts), "
                  "G-EPOCH, G-RANGE, G-MISSING flags beyond R30's shares, G-KEYS, G-HIST static scan, G-NODRAW, "
                  "G-SUPPORT, G-FACTS; G-CLOSED is enforced when the verdicts are applied")


class PassRefusal(RefusedError):
    """A pipeline pass refused (fail loudly)."""


def _write_parquet_once(frame: pd.DataFrame, path: Path) -> None:
    """Write a parquet file once (a new name, never overwritten); on a resumed pass an existing file
    must hold the same rows."""
    import os

    if path.exists():
        old = pd.read_parquet(path)
        if not (list(old.columns) == list(frame.columns) and old.reset_index(drop=True).equals(
                frame.reset_index(drop=True))):
            raise PassRefusal("G-FINGERPRINT", "%s exists with other rows; a resumed pass never changes saved "
                              "rows" % path, fix="start a new run")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp_%d" % os.getpid())
    with open(tmp, "xb") as fh:
        frame.to_parquet(fh, index=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.rename(str(tmp), str(path))


def _tool_kind(tool: Any) -> str:
    return {LA.Tool.PLAIN: "plain", LA.Tool.CORRECTOR: "corrector", PLACEBO: "placebo_corrector"}[tool]


def _arm_doc_spec(doc: Optional[Mapping[str, Any]]) -> Optional[LA.ArmSpec]:
    if doc is None:
        return None
    return LA.ArmSpec(link=Link(doc["link"]), tool=LA.Tool(doc["tool"]), weighting=LA.Weighting(doc["weighting"]),
                      selectable=bool(doc["selectable"]))


def _point_doc(doc: Optional[Mapping[str, Any]]) -> Optional[RK.GridPoint]:
    if doc is None:
        return None
    return RK.GridPoint(float(doc["level"]), None if doc["ratio"] is None else float(doc["ratio"]))


def _point_name(name: str, pt: Any) -> str:
    return "%s@level=%r,ratio=%r" % (name, pt.level, pt.ratio)


def _without(doc: Mapping[str, Any], key: str) -> Any:
    """A record as its saved JSON values (NaN as null, report.metrics' rule), without one key."""
    return json.loads(dumps(M._json_safe({k: v for k, v in doc.items() if k != key})))


class HistoryOverride(object):
    """A FeatureSource (FitContext's contract) over the pool whose last history columns come from
    another block: the inner decision's features, with the own-history block built at the guard cut."""

    def __init__(self, pool: Any, history_pool: Any) -> None:
        k = len(history_pool.tree_columns)
        if tuple(pool.tree_columns[-k:]) != tuple(history_pool.tree_columns):
            raise PassRefusal("R17", "the inner history block's columns %s are not the pool's last %d tree columns"
                              % (list(history_pool.tree_columns), k))
        self._pool = pool
        self._hist = history_pool
        self._k = k
        self.tree_columns = tuple(pool.tree_columns)
        self.context_columns = tuple(pool.context_columns)

    def tree_features(self, grid_rows: Any) -> np.ndarray:
        X = np.array(self._pool.tree_features(grid_rows), dtype=np.float32, copy=True)
        X[:, -self._k:] = self._hist.tree_features(grid_rows)
        return X

    def context(self, grid_rows: Any) -> np.ndarray:
        return self._pool.context(grid_rows)


class RunState(object):
    """The in-memory state of one run (see the module docstring)."""

    def __init__(self, pipe: Any) -> None:
        self.p = pipe
        self.log = pipe.log
        self._stack = ExitStack()
        self.t0 = time.time()
        self.timings: Dict[str, float] = {}
        self._log_marks: Dict[str, int] = {}
        # owner ruling G1: each context's log twins of the rows a trimmed hand-out kept, with the context's log
        # length when each was made (weak keys: a lead's context and its pool are released with the lead)
        self._g1_log: "weakref.WeakKeyDictionary[Any, List[Any]]" = weakref.WeakKeyDictionary()
        self.ctx_inner = None
        self.ctx_inner_history = None
        self.extra_contexts: List[Any] = []            # (name, FitContext) of the forecast ladder's leads
        self.hit_tol = None
        # the nowcast banks' own exit stacks (nested in the run's), so each bank's store can be released
        # before the run ends (release_bank); a released bank's name is kept with its record
        self._bank_stacks: Dict[str, ExitStack] = {}
        self.banks_released: Dict[str, Any] = {}
        # plan R20's per-group batching (module docstring); False only for the gates' whole-frame path
        self.per_group = bool(pipe.per_group)          # a pipe without the attribute raises (never a default)
        self.schedule_record: Dict[str, Any] = {"passes": []}

    def __enter__(self) -> "RunState":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self._stack.close()
        finally:
            for name in ("pool", "pool_inner_history", "inner_features", "store_fit", "store_inner", "ctx_fit",
                         "ctx_guard", "ctx_inner_history", "ctx_inner", "donor_fit", "donor_inner"):
                self.__dict__.pop(name, None)
            self.extra_contexts = []
            gc.collect()
        return False

    def _beat(self, phase: str, message: str, done: Optional[int] = None, total: Optional[int] = None) -> None:
        self.p.status.beat(phase, message, done=done, total=total)
        self.log("%s: %s" % (phase, message))

    def _time(self, name: str, t0: float) -> None:
        self.timings[name] = round(time.time() - t0, 2)

    # ------------------------------------------------------------------ the fitctx log, part by part
    def _contexts(self) -> List[Any]:
        out = []
        for name in ("ctx_fit", "ctx_guard", "ctx_inner_history", "ctx_inner"):
            ctx = self.__dict__.get(name)
            if ctx is not None and all(ctx is not other for _, other in out):
                out.append((name, ctx))
        for name, ctx in self.extra_contexts:
            if all(ctx is not other for _, other in out):
                out.append((name, ctx))
        return out

    def log_g1_kept(self, ctx: Any, twins: Sequence[Any]) -> None:
        """Owner ruling G1: keep a context's log twins (stages.g1_kept_log_row: (the context's log length when
        made, the FitCtxLogRow)) for write_log_part, which writes each right after its hand-out's own row."""
        if twins:
            self._g1_log.setdefault(ctx, []).extend((int(at), row) for at, row in twins)

    def save_context_missing_rows(self, what: str, frame: pd.DataFrame) -> str:
        """Owner ruling G1: the fit rows one pass left out (stages.ContextMissingRows.frame), saved once as
        context_missing/<pass>.parquet (a resumed pass must save the same rows). Returns the path in the run
        folder."""
        slug = re.sub(r"[^a-z0-9]+", "_", str(what).lower()).strip("_")
        if not slug:
            raise PassRefusal("G1", "internal: the pass %r has no name to save its left-out rows under" % (what,))
        rel = "%s/%s.parquet" % (CONTEXT_MISSING_DIR, slug)
        _write_parquet_once(frame.reset_index(drop=True), self.p.folder / CONTEXT_MISSING_DIR / (slug + ".parquet"))
        return rel

    def write_log_part(self, part: str) -> None:
        """The hand-outs made since the last part, as phases/<part>/fitctx_log.parquet (deterministic, so a
        redone part must equal the one on disk). Owner ruling G1's twins follow their hand-out's own row."""
        rows = []
        for name, ctx in self._contexts():
            log = ctx.log()
            start = self._log_marks.get(name, 0)
            twins = self._g1_log.get(ctx, [])
            g1_mark = name + G1_LOG_MARK
            t_start = self._log_marks.get(g1_mark, 0)
            # a hand-out at log index i sorts at (i + 1, 0); a twin made when the log held n rows at (n, 1), so
            # right after the hand-out it trims (and before any later hand-out)
            keyed = [((i + 1, 0, i), r) for i, r in enumerate(log) if i >= start]
            keyed += [((at, 1, k), r) for k, (at, r) in enumerate(twins) if k >= t_start]
            keyed.sort(key=lambda kr: kr[0])
            rows.extend(dict(r, context=name, part=part) for r in log_records(tuple(r for _, r in keyed)))
            self._log_marks[name] = len(log)
            self._log_marks[g1_mark] = len(twins)
        cols = ["object_kind", "purpose", "lead", "cut_kind", "cut", "max_label_time", "n_rows", "groups_hash",
                "row_key_hash", "fold", "fold_purpose", "context", "part"]
        frame = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame({c: [] for c in cols})
        _write_parquet_once(frame, self.p.folder / "phases" / part / FITCTX_LOG)

    def write_fitctx_log(self, ladder_parts: Sequence[str] = ()) -> None:
        """fitctx_log.parquet: every part on disk, in LOG_PARTS order, then the forecast ladder's parts in
        lead order (kept when a resumed run finds it written)."""
        path = self.p.folder / FITCTX_LOG
        if path.exists():
            return
        names = list(LOG_PARTS) + list(ladder_parts)
        parts = [pd.read_parquet(self.p.folder / "phases" / part / FITCTX_LOG) for part in names
                 if (self.p.folder / "phases" / part / FITCTX_LOG).is_file()]
        _write_parquet_once(pd.concat(parts, ignore_index=True), path)

    # ------------------------------------------------------------------ step 3-5: vault and pool
    def _history(self, ctx: Any, spec17: Any, rows: np.ndarray, n: int) -> Any:
        fill, donor_mean = ST.history_inputs(ctx, self.vg, self.p.split_sets, self.bank_units)
        hist, filled = ST.history_block(self.vg.grid, spec17, self.vg.steps, rows // n, 0, self.labels, fill,
                                        season_keys_of(self.vg.steps, self.season), donor_mean)
        return hist, dict(filled), donor_mean

    def build_pool(self, need_inner: bool = True) -> None:
        p = self.p
        t0 = time.time()
        self.derived = p.derived
        self.kind = PR.router_kind(self.derived)      # R12; the neighbour kind (M8) stops here, before any fit
        self.vg = p._vault(p.folder)
        self.labels = self.vg.labels
        self.lists = self.derived["R18:units"].value
        self.groups = tuple(sorted(self.lists.bank))
        order = {u: i for i, u in enumerate(self.vg.grid.unit_ids)}
        self.bank_units = sorted((u for g in self.groups for u in self.lists.bank[g]), key=order.get)
        self.scored_units = sorted((u for g in self.groups for u in self.lists.scored[g]), key=order.get)
        self.unit_group = {u: g for g in self.groups for u in self.lists.bank[g]}
        self.season = self.derived["R2"].value
        self.cuts = self.derived["R11"].value[0]
        self.windows = self.derived["R7"].value
        self.links = tuple(self.derived["R22"].value)
        self.legal = p.spec.legal_range
        self.ub = self.legal[1] if np.isfinite(self.legal[1]) else None
        spec17 = self.derived["R17"].value
        tree_cols = tuple(p.spec.tree_features) + tuple(spec17.columns)
        ctx_cols = tuple(p.spec.context)
        n = int(self.vg.grid.n_steps)
        rows = np.arange(len(self.vg.grid.unit_ids) * n, dtype=np.int64)
        self._beat("pool", "%d grid rows (%d units x %d steps), %d tree columns (%d history), %d context"
                   % (rows.size, len(self.vg.grid.unit_ids), n, len(tree_cols), len(spec17.columns), len(ctx_cols)))
        self.pool = self._stack.enter_context(open_pool(p.temp_dir, "pool", rows, tree_cols, ctx_cols))
        self.ctx_fit = FitContext(self.derived, p.split_sets, self.vg.grid, self.labels, self.pool, self.lists, 0,
                                  CutKind.FIT)
        if spec17.columns:
            hist, self.history_filled, self.history_donor_mean = self._history(self.ctx_fit, spec17, rows, n)
        else:
            hist, self.history_filled, self.history_donor_mean = np.zeros((rows.size, 0), dtype=np.float32), {}, None
        if self.per_group:
            self.fill_pool_by_group(self.pool, hist, None)
        else:
            lagged = p.reader.lagged(self.derived["R8"].value)
            base = p.reader.base_rows(self.vg.unit_ids, self.vg.steps)
            tree_values = lagged[list(p.spec.tree_features)].to_numpy(dtype=np.float32) if p.spec.tree_features \
                else np.zeros((len(lagged), 0), dtype=np.float32)
            ctx_values = lagged[list(ctx_cols)].to_numpy(dtype=np.float32) if ctx_cols else None
            ST.fill_pool(self.pool, self.vg, lambda r: tree_values[base[r]],
                         (lambda r: ctx_values[base[r]]) if ctx_values is not None else (lambda r: None), hist,
                         self.log)
            del tree_values, ctx_values
        del hist
        self.inner_features = self.pool
        self.history_inner = None
        if need_inner and K.INNER_CUT_BANK_REFIT and spec17.columns:
            # L6 b: the inner decision stands at the guard cut, so do its history block's fallbacks
            ctx_g = self.ctx_fit.for_lead(0, CutKind.GUARD)
            self.ctx_inner_history = ctx_g
            hist_g, filled_g, mean_g = self._history(ctx_g, spec17, rows, n)
            self.pool_inner_history = self._stack.enter_context(
                open_pool(p.temp_dir, "pool_inner_history", rows, tuple(spec17.columns), ()))
            for a0 in range(0, rows.size, 50000):
                self.pool_inner_history.write(rows[a0:a0 + 50000], hist_g[a0:a0 + 50000], None)
            self.pool_inner_history.require_complete()
            del hist_g
            self.inner_features = HistoryOverride(self.pool, self.pool_inner_history)
            self.history_inner = {"cut": int(ctx_g.cut), "filled_share": filled_g, "donor_mean": mean_g}
            self.log("inner history block at the guard cut %d: donor-row mean %.6g (fit cut %.6g)"
                     % (ctx_g.cut, mean_g, self.history_donor_mean))
        self._time("pool", t0)

    def fill_pool_by_group(self, pool: Any, hist: np.ndarray, lead: Optional[int], move: Any = None,
                           adjust: Any = None) -> Optional[np.ndarray]:
        """Plan R20's per-group batching of a pool fill: for each group, the picked units' column reader of that
        group alone (pipeline/stream.py GroupReaders: one group's reader in RAM at a time), its lagged frame (R8,
        the last-value rule) and the group's grid rows written once (each unit's every step, ascending), with
        the history block's rows. lead None: the nowcast pool (the lagged values at each grid row, as
        stages.fill_pool writes them from the whole reader). lead L: the forecast ladder's lead pool (the kept
        tree features and router context moved to the issue step t - L by io.apply.features_at_issue_step on
        the group's base rows, pre-Y0 lag year included, as Ladder._moved does on the whole reader); returns the
        per-grid-row flag 'the issue row is absent' (None for lead None). Byte for byte the whole path's pool:
        every value is a function of its unit's own rows (the separability guard checked the feature script).
        move: the function that moves features to the issue step (the ladder passes its own reference of
        io.apply.features_at_issue_step); adjust(rows, tree, context, absent) -> (tree, context, absent): the
        ladder's per-group seam on a group's moved rows before they are written (identity unless a test plants
        a fault there, as the whole path's Ladder._moved)."""
        from treeroute.io.apply import features_at_issue_step
        from treeroute.io.steps import predecessor_index

        move = features_at_issue_step if move is None else move

        p = self.p
        readers = p.reader
        lags = self.derived["R8"].value
        tcols, ccols = list(p.spec.tree_features), list(p.spec.context)
        n = int(self.vg.grid.n_steps)
        gou = np.asarray(self.vg.grid.group_of_unit, dtype=object)
        absent = np.zeros(len(self.vg.grid.unit_ids) * n, dtype=bool) if lead is not None else None
        bank = np.asarray(self.bank_units, dtype=object).astype(str)
        groups = [g for g in readers.groups if (gou == g).any()]
        stray = sorted(set(gou.tolist()) - set(readers.groups))
        if stray:
            raise PassRefusal("R20", "the vault's groups %s have no picked-unit reader" % stray[:5])
        for i, g in enumerate(groups):
            idx = np.flatnonzero(gou == g)
            rows = (idx[:, None] * n + np.arange(n, dtype=np.int64)[None, :]).reshape(-1)
            reader = readers.reader(g)
            lagged = readers.lagged(g, lags)
            base = reader.base_rows(self.vg.unit_ids[rows], self.vg.steps[rows])
            if lead is None:
                tv = lagged[tcols].to_numpy(dtype=np.float32)[base] if tcols else np.zeros((rows.size, 0), np.float32)
                cv = lagged[ccols].to_numpy(dtype=np.float32)[base] if ccols else None
            else:
                units = np.asarray(reader.units, dtype=object).astype(str)
                sub = np.flatnonzero(np.isin(units, bank))
                codes, steps = reader.codes[sub], reader.steps[sub]
                X = lagged[tcols].to_numpy(dtype=np.float32)[sub] if tcols else np.zeros((sub.size, 0), np.float32)
                moved = move(X, codes, steps, int(lead))
                moved_c = move(lagged[ccols].to_numpy(dtype=np.float32)[sub], codes, steps, int(lead))                     if ccols else None
                inv = np.full(units.size, -1, dtype=np.int64)
                inv[sub] = np.arange(sub.size, dtype=np.int64)
                gpos = inv[base]
                if (gpos < 0).any():
                    raise PassRefusal("R8", "internal: %d grid rows are not base rows of a bank unit"
                                      % int((gpos < 0).sum()))
                if int(lead) > 0:
                    absent[rows] = (predecessor_index(codes, steps, int(lead)) < 0)[gpos]
                tv = moved[gpos]
                cv = moved_c[gpos] if moved_c is not None else None
                del moved, moved_c, X
                if adjust is not None:
                    tv, cv, absent[rows] = adjust(rows, tv, cv, absent[rows].copy())
            del lagged
            for a0 in range(0, rows.size, POOL_FILL_ROWS):
                r = rows[a0:a0 + POOL_FILL_ROWS]
                tree = np.hstack([tv[a0:a0 + POOL_FILL_ROWS], hist[r]]) if hist.shape[1] else tv[a0:a0 + POOL_FILL_ROWS]
                pool.write(r, tree.astype(np.float32), cv[a0:a0 + POOL_FILL_ROWS] if cv is not None else None)
            del tv, cv
            self.p.status.beat("pool" if lead is None else "ladder", "pool filled for group %d of %d" % (i + 1, len(groups)),
                               done=i + 1, total=len(groups))
        readers.release()
        pool.require_complete()
        self.log("pool: %d rows x %d tree columns, %d context columns (filled group by group: %d groups)"
                 % (pool.n_rows, len(pool.tree_columns), len(pool.context_columns), len(groups)))
        return absent

    def donor(self, ctx: Any, purpose: str, unit_ids: Optional[Sequence[str]] = None) -> Any:
        """A donor-row hand-out: per group (plan R20) FitContext.donor_rows_lazy (the features read one group's rows at
        a time by fit.bank; the same rows and log row), the whole path FitContext.donor_rows."""
        uid = tuple(unit_ids) if unit_ids is not None else None
        return ctx.donor_rows_lazy(purpose, uid) if self.per_group else ctx.donor_rows(purpose, uid)

    def answers_once(self, store: Any) -> Any:
        """The store the GLS weight model reads: per group (plan R20) a fit.tables.DropAfterRead view (each group's
        donor-row table dropped once read), the whole path the store itself."""
        return DropAfterRead(store) if self.per_group else store

    def _pass_tables(self, store: Any, features: Any, kinds: Sequence[str], last: Optional[int], phase: str) -> Any:
        """The tables one pass reads. Per-group batching: a router.GroupTables (each group's scored-unit rows built
        right before the group is routed, every table of the group dropped right after it). The whole path: every
        group's tables built now (_build_tables), None."""
        if not self.per_group:
            self._build_tables(store, features, kinds, last, phase)
            return None
        groups = tuple(self.groups)
        feats = ST.zero_filled(features)
        rec = {"phase": phase, "kinds": list(kinds), "last": last, "groups": len(groups), "peak_table_bytes": 0,
               "peak_group": None}
        self.schedule_record["passes"].append(rec)

        def build(g: str) -> None:
            ids = ST.unit_positions(self.vg, self.lists.scored[g], None, last)
            for kind in kinds:
                store.build(g, kind, ids, feats)

        def drop(g: str) -> None:
            held = store.held_bytes()
            if held > rec["peak_table_bytes"]:
                rec["peak_table_bytes"], rec["peak_group"] = int(held), g
            store.drop_group(g)
            i = groups.index(g)
            self.p.status.beat(phase, "tables %s: group %d of %d routed and dropped" % ("/".join(kinds), i + 1,
                                                                                         len(groups)),
                               done=i + 1, total=len(groups))
        return PR.GroupTables(groups=groups, build=build, drop=drop)

    # ------------------------------------------------------------------ step 6: fits
    def fit(self, need_inner: bool = True) -> None:
        p = self.p
        t0 = time.time()
        # the GLS weight model reads the fit-cut features (its answers come from the fit-cut bank, L6)
        self.ctx_guard = self.ctx_fit.for_lead(0, CutKind.GUARD)
        self._beat("fits", "bank at the fit cut %d: %d groups x %d trees" % (self.cuts.fit_cut, len(self.groups),
                                                                            p.trees_per_group))
        # per group (plan R20): the donor rows' features are read one group at a time by the bank fit (lazy X)
        self.donor_fit = self.donor(self.ctx_fit, "bank")
        self.bank_fit = fit_donor_bank(self.donor_fit, p.trees_per_group)
        self._check_bank(self.bank_fit, "fit-cut")
        row_group = ST.row_group_of(self.vg)
        self.store_fit = self._bank_stack(BANK_FIT).enter_context(
            TreeAnswerStore.from_bank(self.bank_fit, row_group, p.temp_dir, p.registry))
        self.masks_fit = ST.block_masks(self.bank_fit.tree_group, p.blocks)
        self.c = c_for_cut_against_plan(self.donor_fit, self.derived) if Link.LOG_C in self.links else None
        self.tol, self.tol_record = ST.guard_tolerances(self.donor_fit, self.links, self.c, self.ub, p.smoke)
        self.donor_mean_fit = ST.donor_link_means(self.donor_fit, self.links, self.c, self.ub)
        if self.kind == PR.KIND_REGION:
            self.weights = None
            REC.write_once_or_same(p.folder / "gls_weight_model.json", {"fitted": False, "reason": PR.REGION_GLS_ABSENT})
        else:
            self._beat("fits", "GLS weight model (R25) at the guard cut %d" % self.cuts.guard_cut)
            self.weights = weight_model_for_cut(self.ctx_fit, self.ctx_guard, self.answers_once(self.store_fit),
                                                self.bank_fit.tree_group, blocks=p.blocks)
            from treeroute.derive.derived import derived_entry

            REC.write_once_or_same(p.folder / "gls_weight_model.json",
                                   derived_entry(weight_model_record(self.weights)))
        if need_inner:
            if K.INNER_CUT_BANK_REFIT:
                self._beat("fits", "bank refit at the inner cut %d (L6 b)" % self.cuts.guard_cut)
                self.ctx_inner = FitContext(self.derived, p.split_sets, self.vg.grid, self.labels,
                                            self.inner_features, self.lists, 0, CutKind.GUARD)
                self.donor_inner = self.donor(self.ctx_inner, "bank_inner")
                self.bank_inner = fit_donor_bank(self.donor_inner, p.trees_per_group)
                self._check_bank(self.bank_inner, "inner-cut")
                self.store_inner = self._bank_stack(BANK_INNER).enter_context(
                    TreeAnswerStore.from_bank(self.bank_inner, row_group, p.temp_dir, p.registry))
                self.masks_inner = ST.block_masks(self.bank_inner.tree_group, p.blocks)
            else:
                self.ctx_inner = self.ctx_guard
                self.donor_inner = self.donor(self.ctx_guard, "normal_fallback")
                self.bank_inner, self.store_inner, self.masks_inner = self.bank_fit, self.store_fit, self.masks_fit
            self.donor_mean_inner = ST.donor_link_means(self.donor_inner, self.links, self.c, self.ub)
        self.write_log_part("setup_with_inner" if need_inner else "setup")
        self._time("fits", t0)

    def _bank_stack(self, which: str) -> ExitStack:
        """A new exit stack for one nowcast bank's store, nested in the run's (so the run's exit still closes
        it), which release_bank closes early."""
        if which in self._bank_stacks or which in self.banks_released:
            raise PassRefusal("R20", "internal: the nowcast's %s bank is opened twice in one process" % which)
        st = self._stack.enter_context(ExitStack())
        self._bank_stacks[which] = st
        return st

    def banks_held(self) -> List[str]:
        """The nowcast banks still in memory in this process (BANK_FIT, BANK_INNER), in that order."""
        return [w for w in (BANK_FIT, BANK_INNER) if getattr(self, BANK_ATTRS[w][0], None) is not None]

    def release_bank(self, which: str, why: str) -> Optional[Dict[str, Any]]:
        """Release one nowcast bank (BANK_FIT or BANK_INNER) once nothing reads it any more: its store's temp
        files are deleted loudly (TreeAnswerStore.close), its exit stack is emptied (so no reference to its
        trees survives in the run's stack), and the bank, store and block masks leave this state; gc. A bank
        this process never fitted (a resumed run) is a no-op (None). With A7.inner_cut_bank_refit off the
        inner names alias the fit-cut bank: releasing BANK_INNER then drops only the alias."""
        if which not in BANK_ATTRS:
            raise PassRefusal("R20", "internal: no nowcast bank named %r (%s)" % (which, sorted(BANK_ATTRS)))
        bank_attr, store_attr, masks_attr = BANK_ATTRS[which]
        bank = self.__dict__.get(bank_attr)
        if bank is None:
            self._bank_stacks.pop(which, None)
            return None
        alias = which == BANK_INNER and bank is self.__dict__.get(BANK_ATTRS[BANK_FIT][0])
        rec = {"bank": which, "trees": len(bank.trees), "fingerprint": bank.manifest.bank_fingerprint,
               "why": why, "alias_of_fit_cut_bank": bool(alias)}
        del bank
        stack = self._bank_stacks.pop(which, None)
        for name in (bank_attr, store_attr, masks_attr):
            self.__dict__.pop(name, None)
        if stack is not None and not alias:
            stack.close()                 # TreeAnswerStore.close: every temp file deleted, loudly
        gc.collect()
        self.banks_released[which] = rec
        self.log("released the nowcast's %s bank (%d trees, fingerprint %s)%s: %s"
                 % (which, rec["trees"], rec["fingerprint"][:16],
                    " (an alias of the fit-cut bank: only the names dropped)" if alias else " and its tables", why))
        return rec

    def _check_bank(self, bank: Any, what: str) -> None:
        owners = sorted(set(bank.tree_group))
        if owners != list(self.groups):
            raise PassRefusal("R19", "the %s bank's tree groups %s are not the run's groups %s (every group trains "
                              "its own trees under LORO)" % (what, owners[:5], list(self.groups)[:5]))
        self.log("%s bank: %d trees, fingerprint %s, rows at or before %d (max label step %d)"
                 % (what, len(bank.trees), bank.manifest.bank_fingerprint[:16], bank.manifest.cut,
                    bank.manifest.max_label_time))

    def _build_tables(self, store: Any, features: Any, kinds: Sequence[str], last: Optional[int], phase: str) -> None:
        for i, g in enumerate(self.groups):
            ids = ST.unit_positions(self.vg, self.lists.scored[g], None, last)
            for kind in kinds:
                store.build(g, kind, ids, ST.zero_filled(features))
            self.p.status.beat(phase, "tables %s: group %d of %d" % ("/".join(kinds), i + 1, len(self.groups)),
                               done=i + 1, total=len(self.groups))

    # ------------------------------------------------------------------ step 8: the decision surface
    def decision(self) -> None:
        p = self.p
        t0 = time.time()
        ctx = self.ctx_inner
        fit_cut, guard_cut = int(self.cuts.fit_cut), int(self.cuts.guard_cut)
        n = int(self.vg.grid.n_steps)
        row_of = {u: i for i, u in enumerate(self.vg.grid.unit_ids)}
        vu, vt, vv = self.labels.validity(guard_cut + 1, fit_cut)
        pos = np.fromiter((row_of[u] for u in vu.tolist()), dtype=np.int64, count=vu.size) * n + (vt - self.vg.first_step)
        scored = np.isin(vu, np.asarray(self.scored_units, dtype=object))
        last_day = int(step_bounds(np.array([fit_cut], dtype=np.int64), p.cadence)[1][0])
        ended = self.vg.window_end[pos] <= last_day
        pick = scored & vv & ended
        self.log("decision surface (D67): %d inner-score rows of the scored units in steps %d..%d; %d with a valid "
                 "label; %d whose own label window ended by the fit cut: %d rows scored"
                 % (int(scored.sum()), guard_cut + 1, fit_cut, int((scored & vv).sum()),
                    int((scored & vv & ended).sum()), int(pick.sum())))
        surface = self.labels.decision_surface(vu[pick], vt[pick], fit_cut)
        s_keys = pos[pick]
        self._beat(PHASE, "tree-answer tables of the inner-cut bank over the scored units' rows up to %d%s"
                   % (fit_cut, " (one group at a time)" if self.per_group else ""))
        sched = self._pass_tables(self.store_inner, self.inner_features, ("plain", "corrector"), fit_cut, PHASE)
        tree_arms = self.decision_arms()
        inp = PR.PassInput("decision surface", ctx, self.store_inner, self.masks_inner, self.inner_features,
                           np.asarray(surface.unit_ids, dtype=object), np.asarray(surface.times, dtype=np.int64),
                           s_keys, self.tol, self.donor_mean_inner, "router_inner", self.c, schedule=sched)
        router = PR.PassRouter(self, inp, self.kind, weights=self.weights_fn(self.weights, self.pool))
        self._beat(PHASE, "%s router: %d tree arms on the decision surface (%s)"
                   % (self.kind, len(tree_arms), ", ".join(LA.arm_name(a) for a in tree_arms)))
        routed = router.route(tree_arms, None, y_surface=np.asarray(surface.y, dtype=np.float64), plumbing=True)
        arms: List[Any] = [LD.SurfaceArm(a, ST.inverse(routed.predictions[LA.arm_name(a)], a.link, self.c, self.ub))
                           for a in tree_arms]
        arms += [LD.SurfaceArm(LA.trees_off_of(L), ST.inverse(routed.trees_off[L], L, self.c, self.ub))
                 for L in self.links]
        self.plumbing = dict(routed.plumbing)
        record = LD.decide(surface, arms, routed.grid, self.legal, ctx, gls_absent_reason=self.gls_absent_reason())
        for line in LD.decision_lines(record):         # decide() printed them; the run log keeps them too
            self.log.file_only(line)
        self._save_inner(record, arms, surface)
        # every decision record is written BEFORE the lock, so a process that stops after the lock leaves a
        # folder a resumed run can finish from (the lock and its records, never a re-decision)
        REC.write_once_or_same(p.folder / DECISION_CHECKS, {
            "g_plumb": self.plumbing, "tolerances": self.tol_record, "c": self.c, "router_kind": self.kind,
            "gls_absent_reason": self.gls_absent_reason(), "gls": self.gls_record(),
            "fallback": routed.records.get("fallback"), "fallback_gls_note": routed.records.get("fallback_gls_note"),
            "fallback_levels": router.levels_found, "region": routed.records.get("region"),
            "context_missing": routed.records.get("context_missing"),        # owner ruling G1
            "surface_rows": int(record.n_rows),
            "surface_sha256": record.surface_sha256, "candidates": len(record.candidates),
            "surface_clip": {name: {"n_rows": cc.n_rows, "n_finite": cc.n_finite, "n_below": cc.n_below,
                                    "n_above": cc.n_above, "n_nan": cc.n_nan}
                             for name, cc in sorted(record.clip.items())},
            "inner_history": self.history_inner,
            "inner_features": ("own-history block at the guard cut" if self.history_inner is not None
                               else "the fit-cut pool (no history block, or no inner-cut refit)")})
        self.write_log_part("decision")                # the decision's hand-outs, before the lock
        self.adoption = record.adoption
        self.adoption_sha = lock_adoption(record.adoption, self.labels, p.folder)
        self._manifest_adoption()
        self._time(PHASE, t0)

    # ------------------------------------------------------------------ arms, weights (R24, R25)
    def weightings(self) -> tuple:
        """The weightings routed: unweighted and GLS for the per-unit kind; unweighted only for the region
        kind, which has no weighted solve (router.REGION_GLS_ABSENT)."""
        if self.kind == PR.KIND_REGION:
            return (LA.Weighting.UNWEIGHTED,)
        return (LA.Weighting.UNWEIGHTED, LA.Weighting.GLS)

    def gls_absent_reason(self) -> Optional[str]:
        return PR.REGION_GLS_ABSENT if self.kind == PR.KIND_REGION else None

    def gls_record(self) -> Dict[str, Any]:
        if self.kind == PR.KIND_REGION:
            return {"routed": False, "reason": PR.REGION_GLS_ABSENT}
        return {"routed": True, "kernel": "route.solve solve_grid_weighted / solve_point_weighted (NEW formula, "
                                          "owner review): the weighted primal is solve_local with the weights; the "
                                          "weighted shared-Gram solve is grid_dual on rows scaled by sqrt(w)",
                "weights": "fit.weights.weights_for_rows on the router's fit rows (R25; out-of-bag sigma on the "
                           "weight model's own donor rows, L5 c); trees-off unweighted"}

    def decision_arms(self) -> List[Any]:
        """R24's selectable arms of candidate_arms(R22 links), in candidate order, for the routed weightings."""
        keep = self.weightings()
        return [a for a in LA.candidate_arms(self.links) if a.selectable and a.weighting in keep]

    def weights_fn(self, model: Any, features: Any) -> Any:
        """Router fit rows -> their R25 weights (fit.weights.weights_for_rows on the features the weight
        model was fitted on), or None without a model."""
        if model is None:
            return None
        zf = ST.zero_filled(features)
        return lambda keys: weights_for_rows(model, np.asarray(keys, dtype=np.int64), zf(keys))

    def _save_inner(self, record: Any, arms: Sequence[Any], surface: Any) -> None:
        """inner_preds.parquet: every surface row's keys and label (the vault's as-of view at the fit cut),
        every candidate clipped (as decide scored it) and before the clip."""
        units = np.asarray(record.unit_ids, dtype=object)
        if not (np.array_equal(units, np.asarray(surface.unit_ids, dtype=object))
                and np.array_equal(np.asarray(record.times), np.asarray(surface.times))):
            raise PassRefusal("G-LOCK", "internal: the decision record's rows are not the surface's rows")
        frame = pd.DataFrame({"unit": units, "group": [self.unit_group[u] for u in units.tolist()],
                              "time": np.asarray(record.times, dtype=np.int64),
                              "y": np.asarray(surface.y, dtype=np.float64)})
        cols = {}
        for name, values in record.predictions.items():
            v = np.asarray(values)
            if v.ndim == 1:
                cols[name] = v
            else:
                for j, pt in enumerate(record.grid):
                    cols[_point_name(name, pt)] = v[:, j]
        for sa in arms:
            name = M.PRE_PREFIX + LA.arm_name(sa.arm)
            v = np.asarray(sa.pre_clip, dtype=np.float64)
            if v.ndim == 1:
                cols[name] = v
            else:
                for j, pt in enumerate(record.grid):
                    cols[_point_name(name, pt)] = v[:, j]
        frame = pd.concat([frame, pd.DataFrame(cols)], axis=1)
        _write_parquet_once(frame, self.p.folder / REC.INNER_PREDS)
        REC.write_text_once_or_same(self.p.folder / REC.INNER_CANDIDATES, REC.csv_text(pd.DataFrame(list(record.table()))))

    def _manifest_adoption(self) -> None:
        """The adoption hash in the manifest's write-once addendum (the vault contract: the caller puts the
        hash in the manifest before any test label opens). Checked against the lock record."""
        folder = self.p.folder
        lock = read_json(folder / (ADOPTION_FILE + LOCK_SUFFIX))
        if lock["sha256"] != self.adoption_sha:
            raise PassRefusal("G-LOCK", "the lock record names SHA-256 %s, the adoption %s"
                              % (lock["sha256"], self.adoption_sha))
        REC.write_once_or_same(folder / MANIFEST_ADOPTION, {
            "fingerprint": self.p.fingerprint, "manifest": "manifest.json", "adoption_file": ADOPTION_FILE,
            "adoption_sha256": self.adoption_sha, "lock_file": ADOPTION_FILE + LOCK_SUFFIX,
            "rule": "G-LOCK: the adoption hash is recorded with the manifest before any test label opens"})

    def read_adoption(self) -> None:
        """A resumed run: the locked adoption.json read back (never re-decided)."""
        folder = self.p.folder
        lock = read_json(folder / (ADOPTION_FILE + LOCK_SUFFIX))
        doc = read_json(folder / ADOPTION_FILE)
        self.adoption_sha = lock["sha256"]
        self.adoption = LD.Adoption(
            adopted=_arm_doc_spec(doc.get("adopted")), penalty=_point_doc(doc.get("penalty")),
            declined=bool(doc["declined"]), best_tree_arm=_arm_doc_spec(doc["best_tree_arm"]),
            best_tree_penalty=_point_doc(doc["best_tree_penalty"]),
            eligible=tuple(_arm_doc_spec(a) for a in doc.get("eligible", [])),
            surface_mae=dict(doc.get("surface_mae", {})), beside={k: (float("nan") if v is None else v)
                                                                  for k, v in doc.get("beside", {}).items()})

    # ------------------------------------------------------------------ step 9: the test pass
    def test_pass(self) -> None:
        p = self.p
        t0 = time.time()
        a = self.adoption
        point = a.best_tree_penalty if a.declined else a.penalty
        point = RK.GridPoint(float(point.level), None if point.ratio is None else float(point.ratio))
        self._manifest_adoption()                          # before any test label opens (G-LOCK)
        tl = self.labels.open_test_labels(self.adoption_sha, 0)
        t_keys = ST.unit_positions(self.vg, self.scored_units, self.vg.test_first, None)
        t_units = self.vg.unit_ids[t_keys]
        t_steps = self.vg.steps[t_keys]
        y_of = pd.Series(np.asarray(tl.y, dtype=np.float64),
                         index=pd.MultiIndex.from_arrays([np.asarray(tl.unit_ids, dtype=object),
                                                          np.asarray(tl.times, dtype=np.int64)]))
        y = y_of.reindex(pd.MultiIndex.from_arrays([t_units, t_steps])).to_numpy(dtype=np.float64)
        self.log("test pass: %d rows of %d scored units (%d with a label); tree arms at level %r ratio %r (%s)"
                 % (t_keys.size, len(self.scored_units), int(np.isfinite(y).sum()), point.level, point.ratio,
                    "the best tree arm's penalty: the layer declined" if a.declined else "the adopted penalty"))
        self._beat(PHASE_T, "tree-answer tables of the fit-cut bank (plain, corrector, placebo)%s"
                   % (" (one group at a time)" if self.per_group else ""))
        sched = self._pass_tables(self.store_fit, self.pool, ("plain", "corrector", "placebo_corrector"), None, PHASE_T)
        test_arms = [LA.ArmSpec(L, tool, w, True) for L in self.links for tool in TREE_TOOLS for w in self.weightings()]
        test_arms += [LA.ArmSpec(L, PLACEBO, w, False) for L in self.links for w in self.weightings()]
        inp = PR.PassInput("test pass", self.ctx_fit, self.store_fit, self.masks_fit, self.pool, t_units, t_steps,
                           t_keys, self.tol, self.donor_mean_fit, "router_test", self.c, schedule=sched)
        router = PR.PassRouter(self, inp, self.kind, weights=self.weights_fn(self.weights, self.pool),
                               fallback_levels=self.decided_levels())
        self._beat(PHASE_T, "%s router at the pinned penalty: %d arms and placebos" % (self.kind, len(test_arms)))
        routed = router.route(test_arms, point)
        arms, placebos, pre = {}, {}, {}
        for spec in test_arms:
            name = LA.arm_name(spec)
            p_pre = ST.inverse(routed.predictions[name][:, 0], spec.link, self.c, self.ub)
            (placebos if spec.tool is PLACEBO else arms)[name] = clip_to_legal(p_pre, self.legal, False)[0]
            pre[name] = p_pre
        for L in self.links:
            off = LA.arm_name(LA.trees_off_of(L))
            off_pre = ST.inverse(routed.trees_off[L], L, self.c, self.ub)
            arms[off] = clip_to_legal(off_pre, self.legal, False)[0]
            pre[off] = off_pre
        normal_identity = np.asarray(routed.score_normal[Link.IDENTITY], dtype=np.float64)
        self.test_records = routed.records
        baselines = {"predict_zero": M.baseline_predict_zero(t_keys.size, self.legal),
                     "guess_normal": M.baseline_guess_normal(normal_identity, self.legal),
                     "last5_normal": self._last5(t_units, t_steps)}
        years = _years_of_steps(t_steps, p.cadence)
        frame = M.assemble_rows({"unit": t_units, "group": np.asarray([self.unit_group[u] for u in t_units.tolist()],
                                                                     dtype=object),
                                 "time": t_steps, "year": years},
                                0, t_steps, y, normal_identity, arms, placebos, pre, baselines, self.legal)
        path = p.folder / REC.TEST_PREDS
        if path.exists():
            if not M.read_rows(path).equals(frame):
                raise PassRefusal("G-FINGERPRINT", "%s exists with other rows" % path, fix="start a new run")
        else:
            M.write_rows_once(frame, path)
        self.n_test_rows = int(len(frame))
        doc = {"fit_cut_store": self.store_fit.record(),
               "inner_cut_store": (self.store_inner.record() if getattr(self, "store_inner", None) is not None
                                   else None)}
        if self.per_group:
            doc["schedule"] = {"rule": TABLE_SCHEDULE_RULE, "passes": list(self.schedule_record["passes"])}
        REC.write_once_or_same(p.folder / "tables.json", doc)
        REC.write_once_or_same(p.folder / "test_pass_router.json", {"router_kind": self.kind,
                                                                    "records": M._json_safe(routed.records)})
        self.write_log_part("test_pass")
        self._time(PHASE_T, t0)

    def decided_levels(self) -> Dict[str, Any]:
        """The fallback levels (R12) the decision surface found, from decision_checks.json (written before
        the adoption lock)."""
        return dict(read_json(self.p.folder / DECISION_CHECKS).get("fallback_levels") or {})

    def _last5(self, units: np.ndarray, steps: np.ndarray, ctx: Any = None, cut_year: Optional[int] = None) -> np.ndarray:
        ctx = self.ctx_fit if ctx is None else ctx
        cut_year = int(self.windows.train_end) if cut_year is None else int(cut_year)
        out = np.full(units.size, np.nan)
        keys = season_keys_of(steps, self.season)
        for u in np.unique(units.astype(str)):
            sel = units == u
            h = ctx.unit_history(u, "last5_normal")
            out[sel] = M.baseline_last5_normal(h, self.kind, keys[sel], cut_year, self.legal)
        return out

    # ------------------------------------------------------------------ step 12: metrics
    def hit_tolerance(self) -> Any:
        """R33's hit tolerance from the fit-cut donor rows against their identity normal (D9), and the
        package's declared measurement-error floor (or None). Cached for the ladder."""
        if self.hit_tol is None:
            normals = ST.unit_normals(self.ctx_fit, self.bank_units, Link.IDENTITY, None, None,
                                      self.donor_mean_fit[Link.IDENTITY], self.season)
            d = self.donor_fit
            ref = np.empty(d.y.size, dtype=np.float64)
            keys = season_keys_of(np.asarray(d.times, dtype=np.int64), self.season)
            du = np.asarray(d.unit_ids, dtype=object)
            for u in np.unique(du.astype(str)):
                sel = du == u
                ref[sel] = RK.normal_values(normals[u], keys[sel])
            floor = self.p.spec.measurement_error_floor
            self.hit_tol = (M.hit_tolerance(d, ref), float(floor) if floor else None)
        return self.hit_tol

    def _strata(self, preds: pd.DataFrame, tol: float, floor: Optional[float], kind: str) -> Dict[str, Any]:
        """R34 per declared stratum: quartile edges from the fit-cut donor rows (of the bank units with a
        stratum value), test rows binned right-closed (D73); rows of units without a value are left out and
        counted. Writes per_stratum.csv (every stratum column's table, one after the other)."""
        p = self.p
        if not p.strata:
            return {}
        tables, records = [], {}
        for col, per_unit in sorted(p.strata.items()):
            values = per_unit.reindex(pd.Index(self.bank_units, dtype=object)).to_numpy(dtype=np.float64)
            with_value = tuple(u for u, v in zip(self.bank_units, values) if np.isfinite(v))
            if not with_value:
                raise PassRefusal("R34", "report stratum %r has no value on any bank unit" % col)
            donor = self.donor(self.ctx_fit, "stratum_edges:%s" % col, with_value)
            dv = per_unit.reindex(pd.Index(np.asarray(donor.unit_ids, dtype=object), dtype=object)).to_numpy(np.float64)
            edges = M.stratum_edges(donor, dv)
            v = per_unit.reindex(pd.Index(preds["unit"].to_numpy(dtype=object), dtype=object)).to_numpy(np.float64)
            ok = np.isfinite(v)
            sub = preds[ok].reset_index(drop=True).copy()
            sub["stratum"] = M.stratum_bins(v[ok], edges)
            table = M.score_table(sub, ("stratum",), tol, floor, kind)
            table.insert(0, "stratum_column", col)
            for i, e in enumerate(edges):
                table["edge_q%d" % (25 * (i + 1))] = e
            tables.append(table)
            records[col] = {"edges": list(edges), "donor_rows": int(donor.y.size),
                            "bank_units_without_value": len(self.bank_units) - len(with_value),
                            "test_rows_without_value": int((~ok).sum()), "test_rows": int(ok.sum())}
            self.log("per-stratum table %s: edges %s from %d donor rows; %d test rows without a value left out"
                     % (col, [round(e, 6) for e in edges], donor.y.size, int((~ok).sum())))
        REC.write_text_once_or_same(p.folder / PER_STRATUM, REC.csv_text(pd.concat(tables, ignore_index=True)))
        return records

    def _preclip(self, preds: pd.DataFrame) -> None:
        """preclip.csv: per arm and placebo, the rows outside the legal range before the clip, on the
        decision surface (decide's counts) and on the test pass (the saved pre-clip values)."""
        lo, hi = self.legal
        lines = []
        checks = read_json(self.p.folder / DECISION_CHECKS)
        for name, cc in sorted(checks["surface_clip"].items()):
            rate = (cc["n_below"] + cc["n_above"]) / float(cc["n_finite"]) if cc["n_finite"] else float("nan")
            lines.append(dict({"pass": "decision_surface", "column": name}, **cc, preclip_rate=rate))
        for c in [c for c in preds.columns if c.startswith(M.PRE_PREFIX)]:
            v = preds[c].to_numpy(dtype=np.float64)
            fin = np.isfinite(v)
            below, above = int((v[fin] < lo).sum()), int((v[fin] > hi).sum())
            lines.append({"pass": "test", "column": c[len(M.PRE_PREFIX):], "n_rows": int(v.size),
                          "n_finite": int(fin.sum()), "n_below": below, "n_above": above,
                          "n_nan": int((~fin).sum()),
                          "preclip_rate": (below + above) / float(fin.sum()) if fin.any() else float("nan")})
        REC.write_text_once_or_same(self.p.folder / PRECLIP, REC.csv_text(pd.DataFrame(lines)))

    def report(self) -> Dict[str, Any]:
        p = self.p
        t0 = time.time()
        folder = p.folder
        preds = M.read_rows(folder / REC.TEST_PREDS)
        REC.check_scored_units(folder)                     # G-SPLIT on the outputs, before any score
        tol, floor = self.hit_tolerance()
        kind = p.kind
        t_group = M.score_table(preds, ("group",), tol, floor, kind)
        t_year = M.score_table(preds, ("year",), tol, floor, kind)
        t_pooled = M.score_table(preds, (), tol, floor, kind)
        for name, table in (("score_by_group.csv", t_group), (PER_YEAR, t_year), ("score_pooled.csv", t_pooled)):
            REC.write_text_once_or_same(folder / name, REC.csv_text(table))
        strata = self._strata(preds, tol, floor, kind)
        self._preclip(preds)
        seen = [g for g in p.split_sets.seen_during_design if g in self.groups]
        if seen:
            t_seen = M.score_table(preds[~preds["group"].isin(seen)].reset_index(drop=True), (), tol, floor, kind)
            REC.write_text_once_or_same(folder / "score_pooled_without_seen_during_design.csv",
                                        REC.csv_text(t_seen))

        a = self.adoption
        declined = bool(a.declined)
        adopted_arm = LA.trees_off_of(Link.IDENTITY) if declined else a.adopted
        own_link = Link.IDENTITY if declined else a.adopted.link
        adopted_col = M.ARM_PREFIX + LA.arm_name(adopted_arm)
        ref_col = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(own_link))
        scored_cols = [c for c in preds.columns if c.startswith((M.ARM_PREFIX, M.PLACEBO_PREFIX))]
        per_group = {c: M.metric_by_key(t_group, c, "mae", "group") for c in scored_cols}

        def pooled(col):
            sel = t_pooled[(t_pooled["line"] == M.LINE_POOLED) & (t_pooled["column"] == col)
                           & (t_pooled["rows_basis"] == M.ROWS_BASIS_ALL)]
            return float(sel["mae"].iloc[0])
        pairs = []
        for L in self.links:
            off = M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(L))
            for w in self.weightings():             # D75: each tree arm vs its trees-off, each corrector vs its placebo
                plain = M.ARM_PREFIX + LA.arm_name(LA.ArmSpec(L, LA.Tool.PLAIN, w, True))
                corr = M.ARM_PREFIX + LA.arm_name(LA.ArmSpec(L, LA.Tool.CORRECTOR, w, True))
                plac = M.PLACEBO_PREFIX + LA.arm_name(LA.ArmSpec(L, PLACEBO, w, False))
                pairs += [(off, plain), (off, corr), (plac, corr)]
        band, band_records = M.band_from_pairs(per_group, pairs)
        tagged = []
        for rec in band_records:
            groups = sorted(per_group[rec["reference"]])
            dv = np.array([per_group[rec["reference"]][g] - per_group[rec["arm"]][g] for g in groups])
            tag, _ = M.contrast_tag(dv, band)
            tagged.append(dict(rec, tag=tag.value))
        verdict = M.single_verdict(per_group[ref_col], per_group[adopted_col], pooled(ref_col), pooled(adopted_col),
                                   band, declined, M.REFERENCE_OWN_LINK_TREES_OFF)
        contrast = {g: per_group[ref_col][g] - per_group[adopted_col][g] for g in per_group[ref_col]}
        block_index = dict(p.blocks.block_of_group)
        blocked = M.blocked_jackknife(contrast, {g: block_index[g] for g in contrast})
        blocked_flag = M.blocked_jackknife_flag(verdict.contrast, blocked)
        beside = {"arithmetic_normal_mae": pooled(M.ARM_PREFIX + LA.arm_name(LA.trees_off_of(Link.IDENTITY)))}
        base_rows = t_pooled[(t_pooled["line"] == M.LINE_POOLED) & (t_pooled["column_kind"] == "baseline")]
        for _, r in base_rows.iterrows():
            beside["%s_mae@%s" % (r["column"], r["rows_basis"])] = float(r["mae"])
        # per-group lines (with the noise note and the overlap block)
        members = {g: "+".join(p.blocks.members[i]) for g, i in block_index.items()}
        lines = []
        for g in sorted(per_group[adopted_col]):
            sub = preds[preds["group"] == g]
            n_units = int(sub["unit"].nunique())
            lines.append({"group": g, "scored_units": n_units, "test_rows": int(len(sub)),
                          "labelled_rows": int(np.isfinite(sub["y"].to_numpy(dtype=np.float64)).sum()),
                          "overlap_block": members[g], "mae_adopted": per_group[adopted_col][g],
                          "mae_reference": per_group[ref_col][g], "contrast": contrast[g],
                          "noise_note": NOISE_NOTE % n_units})
        REC.write_text_once_or_same(folder / "per_group.csv", REC.csv_text(pd.DataFrame(lines)))
        jk = [dict(r, kind="band_pair") for r in tagged]
        jk.append({"kind": "single_verdict", "reference": ref_col, "arm": adopted_col,
                   "mean": verdict.contrast.mean, "se": verdict.contrast.se, "low": verdict.contrast.low,
                   "high": verdict.contrast.high, "n_groups": verdict.contrast.n_groups, "tag": verdict.tag.value})
        jk.append({"kind": "blocked_jackknife (report only)", "reference": ref_col, "arm": adopted_col,
                   "mean": blocked.mean, "se": blocked.se, "low": blocked.low, "high": blocked.high,
                   "n_groups": blocked.n_groups, "tag": "flag: group jackknife may be too narrow" if blocked_flag else ""})
        REC.write_text_once_or_same(folder / "jackknife.csv", REC.csv_text(pd.DataFrame(jk)))
        checks = read_json(folder / DECISION_CHECKS)
        self._guard_report(checks, strata)
        rec = {"kind": kind, "package": p.package.dataset.name, "run_fingerprint": p.fingerprint,
               "draft": p.draft.record(), "headline_eligible": not p.not_headline,
               "not_headline_reasons": list(p.not_headline),
               "listed_in_reports": list(p.spec.listed_in_reports),
               "adopted": LA.arm_name(adopted_arm), "declined": declined,
               "penalty": None if a.penalty is None else {"level": a.penalty.level, "ratio": a.penalty.ratio},
               "best_tree_arm": LA.arm_name(a.best_tree_arm),
               "best_tree_penalty": {"level": a.best_tree_penalty.level, "ratio": a.best_tree_penalty.ratio},
               "adoption_sha256": self.adoption_sha, "reference": ref_col,
               "verdict": M.verdict_record(verdict), "band": band,
               "band_source": "this run's own D75 contrasts (each tree arm vs its own trees-off, each corrector "
                              "vs its placebo; R35 derives the band from the package's first headline run, and "
                              "registry/bands.csv is not written by the engine yet)",
               "band_pairs": tagged, "blocked_jackknife": {"mean": blocked.mean, "se": blocked.se,
                                                           "low": blocked.low, "high": blocked.high,
                                                           "n_blocks": blocked.n_groups, "flag": blocked_flag},
               "pooled_mae_adopted": pooled(adopted_col), "pooled_mae_reference": pooled(ref_col),
               "beside": beside, "hit_tolerance": tol, "measurement_error_floor": floor,
               "n_groups": len(per_group[adopted_col]), "scored_units": len(self.scored_units),
               "test_rows": int(len(preds)), "history_filled_share": self.history_filled,
               "inner_history": checks.get("inner_history"), "strata": strata,
               "router_kind": self.kind, "gls_arms": self.gls_record(), "tolerances": self.tol_record,
               TIMINGS_KEY: dict(self.timings, report=round(time.time() - t0, 2))}
        if p.draft.is_draft:
            rec = dict({"DRAFT": "DRAFT: %s -- never a headline number" % p.draft.stamp}, **rec)
        path = folder / REC.VERDICT_FILE
        if path.exists():
            # a resumed report: the same verdict (timings are the only field a process may change)
            if _without(read_json(path), TIMINGS_KEY) != _without(rec, TIMINGS_KEY):
                raise PassRefusal("G-FINGERPRINT", "%s exists with another verdict" % path, fix="start a new run")
        else:
            M.write_json_once(rec, path)
        self.log("verdict: %s adopted %s vs %s: contrast %.6g [%.6g, %.6g], band %.6g, pooled MAE %.6g vs %.6g"
                 % (verdict.tag.value, rec["adopted"], ref_col, verdict.contrast.mean, verdict.contrast.low,
                    verdict.contrast.high, band, rec["pooled_mae_adopted"], rec["pooled_mae_reference"]))
        return {"verdict": verdict.tag.value, "adopted": rec["adopted"], "band": band,
                "pooled_mae_adopted": rec["pooled_mae_adopted"], "pooled_mae_reference": rec["pooled_mae_reference"],
                "draft": p.draft.is_draft, "test_rows": rec["test_rows"]}

    def _guard_report(self, checks: Mapping[str, Any], strata: Mapping[str, Any]) -> None:
        """guard_report.json: what each runtime guard of this run checked, and which guards did not run."""
        p = self.p
        folder = p.folder
        opened = folder / (OPENED_FILE % 0)
        a = self.adoption
        report = {
            "run_fingerprint": p.fingerprint,
            "ran": {
                "G-PLUMB": checks["g_plumb"],
                "N2 (R27)": {"eligible": [LA.arm_name(x) for x in a.eligible], "declined": bool(a.declined),
                             "surface_mae": dict(a.surface_mae)},
                "G-LOCK": {"adoption_sha256": self.adoption_sha, "manifest_addendum": MANIFEST_ADOPTION,
                           "test_labels_opened": read_json(opened) if opened.is_file() else None},
                "G-DISJOINT": {"overlap_blocks": len(p.blocks.members),
                               "rule": "each router drops its own overlap block's tree columns "
                                       "(own_block_tree_columns); route.kinds asserts it at every router fit"},
                "G-SPLIT (outputs)": "test_preds.parquet scores exactly each group's derived scored units",
                "G-CLIP": "every prediction and baseline clipped to the legal range; counts in %s" % PRECLIP,
                "R36": checks["tolerances"],
                "R12": {"router_kind": self.kind, "fallback_decision_surface": checks.get("fallback"),
                        "fallback_levels": checks.get("fallback_levels"),
                        "fallback_test_pass": (read_json(folder / "test_pass_router.json").get("records", {})
                                               .get("fallback") if (folder / "test_pass_router.json").is_file()
                                               else None)},
                "G-FITCUT": "every hand-out in %s (per part under phases/)" % FITCTX_LOG,
                "feature lineage": p.feature_lineage,
                "R34 strata": strata or "no report_stratum column declared",
            },
            "not_run": [NOT_RUN_GUARDS],
            "departures": [r for r in p.not_headline if r.startswith("departure ")],
        }
        REC.write_once_or_same(folder / GUARD_REPORT, report)


PHASE = "decision"
PHASE_T = "test_pass"

__all__ = ["RunState", "PassRefusal", "HistoryOverride", "MANIFEST_ADOPTION", "LOG_PARTS"]
