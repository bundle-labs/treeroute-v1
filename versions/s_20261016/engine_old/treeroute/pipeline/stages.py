"""The pipeline's stages between derive_all and the report (plan 4.1 steps 3-9): the label vault on the
dense grid, the feature pool with the own-history block, the banks and their tree-answer stores, the
router passes and the R36 tolerances.

Orchestration only. Every rule is its approved module's: the grid (io.steps.build_dense_grid), the
vault (labels.vault.LabelView), the history block (io.apply.history_block), FitContext and its
containers (fit.context), the bank (fit.bank.fit_donor_bank), the tree-answer store (fit.tables), the
GLS weight model (fit.weights), the normals and the per-unit router (route.kinds), the links and the
clip (layer.links), the tolerance's s (report.metrics.guard_tolerance).

The routers themselves are dispatched by pipeline/router.py (the per-unit kernels of route.kinds, with
the region fallback of route/region.py for short-history units and the GLS-weighted solve; the region
kernels of route/region.py). This module gives it the pieces: the normal columns from NormalTables built
at the pass's cut and link (R15, _normals_on refuses a table of another cut, link or c), the masks only
from own_block_tree_columns over the overlap blocks (R14, G-DISJOINT), and the router rows.

Owner ruling G1 (owner rulings, section G) is applied where the router rows are assembled (pass_rows): a fit
row whose router context is missing or non-finite leaves the per-unit router's fit, as a row with a missing
label does (R30), counted per unit (drop_missing_context, flagged above the engine constant
C10.context_missing_flag_share of a unit's fit rows) and listed row by row (ContextMissingRows: unit, step,
grid position, the missing columns); nothing is filled; the router's normal of a unit that lost rows is
built from its kept fit rows, read through FitContext.unit_history less the rows G1 left out (R15 on the fit
rows, so R16 holds: context_kept_histories); a scored row with missing context refuses (check_score_context;
at a forecast lead, owner ruling H4 first takes the test rows whose issue row is absent out of the scored
rows, pipeline.ladder); route.kinds' R20 refusal is unchanged and stays as the last guard. The kept rows are
logged (G-FITCUT): each FitContext
hand-out G1 trims gets a twin fitctx_log row with the purpose suffix G1_KEPT_SUFFIX and the kept rows'
count, newest label step and row-key hash (g1_kept_log_row), which the run state writes right after the
hand-out's own row.
"""

from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import timing
from treeroute.derive.shapes import Link
from treeroute.errors import RefusedError
from treeroute.fit.context import FitContext, FitCtxLogRow, season_keys_of
from treeroute.io.apply import history_block
from treeroute.io.steps import build_dense_grid, step_bounds
from treeroute.labels.vault import LabelView, row_key_hash
from treeroute.layer.links import link_forward, link_inverse
from treeroute.report import metrics as M
from treeroute.route import kinds as RK
from treeroute import split as SP

R36_STANDIN = ("C9.guard_tolerance_k is unset: smoke stand-in k = C9.identity_gate / s(identity), so the "
               "identity gate is the identity_gate constant and every link's tolerance is k x s(link); "
               "plumbing only, never a headline number")


class StageRefusal(RefusedError):
    """A pipeline stage refused (fail loudly)."""


# ---------------------------------------------------------------------------------------------------
# The vault on the dense grid
@dataclass
class VaultGrid:
    grid: Any
    labels: LabelView
    unit_ids: np.ndarray            # per grid position
    steps: np.ndarray               # per grid position
    window_end: np.ndarray          # per grid position: the last day of the row's own label window
    first_step: int
    last_step: int
    test_first: int


def label_window_ends(steps: np.ndarray, cadence: Any, target_facts: Any) -> np.ndarray:
    """The last day of each step's own label window (timing.target_content, reach facts included)."""
    distinct, inverse = np.unique(np.asarray(steps, dtype=np.int64), return_inverse=True)
    first, last = step_bounds(distinct, cadence)
    ends = np.array([timing.target_content(target_facts, (int(a), int(b)))[1]
                     for a, b in zip(first.tolist(), last.tolist())], dtype=np.int64)
    return ends[np.asarray(inverse).reshape(-1)]


def build_vault(unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray, y: np.ndarray,
                coverage: Tuple[int, int], test_first: int, cadence: Any, target_facts: Any,
                run_folder: Any) -> VaultGrid:
    """The keys-only dense grid over the given target rows (their census inside the coverage) and the
    label vault built on it (the ONLY holder of the labels, G-LOCK)."""
    lo, hi = int(coverage[0]), int(coverage[1])
    inside = (steps >= lo) & (steps <= hi)
    u, g, s, yy = unit_ids[inside], group_ids[inside], steps[inside], y[inside]
    grid = build_dense_grid(u, g, s, (lo, hi))
    wend = label_window_ends(s, cadence, target_facts)
    target = SimpleNamespace(unit_ids=u, group_ids=g, y=yy)
    labels = LabelView(grid, target, s, int(test_first), wend, run_folder, cadence=cadence)
    n = int(grid.n_steps)
    pos_steps = np.tile(np.arange(lo, lo + n, dtype=np.int64), len(grid.unit_ids))
    pos_units = np.repeat(np.asarray(grid.unit_ids, dtype=object), n)
    return VaultGrid(grid=grid, labels=labels, unit_ids=pos_units, steps=pos_steps,
                     window_end=label_window_ends(pos_steps, cadence, target_facts),
                     first_step=lo, last_step=hi, test_first=int(test_first))


def unit_positions(vg: VaultGrid, units: Sequence[str], first: Optional[int] = None,
                   last: Optional[int] = None) -> np.ndarray:
    """Grid positions of the given units' steps inside [first, last], ascending (unit by unit, step
    order: the tree-answer store's row order)."""
    row_of = {u: i for i, u in enumerate(vg.grid.unit_ids)}
    n = int(vg.grid.n_steps)
    lo = vg.first_step if first is None else max(int(first), vg.first_step)
    hi = vg.last_step if last is None else min(int(last), vg.last_step)
    if hi < lo:
        return np.zeros(0, dtype=np.int64)
    rows = sorted(row_of[u] for u in units)
    offs = np.arange(lo - vg.first_step, hi - vg.first_step + 1, dtype=np.int64)
    return (np.asarray(rows, dtype=np.int64)[:, None] * n + offs[None, :]).reshape(-1)


def row_group_of(vg: VaultGrid) -> Callable[[np.ndarray], np.ndarray]:
    """The tree-answer store's row-group source: the grid's own unit -> group key (ruling D)."""
    groups = np.asarray(vg.grid.group_of_unit, dtype=object)
    n = int(vg.grid.n_steps)

    def row_group(ids: np.ndarray) -> np.ndarray:
        return groups[np.asarray(ids, dtype=np.int64) // n]
    return row_group


# ---------------------------------------------------------------------------------------------------
# The pool (tree features + the own-history block, router context)
def history_inputs(ctx: FitContext, vg: VaultGrid, split: Any, bank_units: Sequence[str]) -> Tuple[Dict[str, Any], float]:
    """R17's fallback inputs at the context's cut: each unit's UnitHistory (normal_fill) and the
    donor-row mean of y (a label-only donor view of the bank units; F1's last fallback)."""
    fill = {u: ctx.unit_history(u, "history_fill") for u in vg.grid.unit_ids}
    view = vg.labels.donor_labels(split, ctx.cut, ctx.cut_kind, ctx.lead, tuple(bank_units), "history_fill",
                                  picks=ctx.picks)
    y = np.asarray(view.y, dtype=np.float64)
    if y.size == 0:
        raise StageRefusal("R17", "no donor row at the cut: the history block's last fallback is undefined")
    return fill, float(y.mean())


def fill_pool(pool: Any, vg: VaultGrid, lagged_rows: Callable[[np.ndarray], np.ndarray],
              context_rows: Callable[[np.ndarray], Optional[np.ndarray]], history: np.ndarray,
              echo: Callable[[str], None]) -> None:
    """Write every pool row once, in row blocks: the lagged tree features and the history block, then
    the router context."""
    rows = np.asarray(pool.grid_rows, dtype=np.int64)
    block = 50000
    for a0 in range(0, rows.size, block):
        r = rows[a0:a0 + block]
        tree = np.hstack([lagged_rows(r), history[a0:a0 + block]]) if history.shape[1] else lagged_rows(r)
        pool.write(r, tree.astype(np.float32), context_rows(r))
    pool.require_complete()
    echo("pool: %d rows x %d tree columns, %d context columns" % (rows.size, len(pool.tree_columns),
                                                                  len(pool.context_columns)))


def zero_filled(pool: Any) -> Callable[[np.ndarray], np.ndarray]:
    """The tree-answer store's feature source: the pool's tree features with R30's 0-fill, float32."""
    def features(ids: np.ndarray) -> np.ndarray:
        X = np.array(pool.tree_features(np.asarray(ids, dtype=np.int64)), dtype=np.float32, copy=True)
        if np.isinf(X).any():
            raise StageRefusal("R30", "%d tree feature values are infinite" % int(np.isinf(X).sum()))
        X[np.isnan(X)] = 0.0
        return X
    return features


# ---------------------------------------------------------------------------------------------------
# R36 tolerances
def guard_tolerances(donor_rows: Any, links: Sequence[Any], c: Optional[float], ub: Optional[float],
                     smoke: bool) -> Tuple[Dict[Any, float], Dict[str, Any]]:
    """R36: max(k x s, floor) per link, s = the donor-row standard deviation of link(y) (report.metrics).
    k is C9; while C9 is unset a smoke run uses the stand-in R36_STANDIN (recorded) and a headline run
    refuses (UnsetConstantError from the constants registry). The floor is owner ruling O4
    (the owner rulings file, section O): C9.k_min_multiple_of_arith_error x C9.measured_arith_error
    (route.kinds.r36_floor), recorded with the tolerances."""
    s = {L: M.guard_tolerance(donor_rows, L, c if L == Link.LOG_C else None,
                              ub if L == Link.ARCSINE else None, 1.0) for L in links}
    record: Dict[str, Any] = {"s": {getattr(L, "value", str(L)): v for L, v in s.items()}}
    if K.GUARD_TOLERANCE_K is K.UNSET:
        if not smoke:
            K.get("C9.guard_tolerance_k")          # raises UnsetConstantError: the owner sets k first
        k = float(K.IDENTITY_GATE) / s[Link.IDENTITY]
        record.update(k=k, standin=True, note=R36_STANDIN)
    else:
        k = float(K.get("C9.guard_tolerance_k"))
        record.update(k=k, standin=False)
    floor = RK.r36_floor()                          # owner ruling O4: max(k x s, the floor)
    tol = {L: max(k * v, floor) for L, v in s.items()}
    record.update(floor=floor, floor_rule=RK.R36_FLOOR_RULE)
    record["tolerance"] = {getattr(L, "value", str(L)): v for L, v in tol.items()}
    return tol, record


# ---------------------------------------------------------------------------------------------------
# Normals (R15) and the router rows
def donor_link_means(donor_rows: Any, links: Sequence[Any], c: Optional[float], ub: Optional[float]) -> Dict[Any, float]:
    """R15's last fallback per link: the donor-row mean of link(y) at the cut."""
    y = np.asarray(donor_rows.y, dtype=np.float64)
    return {L: float(np.mean(link_forward(y, L, c if L == Link.LOG_C else None, ub if L == Link.ARCSINE else None)))
            for L in links}


def unit_normals(ctx: FitContext, units: Sequence[str], link: Any, c: Optional[float], ub: Optional[float],
                 donor_mean: float, season: Any, histories: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """R15 at the context's cut and one link: each unit's NormalTable (route.kinds.season_normal on the
    link values of its UnitHistory), covering every season key."""
    keys_all = np.arange(1, int(season.steps_per_year) + 1, dtype=np.int64)
    out = {}
    for u in units:
        h = histories[u] if histories is not None else ctx.unit_history(u, "normal")
        z = link_forward(np.asarray(h.y, dtype=np.float64), link, c if link == Link.LOG_C else None,
                         ub if link == Link.ARCSINE else None)
        out[u] = RK.season_normal(u, link, int(ctx.cut), c, np.asarray(h.times, dtype=np.int64),
                                  np.asarray(h.season_keys, dtype=np.int64), z, keys_all, float(donor_mean))
    return out


def _normals_on(normals: Mapping[str, Any], units: np.ndarray, keys: np.ndarray, link: Any, cut: int,
                c: Optional[float]) -> np.ndarray:
    out = np.empty(units.size, dtype=np.float64)
    for u in np.unique(units.astype(str)):
        table = normals[u]
        if table.cut != int(cut) or table.link != link or (link == Link.LOG_C and table.c != c):
            raise StageRefusal("R15", "unit %s: its normal was built at cut %s, link %s, c %s; this pass is at "
                               "cut %d, link %s, c %s" % (u, table.cut, table.link, table.c, cut, link, c))
        sel = units == u
        out[sel] = RK.normal_values(table, keys[sel])
    return out


# ---------------------------------------------------------------------------------------------------
# Owner ruling G1 (OWNER_RULINGS_2026-09-28.md section G, 2026-10-05): missing router context on fit rows.
# The flag share ("flagged above 5% of a unit's fit rows", report only) is the engine constant
# C10.context_missing_flag_share (engine_constants.CONTEXT_MISSING_FLAG_SHARE), read at each call.
G1_RULE =("owner ruling G1: a router fit row whose context (read at the pass's issue step) is missing or "
           "non-finite leaves the router fit, as a row with a missing label does (R30); nothing is filled; a "
           "scored row with missing context refuses; route.kinds' R20 refusal stays as the last guard")
G1_SCOPE = ("the per-unit router's fit rows (the scored units' own rows: the only router that reads context); "
            "the region kernels (the region kind and the R12 fallback) read no context, so their fit rows "
            "are not filtered")
G1_NORMAL = ("the router's normal (R15: the mean of link(y) over the unit's own fit rows) of a unit that lost "
             "rows is built from its kept fit rows (its FitContext unit history less the rows G1 left out), as "
             "for a row with a missing label, so trees-off still equals the normal (R16); the pass's score-row "
             "normal (guess-normal, the decline target, the saved normal column) and, at a lead's test pass, "
             "damped persistence's normal are that same normal, while damped persistence's phi is fitted on "
             "every label of the unit's history (two row sets in one baseline); owner ruling pending on this "
             "normal")
G1_KEPT_SUFFIX = ":g1_kept"    # the purpose suffix of a fitctx_log row that records the rows G1 kept
MISSING_PREFIX = "missing__"   # the column prefix of the saved left-out rows: one flag per context column


@dataclass(frozen=True)
class ContextKeptRows:
    """The router fit rows of one pass after owner ruling G1: the RouterRows FitContext.router_rows handed out,
    less the rows whose router context is missing or non-finite, in the same order. The fields are RouterRows'
    (the scalers and the kernels read them by name). Built only by drop_missing_context, from issued rows."""
    cut: int
    cut_kind: Any
    lead: int
    unit_ids: np.ndarray
    times: np.ndarray
    row_positions: np.ndarray
    y: np.ndarray
    context: np.ndarray


@dataclass(frozen=True)
class ContextMissingRows:
    """The router fit rows owner ruling G1 left out of one pass, one entry per row in the RouterRows' order:
    the unit, the label step, the grid position and, per context column, whether its value was missing or
    non-finite (the row's context is read at its issue step: the label step less the lead). Built only by
    drop_missing_context; frame() is what the run saves."""
    cut: int
    cut_kind: Any
    lead: int
    columns: Tuple[str, ...]
    unit_ids: np.ndarray
    times: np.ndarray
    row_positions: np.ndarray
    missing: np.ndarray             # bool, (rows, context columns)

    def frame(self, what: str, purpose: str) -> pd.DataFrame:
        """One row per left-out fit row: the pass, its router_rows purpose, lead, cut kind and cut, then the
        row's unit, label step, issue step, grid position and one MISSING_PREFIX flag per context column."""
        n = int(np.asarray(self.times).size)
        cols: Dict[str, Any] = {
            "pass": np.full(n, str(what), dtype=object), "purpose": np.full(n, str(purpose), dtype=object),
            "lead": np.full(n, int(self.lead), dtype=np.int64),
            "cut_kind": np.full(n, str(getattr(self.cut_kind, "value", self.cut_kind)), dtype=object),
            "cut": np.full(n, int(self.cut), dtype=np.int64), "unit": np.asarray(self.unit_ids, dtype=object),
            "time": np.asarray(self.times, dtype=np.int64),
            "issue": np.asarray(self.times, dtype=np.int64) - int(self.lead),
            "row_position": np.asarray(self.row_positions, dtype=np.int64)}
        for j, c in enumerate(self.columns):
            cols[MISSING_PREFIX + c] = np.asarray(self.missing[:, j], dtype=bool)
        return pd.DataFrame(cols)


def g1_kept_log_row(ctx: FitContext, object_kind: str, purpose: str, units: np.ndarray, times: np.ndarray,
                    kept_units: np.ndarray, kept_times: np.ndarray) -> Tuple[int, FitCtxLogRow]:
    """The fitctx_log row of the rows owner ruling G1 kept from one hand-out (G-FITCUT: the log records what
    was fitted). Called right after the hand-out: the context's newest log row must be that hand-out's
    (same object kind, purpose, row count and row-key hash; else an internal refusal). The twin keeps the
    hand-out's lead, cut kind, cut, groups hash and fold, and takes the purpose plus G1_KEPT_SUFFIX and the
    kept rows' count, newest label step (-1 when none) and row-key hash.
    Returns (the context's log length at that moment, the twin): the run state writes the twin right after
    the hand-out's own row."""
    log = ctx.log()
    src = log[-1] if log else None
    t_all = np.asarray(times, dtype=np.int64)
    if (src is None or src.object_kind != object_kind or src.purpose != purpose or src.n_rows != int(t_all.size)
            or src.row_key_hash != row_key_hash(np.asarray(units, dtype=object), t_all)):
        raise StageRefusal("G-FITCUT", "internal: the context's newest log row is not the %s hand-out (purpose %r, "
                           "%d rows) whose kept rows G1 logs" % (object_kind, purpose, t_all.size))
    t = np.asarray(kept_times, dtype=np.int64)
    if t.size and int(t.max()) > int(src.cut):
        raise StageRefusal("G-FITCUT", "internal: a G1-kept row is dated after the cut %d" % int(src.cut))
    twin = replace(src, purpose=purpose + G1_KEPT_SUFFIX, max_label_time=int(t.max()) if t.size else -1,
                   n_rows=int(t.size), row_key_hash=row_key_hash(np.asarray(kept_units, dtype=object), t))
    return len(log), twin


def drop_missing_context(fit: Any, context_columns: Sequence[str]) -> Tuple[Any, Dict[str, Any],
                                                                          Optional[ContextMissingRows]]:
    """Owner ruling G1 on one pass's router fit rows (FitContext.router_rows: labelled rows at or before the
    cut, their context read at each row's issue step, NaN kept). A row with any missing or non-finite context
    value leaves the fit, as a row with a missing label does (R30); no value is filled or invented.

    Returns (the fit rows, the G1 record, the rows left out). When no row leaves, the RouterRows object itself
    comes back with None for the rows left out, so the pass is byte for byte what it was before G1. Otherwise
    a ContextKeptRows holds the kept rows in their order and a ContextMissingRows the rows left out (unit,
    step, grid position, which context columns were missing). The record counts the rows per unit (the
    unit's fit rows before G1, the rows left out, their share, flagged above C10.context_missing_flag_share), per
    context column and per step.
    Refuses: context that is not (fit rows, context columns); a pass whose every fit row lost its context
    (the router would have no fit row)."""
    cols = tuple(str(c) for c in context_columns)
    units = np.asarray(fit.unit_ids, dtype=object)
    times = np.asarray(fit.times, dtype=np.int64)
    n = int(units.size)
    C = np.asarray(fit.context, dtype=np.float64)
    if not cols or C.ndim != 2 or C.shape != (n, len(cols)) or times.shape != (n,):
        raise StageRefusal("R20", "the router fit rows hold context of shape %s for %d rows of %d context "
                           "columns" % (C.shape, n, len(cols)))
    bad_cell = ~np.isfinite(C)
    bad = bad_cell.any(axis=1)
    flag_share = float(K.CONTEXT_MISSING_FLAG_SHARE)
    per_unit_rows = {}
    if n:
        uniq, counts = np.unique(units.astype(str), return_counts=True)
        per_unit_rows = {str(u): int(k) for u, k in zip(uniq.tolist(), counts.tolist())}
    by_unit: Dict[str, Any] = {}
    if bad.any():
        lost_u, lost_n = np.unique(units[bad].astype(str), return_counts=True)
        for u, k in zip(lost_u.tolist(), lost_n.tolist()):
            share = float(k) / float(per_unit_rows[u])
            by_unit[u] = {"left_out": int(k), "fit_rows": per_unit_rows[u], "share": share,
                          "flagged": bool(share > flag_share)}
    steps, step_n = np.unique(times[bad], return_counts=True)
    record: Dict[str, Any] = {
        "rule": G1_RULE, "scope": G1_SCOPE, "normal": G1_NORMAL, "context_columns": len(cols), "fit_rows": n,
        "units_in_fit": len(per_unit_rows), "rows_left_out": int(bad.sum()),
        "units_with_rows_left_out": len(by_unit), "flag_share": flag_share,
        "flag_share_constant": "C10.context_missing_flag_share",
        "flagged_units": sorted(u for u, d in by_unit.items() if d["flagged"]),
        "by_column": {c: int(bad_cell[:, j].sum()) for j, c in enumerate(cols) if bad_cell[:, j].any()},
        "by_step": {str(int(t)): int(k) for t, k in zip(steps.tolist(), step_n.tolist())},
        "by_unit": by_unit}
    if not bad.any():
        return fit, record, None
    if bad.all():
        raise StageRefusal("G1", "every one of the %d router fit rows has missing or non-finite context (%s): the "
                           "router has no fit row left" % (n, record["by_column"]),
                           fix="the context columns must be readable at the fit rows' issue steps (check their "
                               "coverage and lags against the package's first year)")
    keep = np.flatnonzero(~bad)
    lost = np.flatnonzero(bad)
    positions = np.asarray(fit.row_positions, dtype=np.int64)
    out = ContextKeptRows(cut=int(fit.cut), cut_kind=fit.cut_kind, lead=int(fit.lead), unit_ids=units[keep],
                          times=times[keep], row_positions=positions[keep],
                          y=np.asarray(fit.y)[keep], context=np.asarray(fit.context)[keep])
    left = ContextMissingRows(cut=int(fit.cut), cut_kind=fit.cut_kind, lead=int(fit.lead), columns=cols,
                              unit_ids=units[lost], times=times[lost], row_positions=positions[lost],
                              missing=bad_cell[lost])
    return out, record, left


def context_kept_histories(ctx: FitContext, units: Sequence[str],
                           rows: "PassRows") -> Tuple[Optional[Dict[str, Any]], Tuple[Tuple[int, FitCtxLogRow], ...]]:
    """Owner ruling G1 with R15 (the normal is the mean over the unit's own fit rows; G1_NORMAL): when G1 left
    rows out of the pass's fit, every unit's history comes from FitContext.unit_history(unit, 'normal')
    (logged: one 'normal' entry per unit, as before G1), and a unit that lost rows takes that history less
    the rows G1 left out. That trimmed history must be exactly the unit's kept fit rows (times and label
    bytes; else an internal refusal), and it is logged as the hand-out's G1_KEPT_SUFFIX twin
    (g1_kept_log_row). The season keys are the unit history's own (derived.json's R2).
    Returns (the histories, the twins with the context's log length when each was made); (None, ()) when G1
    left no row out: the normals are then built exactly as before G1."""
    rec = rows.context_missing
    if rec is None or not rec["rows_left_out"]:
        return None, ()
    left = rows.left_out
    if left is None:
        raise StageRefusal("G1", "internal: the pass left %d fit rows out but holds no list of them"
                           % int(rec["rows_left_out"]))
    lost = set(rec["by_unit"])
    fu = np.asarray(rows.fit.unit_ids, dtype=object).astype(str)
    ft = np.asarray(rows.fit.times, dtype=np.int64)
    fy = np.asarray(rows.fit.y)
    lu = np.asarray(left.unit_ids, dtype=object).astype(str)
    lt = np.asarray(left.times, dtype=np.int64)
    out: Dict[str, Any] = {}
    logs = []
    for u in units:
        h = ctx.unit_history(u, "normal")
        if str(u) not in lost:
            out[u] = h
            continue
        times = np.asarray(h.times, dtype=np.int64)
        keep = ~np.isin(times, lt[lu == str(u)])
        y = np.asarray(h.y)[keep]
        sel = fu == str(u)
        if not (np.array_equal(times[keep], ft[sel]) and y.dtype == fy.dtype and y.tobytes() == fy[sel].tobytes()):
            raise StageRefusal("G1", "internal: unit %s's history less its %d rows left out is not its kept fit rows "
                               "(%d history rows kept, %d fit rows)" % (u, int((~keep).sum()), int(keep.sum()),
                                                                         int(sel.sum())))
        logs.append(g1_kept_log_row(ctx, "unit_history", "normal", np.full(times.size, str(u), dtype=object), times,
                                    np.full(int(keep.sum()), str(u), dtype=object), times[keep]))
        out[u] = SimpleNamespace(times=times[keep], season_keys=np.asarray(h.season_keys)[keep], y=y)
    return out, tuple(logs)


def check_score_context(score_context: np.ndarray, score_units: np.ndarray, score_steps: np.ndarray,
                        context_columns: Sequence[str], purpose: str) -> None:
    """Owner ruling G1: a SCORED row with missing or non-finite router context refuses loudly (it is never
    filled and never dropped here). Owner ruling H4 (a test row whose issue-step features are missing is left
    out of scoring, saved with a flag and counted) is applied BEFORE this check, by the forecast ladder's test
    pass (pipeline.ladder: a test row whose issue row is absent is never handed to a router), so a row that
    reaches this check with missing context still refuses."""
    C = np.asarray(score_context, dtype=np.float64)
    if C.size == 0 or np.isfinite(C).all():
        return
    bad = ~np.isfinite(C).all(axis=1)
    cols = [str(c) for j, c in enumerate(context_columns) if (~np.isfinite(C[:, j])).any()]
    units = np.asarray(score_units, dtype=object)[bad]
    steps = np.asarray(score_steps, dtype=np.int64)[bad]
    first = ", ".join("%s@%d" % (u, int(t)) for u, t in list(zip(units.tolist(), steps.tolist()))[:5])
    raise StageRefusal("G1", "%s: %d scored row(s) of %d unit(s) have missing or non-finite router context (columns "
                       "%s; first rows %s); a scored row's context is never filled and the row is never dropped"
                       % (purpose, int(bad.sum()), len(set(units.astype(str).tolist())), cols, first),
                       fix="the context columns must be readable at every scored row's issue step")


@dataclass
class PassRows:
    """One router pass's rows in y units (before the link): fit rows from FitContext.router_rows at the
    pass's cut (less the rows owner ruling G1 leaves out: left_out lists them, fit_log holds the
    router_rows hand-out's G1_KEPT_SUFFIX twin), score rows given by the caller."""
    cut: int
    fit: Any                        # RouterRows, or ContextKeptRows when G1 left rows out
    score_units: np.ndarray
    score_steps: np.ndarray
    score_keys: np.ndarray          # grid positions (tree-answer row ids)
    context_mean: Optional[np.ndarray]
    context_sd: Optional[np.ndarray]
    score_context: Optional[np.ndarray]
    context_missing: Optional[Dict[str, Any]] = None    # the G1 record (None: no context column)
    left_out: Optional[ContextMissingRows] = None        # the fit rows G1 left out (None: none)
    fit_log: Tuple[Tuple[int, FitCtxLogRow], ...] = ()   # the kept rows' fitctx_log twin (g1_kept_log_row)


def pass_rows(ctx: FitContext, units: Sequence[str], score_units: np.ndarray, score_steps: np.ndarray,
              score_keys: np.ndarray, purpose: str) -> PassRows:
    """The pass's router rows. With router context: owner ruling G1 first (drop_missing_context: fit rows whose
    context is missing leave the fit, listed in left_out, the kept rows logged as the router_rows hand-out's
    twin in fit_log; a scored row whose context is missing refuses), then the scalers on the kept fit rows
    (route.kinds.router_standardisation, whose R20 refusal stays as the last guard)."""
    raw = ctx.router_rows(tuple(units), purpose)
    fit = raw
    cols = tuple(ctx.features.context_columns)
    g1 = left = None
    fit_log: Tuple[Tuple[int, FitCtxLogRow], ...] = ()
    if cols:
        fit, g1, left = drop_missing_context(raw, cols)
        if fit is not raw:
            fit_log = (g1_kept_log_row(ctx, "router_rows", purpose, raw.unit_ids, raw.times, fit.unit_ids,
                                       fit.times),)
        mean, sd = RK.router_standardisation(fit, fit.context)
        score_ctx = np.asarray(ctx.features.context(score_keys), dtype=np.float64)
        check_score_context(score_ctx, score_units, score_steps, cols, purpose)
    else:
        mean = sd = score_ctx = None
    return PassRows(cut=int(ctx.cut), fit=fit, score_units=np.asarray(score_units, dtype=object),
                    score_steps=np.asarray(score_steps, dtype=np.int64),
                    score_keys=np.asarray(score_keys, dtype=np.int64), context_mean=mean, context_sd=sd,
                    score_context=score_ctx, context_missing=g1, left_out=left, fit_log=fit_log)


def per_unit_rows(rows: PassRows, link: Any, c: Optional[float], ub: Optional[float],
                  normals: Mapping[str, Any], season: Any, unit_group: Mapping[str, str]) -> Any:
    """route.kinds.PerUnitRows of one pass in one link (link-space labels and normals)."""
    fit = rows.fit
    fu = np.asarray(fit.unit_ids, dtype=object)
    ft = np.asarray(fit.times, dtype=np.int64)
    fk = season_keys_of(ft, season)
    sk = season_keys_of(rows.score_steps, season)
    cc = c if link == Link.LOG_C else None
    uu = ub if link == Link.ARCSINE else None
    fy = link_forward(np.asarray(fit.y, dtype=np.float64), link, cc, uu)
    fctx = sctx = None
    if rows.context_mean is not None:
        fctx = RK.standardise_context(fit.context, rows.context_mean, rows.context_sd)
        sctx = RK.standardise_context(rows.score_context, rows.context_mean, rows.context_sd)
    return RK.PerUnitRows(cut=rows.cut, fit_unit=fu, fit_time=ft, fit_y=fy,
                          fit_normal=_normals_on(normals, fu, fk, link, rows.cut, c),
                          fit_context=fctx, fit_keys=np.asarray(fit.row_positions, dtype=np.int64),
                          score_unit=rows.score_units, score_time=rows.score_steps,
                          score_normal=_normals_on(normals, rows.score_units, sk, link, rows.cut, c),
                          score_context=sctx, score_keys=rows.score_keys,
                          score_rows=np.arange(rows.score_units.size), unit_group=dict(unit_group))


def inverse(z: np.ndarray, link: Any, c: Optional[float], ub: Optional[float]) -> np.ndarray:
    """Link space back to y units (before the legal clip)."""
    return link_inverse(np.asarray(z, dtype=np.float64), link, c if link == Link.LOG_C else None,
                        ub if link == Link.ARCSINE else None)


def block_masks(tree_group: Sequence[str], blocks: Any) -> Any:
    """The router's own-overlap-block column masks (R14, G-DISJOINT): own_block_tree_columns over every
    group's whole block."""
    groups = sorted(set(tree_group))
    return RK.own_block_tree_columns(tuple(tree_group), {g: SP.block_of_group(blocks, g) for g in groups})


__all__ = ["R36_STANDIN", "StageRefusal", "VaultGrid", "label_window_ends", "build_vault",
           "unit_positions", "row_group_of", "history_inputs", "fill_pool", "zero_filled", "guard_tolerances",
           "donor_link_means", "unit_normals", "G1_RULE", "G1_SCOPE", "G1_NORMAL",
           "G1_KEPT_SUFFIX", "MISSING_PREFIX", "ContextKeptRows", "ContextMissingRows", "g1_kept_log_row",
           "drop_missing_context", "context_kept_histories", "check_score_context", "PassRows",
           "pass_rows",
           "per_unit_rows", "inverse", "block_masks", "history_block", "season_keys_of"]
