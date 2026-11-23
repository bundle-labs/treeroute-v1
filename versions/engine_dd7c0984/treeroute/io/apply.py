"""Applying computed lags, verdicts and freezes, and the own-history block (plan 1.4, 2.1 R8, R9,
2.3 R17, 4.1 steps 3-4; plan 5 G-CALENDAR, G-CLOSED, G-KEYS, G-HIST, G-LOCK).

SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/io_science.py:
  - apply_lags      R8: a column at the target's own step moves back by its computed lag, through
                    predecessor_index (never a row shift).
  - apply_verdicts  plan 1.4: where each non-key column goes (trees, router, report only, out).
  - apply_freezes   R9: a 'freeze' column holds each unit's value at the computed epoch.
  - history_block   R17: the engine's own-history block, read only through the label vault, with
                    the leak-free fallback of owner ruling F1.
  - features_at_issue_step  R8, R11: at lead L the whole feature row moves back to the issue step.
  - event_history_block     R17 for events: milestone M8 (raises NotImplementedError).

Owner rulings used (SIGNATURES_FOR_REVIEW.md defaults accepted; the owner rulings file in engine/):
  - D32: ALL rows of a frozen column take the unit's epoch value ("ONE pre-window epoch").
  - D33: a unit with no value at the epoch gets NaN (R30 counts it).
  - D83: trailing means use the AVAILABLE steps only, with no minimum count.
  - D84: the all-history mean starts at the first step of the dense grid.
  - D54 (a): the vault serves each row the labels known at that row's issue step.
  - R-D (b): the block starts one step further back when the target's window reaches past its step
    (spec.start_offset_steps, computed by R17 from the reach-after fact; 1 for such a target, so a
    nowcast block then ends at t-2).
  - F1: a missing history value takes the row's trailing means (1 year, then 5 years), then the
    unit's AS-OF season mean (its labels within the cut and at or before the row's newest readable
    step, same season key), then its as-of all-season mean, then the donor-row mean at the cut.
    Never 0, never a label at or after the row. This replaces the old last-resort normal (the
    unit's whole history at the cut, which could hold the row's own and later labels). Keeping the
    trailing means first, and using the target row's season, are readings awaiting the owner's
    confirmation (see history_block). The filled shares are returned and printed.
  - The newest readable step comes from timing.latest_label_step (R11), not a local copy.

Inputs are read by attribute, as the proposed shapes define them (Lag: column, steps,
column_cadence; HistorySpec: columns, last_values, trailing_steps, all_history_mean,
start_offset_steps, dropped_duplicates; UnitHistory: unit_id, times, season_keys, y, cut;
LabelView: asof_rows). Engine code may not import the proposed types (G-IMPORT).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, Tuple

import numpy as np
import pandas as pd

from treeroute.errors import RefusedError
from treeroute.io.steps import DenseGrid, as_int_array, cadence_identity, cadence_view, predecessor_index
from treeroute.timing import latest_label_step

_SHOW = 5

KEY_ROLES = ("key_unit", "key_group", "key_time")
TREE_ROLES = ("driver", "engineered")
CONTEXT_ROLES = ("router_context",)
REPORT_ROLES = ("support", "report_stratum", "external_product")
TARGET_ROLES = ("target", "target_twin")
ROLES = KEY_ROLES + TREE_ROLES + CONTEXT_ROLES + REPORT_ROLES + TARGET_ROLES
ENTER = ("keep", "keep_unreviewed", "watch", "freeze")
LEAVE = ("ban", "conditional")
LISTED = ("keep_unreviewed", "watch")

# Names of the history columns (the contract between R17's spec and this block).
HISTORY_LAST = "hist_last_%d"      # the j-th newest readable label, j = 1 .. last_values
HISTORY_MEAN = "hist_mean_%d"      # the trailing mean over w steps, ending at the newest readable
HISTORY_MEAN_ALL = "hist_mean_all"  # the mean of all history from the grid's first step


@dataclass(frozen=True)
class ColumnSets:
    """Where each entering column may go (plan 1.3 roles, G-KEYS). Every tuple keeps the order of
    the columns given. ``frozen`` and ``listed_in_reports`` are markers: their columns also sit in
    the set their role sends them to."""
    tree_features: Tuple[str, ...]
    router_context: Tuple[str, ...]
    report_only: Tuple[str, ...]        # support, report_stratum, external_product
    frozen: Tuple[str, ...]
    listed_in_reports: Tuple[str, ...]  # keep_unreviewed and watch


def _value(x: Any) -> Any:
    return x.value if isinstance(x, Enum) else x


def _int(x: Any, what: str, rule: str) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise RefusedError(rule, "%s must be an integer, got %r" % (what, x))
    return int(x)


def _check_rows(frame: pd.DataFrame, rule: str, **arrays: np.ndarray) -> Dict[str, np.ndarray]:
    if not isinstance(frame, pd.DataFrame):
        raise RefusedError(rule, "frame must be a pandas DataFrame, got %s" % type(frame).__name__)
    names = list(frame.columns)
    twice = sorted({str(c) for c in names if names.count(c) > 1})
    if twice:
        raise RefusedError(rule, "the frame holds these columns more than once: %s" % twice)
    out = {}
    for name, arr in arrays.items():
        a = as_int_array(arr, name.replace("_", " "), rule=rule)
        if len(a) != len(frame):
            raise RefusedError(rule, "%s has %d values for %d frame rows" % (name, len(a), len(frame)))
        out[name] = a
    return out


def _moved(values: np.ndarray, source: np.ndarray) -> np.ndarray:
    """values taken from the rows ``source`` points at; NaN (or None for objects) where it is -1.
    Integer and boolean values become float64, so a missing predecessor is NaN, never a number."""
    have = source >= 0
    if values.dtype.kind in "iub":
        values = values.astype(np.float64)
    if values.dtype.kind == "f":
        out = np.full(len(source), np.nan, dtype=values.dtype)
    else:
        out = np.full(len(source), None, dtype=object)
    out[have] = values[source[have]]
    return out


# Provenance: plan 2.1 R8 + 5 G-CALENDAR (lags only through the dense-grid predecessor lookup).
def apply_lags(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray,
               lags: Mapping[str, Any], target_cadence: Any) -> pd.DataFrame:
    """Move each column that lives at the target's own step back by its computed lag, through
    predecessor_index.

    Rule: R8, G-CALENDAR. Row i's value of column c becomes the value of the row of the same unit
    exactly lags[c].steps target steps earlier; no such row gives NaN (then R30), never a
    neighbour's value. A lag of 0 leaves the column as it is. Lagged integer and boolean columns
    become float64 (they can then hold the NaN). Same rows, same order, same index; the input frame
    is not changed.
    Closed world: EVERY column of the frame must have its Lag in ``lags``; a column that lives at
    the target's own step with no delay passes an explicit Lag of 0 steps. The keys arrive as
    unit_codes and steps, so the caller keeps key columns out of the frame; coarser columns stay
    out too (join_coarser_column lags them).
    Cadences are compared by what makes them the same step (steps.cadence_identity), not by their
    raw fields.
    Refuses: a frame column with no lag (a column with no lag in derived.json); a lag for a column
    the frame does not hold, or a Lag whose column is not its key (a lag not in derived.json); a
    lag that is negative or not an integer; a lag whose column cadence differs from the target's
    (it belongs to join_coarser_column); duplicate (unit, step); any predecessor read that is not
    in the same unit or not exactly L steps back.
    """
    keys = _check_rows(frame, "R8", unit_codes=unit_codes, steps=steps)
    units, s = keys["unit_codes"], keys["steps"]
    target = cadence_identity(cadence_view(target_cadence))
    no_lag = [str(c) for c in frame.columns if c not in lags]
    if no_lag:
        raise RefusedError("R8", "%d frame columns have no lag: %s" % (len(no_lag), no_lag[:20]),
                           fix="pass every column's Lag from derived.json (Lag of 0 steps for a "
                               "same-step column); keep key columns and coarser columns out of the "
                               "frame")
    absent = sorted(str(c) for c in lags if c not in frame.columns)
    if absent:
        raise RefusedError("R8", "lags name columns the frame does not hold: %s" % absent)
    wanted: Dict[str, int] = {}
    for column, lag in lags.items():
        try:
            lag_column, lag_steps, lag_cadence = lag.column, lag.steps, lag.column_cadence
        except AttributeError:
            raise RefusedError("R8", "the lag of %r is not a Lag (column, steps, column_cadence)" % column) from None
        if lag_column != column:
            raise RefusedError("R8", "the lag stored under %r is the lag of %r" % (column, lag_column))
        k = _int(lag_steps, "the lag of %r" % column, "R8")
        if k < 0:
            raise RefusedError("R8", "the lag of %r is negative (%d)" % (column, k))
        own = cadence_identity(cadence_view(lag_cadence))
        if own != target:
            raise RefusedError("R8", "column %r has cadence %s, not the target's %s; a coarser column is "
                               "lagged in join_coarser_column" % (column, own, target))
        wanted[column] = k
    out = frame.copy(deep=True)
    sources: Dict[int, np.ndarray] = {}
    for column, k in wanted.items():
        if k == 0:
            continue
        if k not in sources:
            src = predecessor_index(units, s, k)
            ok = src >= 0
            if not ((units[src[ok]] == units[ok]).all() and (s[ok] - s[src[ok]] == k).all()):
                raise RefusedError("G-CALENDAR", "internal: a lag-%d read left its unit or step" % k)
            sources[k] = src
        out[column] = pd.Series(_moved(frame[column].to_numpy(), sources[k]), index=frame.index,
                                name=column)
    return out


# Provenance: plan 1.4 (verdicts), 1.3 (roles), 5 G-CLOSED and G-KEYS; pm25_architecture.py:78
# (DROP_CONDITIONAL = True).
def apply_verdicts(columns: Tuple[str, ...], verdicts: Mapping[str, Any],
                   roles: Mapping[str, Any]) -> ColumnSets:
    """Decide where every non-key column goes: tree features, router context, report only, or out.

    Rule: plan 1.4, G-CLOSED, G-KEYS. keep, keep_unreviewed, watch and freeze enter; ban and
    conditional leave every engine run. An entering column goes by its role: driver and engineered
    to the trees; router_context to the router only; support, report_stratum and external_product
    to reports only. freeze columns are also listed in ``frozen``; keep_unreviewed and watch
    columns also in ``listed_in_reports``. Order: the order of ``columns``.
    Refuses: a column without a verdict, or a verdict for an absent column (closed world); a column
    without a role, or a key-role column among the non-key columns (keys never become features);
    the target or a target_twin with any verdict other than ban; an unknown verdict or role; a
    column named twice.
    """
    if isinstance(columns, str):
        raise RefusedError("G-CLOSED", "columns is a list of column names, not one string")
    cols = tuple(columns)
    twice = sorted({c for c in cols if cols.count(c) > 1})
    if twice:
        raise RefusedError("G-CLOSED", "columns named more than once: %s" % twice)
    no_verdict = [c for c in cols if c not in verdicts]
    stray = sorted(c for c in verdicts if c not in set(cols))
    if no_verdict or stray:
        raise RefusedError("G-CLOSED", "closed world: %d columns have no verdict %s; %d verdicts name "
                           "no column in the data %s" % (len(no_verdict), no_verdict[:20], len(stray), stray[:20]))
    no_role = [c for c in cols if c not in roles]
    if no_role:
        raise RefusedError("G-CLOSED", "columns without a role: %s" % no_role)
    tree: List[str] = []
    context: List[str] = []
    report: List[str] = []
    frozen: List[str] = []
    listed: List[str] = []
    for c in cols:
        try:
            verdict = _value(verdicts[c].verdict)
        except AttributeError:
            raise RefusedError("G-CLOSED", "the verdict of %r has no 'verdict' field" % c) from None
        role = _value(roles[c])
        if verdict not in ENTER + LEAVE:
            raise RefusedError("G-CLOSED", "column %r: unknown verdict %r" % (c, verdict))
        if role not in ROLES:
            raise RefusedError("G-CLOSED", "column %r: unknown role %r" % (c, role))
        if role in KEY_ROLES:
            raise RefusedError("G-KEYS", "column %r has the key role %r; keys are never features and "
                               "take no verdict" % (c, role))
        if role in TARGET_ROLES and verdict != "ban":
            raise RefusedError("G-CLOSED", "column %r is the %s; its verdict must be ban, not %r"
                               % (c, role, verdict), fix="the target and its twins are forced to ban")
        if verdict in LEAVE:
            continue
        if role in TREE_ROLES:
            tree.append(c)
        elif role in CONTEXT_ROLES:
            context.append(c)
        else:
            report.append(c)
        if verdict == "freeze":
            frozen.append(c)
        if verdict in LISTED:
            listed.append(c)
    return ColumnSets(tree_features=tuple(tree), router_context=tuple(context),
                      report_only=tuple(report), frozen=tuple(frozen),
                      listed_in_reports=tuple(listed))


def _epochs_of_rows(values: Any, column: str, n: int) -> Tuple[np.ndarray, np.ndarray]:
    """(epoch per row as int64, has-an-epoch flag). Integers, or floats with NaN for no content."""
    arr = np.asarray(values)
    if arr.ndim != 1 or len(arr) != n:
        raise RefusedError("R9", "the content epochs of %r must be one value per frame row (%d), got "
                           "shape %s" % (column, n, arr.shape))
    if arr.dtype.kind == "f":
        has = np.isfinite(arr)
        if not (arr[has] == np.floor(arr[has])).all():
            raise RefusedError("R9", "the content epochs of %r are not whole days" % column)
        out = np.zeros(n, dtype=np.int64)
        out[has] = arr[has].astype(np.int64)
        return out, has
    return as_int_array(arr, "the content epochs of %r" % column, rule="R9"), np.ones(n, dtype=bool)


# Provenance: plan 2.1 R9; defo_ban.py:14-15, 76 ("usable only as ONE pre-window epoch").
def apply_freezes(frame: pd.DataFrame, unit_codes: np.ndarray, content_epoch_of_row: Mapping[str, Any],
                  epochs: Mapping[str, Any]) -> pd.DataFrame:
    """Hold each 'freeze' column at its computed epoch.

    Rule: R9, D32, D33. For a frozen column, EVERY row of a unit takes that unit's value at the
    epoch R9 computed for the cut in use (D32): the value on its rows whose content epoch equals
    the epoch. A unit with no (non-missing) value at the epoch gets NaN on every row (D33; R30 counts
    it). The epoch differs per lead and cut kind, so this runs per cut. Frozen numeric columns come
    back as float64. Same rows, order and index; the input frame is not changed.
    Refuses: an epoch for a column the frame does not hold; content epochs and epochs that name
    different columns; content epochs that are not one whole day per row; a unit whose rows at the
    epoch hold more than one distinct value (the epoch value is ambiguous).
    """
    keys = _check_rows(frame, "R9", unit_codes=unit_codes)
    units = keys["unit_codes"]
    if set(content_epoch_of_row) != set(epochs):
        raise RefusedError("R9", "content epochs name %s but epochs name %s"
                           % (sorted(content_epoch_of_row), sorted(epochs)))
    absent = sorted(c for c in epochs if c not in frame.columns)
    if absent:
        raise RefusedError("R9", "epochs name columns the frame does not hold: %s" % absent)
    out = frame.copy(deep=True)
    n = len(frame)
    for column in epochs:
        epoch = _int(epochs[column], "the epoch of %r" % column, "R9")
        row_epoch, has = _epochs_of_rows(content_epoch_of_row[column], column, n)
        at = has & (row_epoch == epoch)
        values = frame[column]
        if pd.api.types.is_numeric_dtype(values) and not pd.api.types.is_bool_dtype(values):
            values = values.astype(np.float64)
        at_epoch = pd.DataFrame({"unit": units[at], "value": values.to_numpy()[at]}).dropna(subset=["value"])
        distinct = at_epoch.groupby("unit", sort=True)["value"].nunique()
        ambiguous = distinct[distinct > 1]
        if len(ambiguous):
            raise RefusedError("R9", "column %r: %d units hold more than one value at the epoch %d, e.g. "
                               "unit codes %s" % (column, len(ambiguous), epoch,
                                                   ambiguous.index[:_SHOW].tolist()))
        value_of = at_epoch.groupby("unit", sort=True)["value"].first()
        held = pd.Series(units).map(value_of)
        if values.dtype.kind == "f":
            held = held.astype(np.float64)
        out[column] = pd.Series(held.to_numpy(), index=frame.index, name=column)
    return out


# ---------------------------------------------------------------------------------------------------
# R17 own-history block
def history_column_names(spec: Any) -> Tuple[str, ...]:
    """Every history column the spec's fields describe, before duplicates are dropped, in block
    order: the last values (newest first), the trailing means (in spec order), the all-history mean.
    derive_r17 names its columns with these names; history_block refuses any other name."""
    last = _int(spec.last_values, "spec.last_values", "R17")
    if last < 0:
        raise RefusedError("R17", "spec.last_values is negative (%d)" % last)
    names = [HISTORY_LAST % j for j in range(1, last + 1)]
    for w in spec.trailing_steps:
        w = _int(w, "a trailing window of the spec", "R17")
        if w < 1:
            raise RefusedError("R17", "a trailing window must be at least 1 step, got %d" % w)
        names.append(HISTORY_MEAN % w)
    if spec.all_history_mean:
        names.append(HISTORY_MEAN_ALL)
    if len(set(names)) != len(names):
        raise RefusedError("R17", "the spec names a history column twice: %s" % names)
    return tuple(names)


def _latest_label_step(target_steps: np.ndarray, lead_steps: int) -> np.ndarray:
    """The newest label a row predicting step t may read at lead L (plan 2.1 R11, R17), computed by
    timing.latest_label_step itself, once per distinct target step, so the history block follows
    the timing rule whatever it becomes (t - L for L >= 1, t - 1 for a nowcast today). The R17
    start offset is subtracted by the caller, as the timing helper's contract says."""
    steps = np.asarray(target_steps, dtype=np.int64)
    if steps.size == 0:
        return steps.copy()
    distinct, inverse = np.unique(steps, return_inverse=True)
    newest = np.fromiter((latest_label_step(int(s), lead_steps) for s in distinct.tolist()),
                         dtype=np.int64, count=len(distinct))
    return newest[np.asarray(inverse).reshape(-1)]



# ---------------------------------------------------------------------------------------------------
# The leak-free fallback of the history block (owner ruling F1)
@dataclass(frozen=True)
class _Histories:
    """The normal-fill histories (UnitHistory at the cut) of the units a block reads, concatenated:
    one entry per label, with the grid row of its unit."""
    unit_rows: np.ndarray
    times: np.ndarray
    season_keys: np.ndarray
    y: np.ndarray


def _read_histories(grid: DenseGrid, normal_fill: Mapping[str, Any], unit_rows: List[int],
                    first: int, last: int) -> _Histories:
    """Read and check each unit's UnitHistory (unit_id, times, season_keys, y, cut).

    Refuses: a history stored under another unit's id; a history without those fields; fields of
    different lengths; a non-finite label (a UnitHistory holds valid labels only); a label dated
    after the history's own cut (G-FITCUT: 'within the cut'); a label time off the grid; a time
    named twice."""
    rows_out, times_out, keys_out, y_out = [], [], [], []
    for r in unit_rows:
        unit_id = grid.unit_ids[r]
        history = normal_fill[unit_id]
        hid = getattr(history, "unit_id", unit_id)
        if hid != unit_id:
            raise RefusedError("G-DONOR", "the normal-fill history stored under %r belongs to unit %r"
                               % (unit_id, hid))
        try:
            times, keys, labels, cut = history.times, history.season_keys, history.y, history.cut
        except AttributeError:
            raise RefusedError("G-DONOR", "the normal-fill history of %r is not a UnitHistory (times, "
                               "season_keys, y, cut)" % unit_id) from None
        t = as_int_array(times, "the history times of %r" % unit_id, rule="G-DONOR")
        k = as_int_array(keys, "the history season keys of %r" % unit_id, rule="G-DONOR")
        y = np.asarray(labels, dtype=np.float64)
        if y.ndim != 1 or len(t) != len(y) or len(k) != len(y):
            raise RefusedError("G-DONOR", "the unit history of %r has %d times, %d season keys and "
                               "labels of shape %s; they must be one per label"
                               % (unit_id, len(t), len(k), y.shape))
        if y.size and not np.isfinite(y).all():
            raise RefusedError("G-DONOR", "the unit history of %r holds non-finite labels; it holds valid "
                               "labels only" % unit_id)
        c = _int(cut, "the cut of the unit history of %r" % unit_id, "G-FITCUT")
        after = t > c
        if after.any():
            raise RefusedError("G-FITCUT", "the unit history of %r holds %d labels after its cut %d, e.g. "
                               "steps %s" % (unit_id, int(after.sum()), c, t[after][:_SHOW].tolist()))
        off = (t < first) | (t > last)
        if off.any():
            raise RefusedError("G-DONOR", "the unit history of %r holds %d label times off the grid "
                               "[%d, %d], e.g. %s" % (unit_id, int(off.sum()), first, last,
                                                      t[off][:_SHOW].tolist()))
        if len(np.unique(t)) != len(t):
            raise RefusedError("G-DONOR", "the unit history of %r names a label time twice" % unit_id)
        rows_out.append(np.full(len(t), r, dtype=np.int64))
        times_out.append(t)
        keys_out.append(k)
        y_out.append(y)
    if not rows_out:
        empty = np.zeros(0, dtype=np.int64)
        return _Histories(empty, empty, empty, np.zeros(0))
    return _Histories(np.concatenate(rows_out), np.concatenate(times_out), np.concatenate(keys_out),
                      np.concatenate(y_out))


def _pair_codes(a_hist: np.ndarray, b_hist: np.ndarray, a_query: np.ndarray,
                b_query: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Integer codes of (a, b) pairs: one code per distinct pair of the history; a query pair that
    the history does not hold gets -1. a >= 0 (grid rows); b any integers."""
    if len(a_hist) == 0:
        return np.zeros(0, dtype=np.int64), np.full(len(a_query), -1, dtype=np.int64)
    b_all = np.concatenate([b_hist, b_query])
    lo = int(b_all.min())
    span = int(b_all.max()) - lo + 1
    top = int(max(a_hist.max(), a_query.max() if len(a_query) else 0)) + 1
    if top * span >= 2 ** 62:
        raise RefusedError("R17", "the (unit, season key) key space is too large for one int64 key")
    comb_hist = a_hist * span + (b_hist - lo)
    comb_query = a_query * span + (b_query - lo)
    uniq, codes_hist = np.unique(comb_hist, return_inverse=True)
    pos = np.minimum(np.searchsorted(uniq, comb_query), len(uniq) - 1)
    codes_query = np.where(uniq[pos] == comb_query, pos, -1).astype(np.int64)
    return codes_hist.astype(np.int64), codes_query


def _asof_mean(group_q: np.ndarray, newest_q: np.ndarray, group_h: np.ndarray, time_h: np.ndarray,
               y_h: np.ndarray) -> np.ndarray:
    """For each query: the mean of the history labels of its group dated AT OR BEFORE its newest
    readable step (never later); NaN when there is none or the group is -1."""
    out = np.full(len(group_q), np.nan)
    if len(y_h) == 0 or len(group_q) == 0:
        return out
    lo = int(min(time_h.min(), newest_q.min()))
    span = int(max(time_h.max(), newest_q.max())) - lo + 1
    top = int(max(group_h.max(), group_q.max())) + 1
    if top * span >= 2 ** 62:
        raise RefusedError("R17", "the (group, step) key space is too large for one int64 key")
    key = group_h * span + (time_h - lo)
    order = np.argsort(key, kind="stable")
    ks = key[order]
    # running sums restart in every group, so a sum never carries another group's labels
    running = pd.Series(y_h[order]).groupby(group_h[order], sort=False).cumsum().to_numpy()
    ok = np.flatnonzero(group_q >= 0)
    g = group_q[ok]
    start = np.searchsorted(ks, g * span, side="left")
    end = np.searchsorted(ks, g * span + (newest_q[ok] - lo), side="right")
    count = end - start
    have = count > 0
    total = running[end[have] - 1]
    out[ok[have]] = total / count[have]
    return out


def _check_season_keys(hist: _Histories, rows: np.ndarray, t: np.ndarray, season_keys: np.ndarray,
                       first: int, n_steps: int) -> None:
    """Where a target row's own step is among its unit's history times, its season key must be the
    key the history holds for that step: both come from R2, so a disagreement is a convention
    mismatch, which would otherwise send every row to the all-season mean without a word."""
    if len(hist.y) == 0 or len(rows) == 0:
        return
    key_hist = hist.unit_rows * n_steps + (hist.times - first)
    order = np.argsort(key_hist, kind="stable")
    ks = key_hist[order]
    key_rows = rows * n_steps + (t - first)
    pos = np.minimum(np.searchsorted(ks, key_rows), len(ks) - 1)
    found = ks[pos] == key_rows
    held = hist.season_keys[order][pos]
    bad = found & (held != season_keys)
    if bad.any():
        i = np.flatnonzero(bad)[:_SHOW]
        raise RefusedError("R2", "%d target rows carry a season key that differs from the key their "
                           "unit history holds for the same step, e.g. (step, row key, history key) %s"
                           % (int(bad.sum()), list(zip(t[i].tolist(), season_keys[i].tolist(),
                                                       held[i].tolist()))),
                           fix="compute the rows' season keys with the R2 rule that fills "
                               "UnitHistory.season_keys")


def _donor_mean(value: Any) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise RefusedError("G-DONOR", "donor_mean must be a number (the donor-row mean at the cut), got %r"
                           % (value,))
    value = float(value)
    if not np.isfinite(value):
        raise RefusedError("G-DONOR", "donor_mean is not finite (%r); it is the last fallback" % value,
                           fix="pass the donor-row mean of y at the cut (identity link)")
    return value


# Provenance: plan 2.3 R17; pm25_forecast.py:122-159 (history_block: dense grid, rmean over
# available months only, missing lag -> own 12-month mean, never 0); Q4 a, Q12; owner ruling F1
# (the leak-free fallback) and R15's chain (pm25_adaptation.py:584-604: unit-season mean, unit mean,
# donor mean), read as of each row.
def history_block(grid: DenseGrid, spec: Any, target_steps: np.ndarray, unit_rows: np.ndarray,
                  lead_steps: int, labels: Any, normal_fill: Mapping[str, Any],
                  season_keys: np.ndarray, donor_mean: float) -> Tuple[np.ndarray, Mapping[str, float]]:
    """The engine's own-history block for each target row, ending at the issue step.

    Rule: R17, G-HIST, G-CALENDAR, G-LOCK (D83, D84, D54 a, R-D b, owner ruling F1).
    For a row predicting step t at lead L the newest readable label is timing.latest_label_step(t,
    L) (t - L; t - 1 at lead 0), moved back by spec.start_offset_steps. Columns, as spec.columns lists them (names from
    history_column_names): hist_last_j = the label j - 1 steps before the newest readable;
    hist_mean_w = the mean of the AVAILABLE labels among the w steps ending at the newest readable
    (D83, no minimum count); hist_mean_all = the mean of the available labels from the grid's first
    step up to the newest readable (D84). Every label of these columns comes from labels.asof_rows,
    the only label source; a read before the grid's first step is absent.
    The fill chain of a missing value (plan R17, with the normal made leak-free by F1):
      1. the row's own trailing means, shortest window first (1 year, then 5 years, whatever order
         the spec lists them in);
      2. the unit's AS-OF season mean: the mean of the unit's labels in normal_fill (its
         UnitHistory at the cut, so within the cut) dated at or before the row's newest readable
         step and carrying the row's season key;
      3. the unit's as-of all-season mean: the same labels, every season key;
      4. donor_mean, the donor-row mean at the cut.
    Never 0, and never a label at or after the row: steps 2 and 3 read only labels at or before
    the newest readable step (which is before t; at a lead it is the issue step, so a label between
    the issue step and t is not read either) and at or before the history's cut. A test row
    (t after the cut) reads test-window labels up to its issue step in its own columns (D54 a),
    but its fallback reads labels within the cut only.
    ``season_keys`` is the R2 season key of each target row's step t, in the convention of
    UnitHistory.season_keys (checked wherever the row's step is among its unit's history times).
    The season is the row's, as for R15's normal (which the fallback replaces).
    READING (owner confirmation asked, no code change until ruled): (1) step 1 keeps plan R17's
    trailing means in front of F1's chain, reading F1 as a replacement of the leaky normal only;
    the literal F1 text would start at step 2. (2) The season of step 2 is the season of the
    target row's step t, not the season of the missing lag's own step.
    G-HIST: the block asks the vault only for (the row's own unit, the row's newest readable step,
    k_back >= 0), so it never REQUESTS a later label. That each label SERVED is dated at or before
    that step is the LabelView.asof_rows contract and is enforced inside the vault: asof_rows
    returns labels without their steps, so a vault that broke its contract could not be caught
    here (the vault-side test belongs with the vault).
    SIGNATURE (owner sign-off asked): season_keys and donor_mean are added to the approved
    signature, because ruling F1 needs a season key per row and the donor-row mean at the cut and
    the approved inputs carry neither.
    Returns (float32 matrix rows x spec.columns, {column: share of rows filled}); a share is NaN
    when there are no rows. The shares are also PRINTED, one line per call (the approved contract:
    "returned and printed"; plan R17: "The filled share is printed"), so heavy fallback use is
    never silent.
    Refuses: lead_steps < 0; a negative start offset; a column name the spec's fields do not
    describe, or one also listed as a dropped duplicate; a target step outside the grid or a unit
    row that is not on it; season keys that are not one integer per row, or that disagree with the
    unit history; a donor_mean that is not a finite number; a unit with no entry in normal_fill, or
    a history that is not a valid UnitHistory within its cut and on the grid (see _read_histories);
    (internal) a newest readable step that is not before its target step; a non-finite value left
    after the fill chain; a label source that returns values of the wrong shape or an infinite value.
    """
    lead = _int(lead_steps, "lead_steps", "R17")
    if lead < 0:
        raise RefusedError("R17", "lead_steps is negative (%d)" % lead)
    offset = _int(spec.start_offset_steps, "spec.start_offset_steps", "R17")
    if offset < 0:
        raise RefusedError("R17", "spec.start_offset_steps is negative (%d)" % offset)
    t = as_int_array(target_steps, "target steps", rule="R17")
    rows = as_int_array(unit_rows, "unit rows", rule="R17")
    if len(t) != len(rows):
        raise RefusedError("R17", "target steps (%d) and unit rows (%d) differ in length" % (len(t), len(rows)))
    keys = as_int_array(season_keys, "season keys", rule="R17")
    if len(keys) != len(t):
        raise RefusedError("R17", "season keys (%d) and target steps (%d) differ in length" % (len(keys), len(t)))
    donor = _donor_mean(donor_mean)
    n_units = len(grid.unit_ids)
    first = int(grid.first_step)
    n_steps = int(grid.n_steps)
    last = first + n_steps - 1
    off_grid = (rows < 0) | (rows >= n_units)
    if off_grid.any():
        raise RefusedError("R17", "%d unit rows are not on the grid (0..%d)" % (int(off_grid.sum()), n_units - 1))
    outside = (t < first) | (t > last)
    if outside.any():
        raise RefusedError("R17", "%d target steps lie outside the grid [%d, %d]" % (int(outside.sum()), first, last))

    known = history_column_names(spec)
    columns = tuple(spec.columns)
    dropped = set(spec.dropped_duplicates)
    unknown = [c for c in columns if c not in known]
    if unknown:
        raise RefusedError("R17", "spec.columns names %s, which its fields do not describe (known: %s)"
                           % (unknown, list(known)))
    both = sorted(set(columns) & dropped)
    if both:
        raise RefusedError("R17", "columns %s are listed and also dropped as duplicates" % both)
    if len(set(columns)) != len(columns):
        raise RefusedError("R17", "spec.columns names a column twice: %s" % list(columns))

    n = len(t)
    unit_list = sorted(set(rows.tolist()))
    no_fill = [grid.unit_ids[r] for r in unit_list if grid.unit_ids[r] not in normal_fill]
    if no_fill:
        raise RefusedError("G-DONOR", "normal_fill has no unit history for %d units, e.g. %s"
                           % (len(no_fill), no_fill[:_SHOW]))
    hist = _read_histories(grid, normal_fill, unit_list, first, last)
    _check_season_keys(hist, rows, t, keys, first, n_steps)

    newest = _latest_label_step(t, lead) - offset
    if (newest >= t).any():
        raise RefusedError("G-HIST", "internal: a newest readable step is not before its target step")

    last_values = _int(spec.last_values, "spec.last_values", "R17")
    windows = [int(w) for w in spec.trailing_steps]
    need_all = bool(spec.all_history_mean)
    depth = max([last_values] + windows + [0])
    if need_all:
        depth = max(depth, int((newest - first).max()) + 1 if n else 0)
    last_vals = np.full((n, last_values), np.nan)
    sums = np.zeros((n, len(windows)))
    counts = np.zeros((n, len(windows)), dtype=np.int64)
    all_sum = np.zeros(n)
    all_count = np.zeros(n, dtype=np.int64)
    for k in range(depth):
        read_step = newest - k
        sel = np.flatnonzero(read_step >= first)
        if len(sel) == 0:
            break
        got = np.asarray(labels.asof_rows(rows[sel], newest[sel], k), dtype=np.float64)
        if got.shape != (len(sel),):
            raise RefusedError("G-LOCK", "the label vault returned shape %s for %d requests"
                               % (got.shape, len(sel)))
        if np.isinf(got).any():
            raise RefusedError("G-LOCK", "the label vault returned an infinite label")
        # No served-step check here: asof_rows does not return the steps it read (G-HIST is the
        # vault's contract; see the docstring).
        fin = np.isfinite(got)
        if k < last_values:
            last_vals[sel, k] = got
        for j, w in enumerate(windows):
            if k < w:
                sums[sel[fin], j] += got[fin]
                counts[sel[fin], j] += 1
        if need_all:
            all_sum[sel[fin]] += got[fin]
            all_count[sel[fin]] += 1

    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
        all_mean = np.where(all_count > 0, all_sum / np.maximum(all_count, 1), np.nan)

    raw: Dict[str, np.ndarray] = {}
    for j in range(last_values):
        raw[HISTORY_LAST % (j + 1)] = last_vals[:, j]
    for j, w in enumerate(windows):
        raw[HISTORY_MEAN % w] = means[:, j]
    if need_all:
        raw[HISTORY_MEAN_ALL] = all_mean
    # step 1 of the chain: trailing means, shortest window first (the windows are distinct:
    # history_column_names refuses a repeat)
    trailing = [means[:, j] for j in np.argsort(windows, kind="stable").tolist()]

    values: Dict[str, np.ndarray] = {}
    filled: Dict[str, float] = {}
    gaps = np.zeros(n, dtype=bool)
    for column in columns:
        value = raw[column].copy()
        filled[column] = float((~np.isfinite(value)).mean()) if n else float("nan")
        for source in trailing:
            still = ~np.isfinite(value)
            if not still.any():
                break
            value[still] = source[still]
        values[column] = value
        gaps |= ~np.isfinite(value)

    # steps 2-4, only for the rows that still have a gap: as-of season mean, as-of all-season mean,
    # donor-row mean
    need = np.flatnonzero(gaps)
    if len(need):
        q_rows, q_newest = rows[need], newest[need]
        season_hist, season_query = _pair_codes(hist.unit_rows, hist.season_keys, q_rows, keys[need])
        normal = _asof_mean(season_query, q_newest, season_hist, hist.times, hist.y)
        unit_mean = _asof_mean(q_rows, q_newest, hist.unit_rows, hist.times, hist.y)
        normal = np.where(np.isfinite(normal), normal, unit_mean)
        normal = np.where(np.isfinite(normal), normal, donor)
        fallback = np.full(n, np.nan)
        fallback[need] = normal
        for column in columns:
            value = values[column]
            still = ~np.isfinite(value)
            value[still] = fallback[still]

    block = np.empty((n, len(columns)), dtype=np.float64)
    for i, column in enumerate(columns):
        value = values[column]
        left = ~np.isfinite(value)
        if left.any():
            shown = sorted({grid.unit_ids[r] for r in rows[left].tolist()})[:_SHOW]
            raise RefusedError("R17", "internal: column %s has %d rows still missing after the fill chain, "
                               "e.g. units %s" % (column, int(left.sum()), shown))
        block[:, i] = value
    print(_filled_line(lead, n, columns, filled))
    return block.astype(np.float32), filled


def _filled_line(lead: int, n_rows: int, columns: Tuple[str, ...], filled: Mapping[str, float]) -> str:
    """The line history_block prints (plan R17: 'The filled share is printed')."""
    shares = ", ".join("%s %.4f" % (c, filled[c]) for c in columns) if columns else "no history columns"
    return "history block, lead %d, %d rows: filled share per column: %s" % (lead, n_rows, shares)


# Provenance: plan 2.3 R17 (events with repeat visits); 9.1 item 2e. M8 under the fast track.
def event_history_block(unit_ids: np.ndarray, issue_days: np.ndarray, event_start_days: np.ndarray,
                        lead_days: int, labels: Any,
                        normal_fill: Mapping[str, Any]) -> Tuple[np.ndarray, Mapping[str, float]]:
    """Own-history block for events with repeat visits (R17, events). Not built: milestone M8 (the
    event rules, fast track)."""
    raise NotImplementedError("event_history_block is built at milestone M8 (the event rules)")


# ---------------------------------------------------------------------------------------------------
# Provenance: pm25_forecast.py:265-305 (at lead L the whole feature row moves back to the issue step).
def features_at_issue_step(features: np.ndarray, unit_codes: np.ndarray, steps: np.ndarray,
                           lead_steps: int) -> np.ndarray:
    """At lead L, give each target row the feature row of its issue step t - L (same unit).

    Rule: R8, R11, G-CALENDAR. Row i of the result is the feature row of the row of the same unit
    exactly L steps before row i's step, found through predecessor_index (never the adjacent row);
    no such row gives a row of NaN, never a shifted neighbour. Columns keep their R8 lags relative
    to that step (apply_lags ran before). Lead 0 returns a copy of the input, values and dtype
    unchanged. At L >= 1 a float matrix keeps its dtype; an integer or boolean matrix becomes
    float64 (it can then hold the NaN). The input is not changed; rows keep their order.
    Refuses: lead_steps < 0 or not an integer; features that are not a 2-D numeric array; unit codes
    or steps that are not one integer per feature row; duplicate (unit, step), at every lead;
    (internal) any read outside the unit or not exactly L steps back.
    """
    lead = _int(lead_steps, "lead_steps", "R8")
    if lead < 0:
        raise RefusedError("R8", "lead_steps is negative (%d)" % lead)
    X = np.asarray(features)
    if X.ndim != 2:
        raise RefusedError("R8", "features must be a 2-D matrix (rows x columns), got shape %s" % (X.shape,))
    if X.dtype.kind not in "fiub":
        raise RefusedError("R8", "features must be numeric, got dtype %s" % X.dtype)
    units = as_int_array(unit_codes, "unit codes", rule="G-CALENDAR")
    s = as_int_array(steps, "steps", rule="G-CALENDAR")
    if not (len(units) == len(s) == X.shape[0]):
        raise RefusedError("G-CALENDAR", "unit codes (%d), steps (%d) and feature rows (%d) differ in length"
                           % (len(units), len(s), X.shape[0]))
    repeated = pd.DataFrame({"u": units, "s": s}).duplicated(keep=False).to_numpy()
    if repeated.any():
        i = np.flatnonzero(repeated)[:_SHOW]
        raise RefusedError("G-CALENDAR", "%d rows repeat a (unit, step), e.g. %s"
                           % (int(repeated.sum()), list(zip(units[i].tolist(), s[i].tolist()))))
    if lead == 0:
        return X.copy()
    src = predecessor_index(units, s, lead)
    ok = src >= 0
    if not ((units[src[ok]] == units[ok]).all() and (s[ok] - s[src[ok]] == lead).all()):
        raise RefusedError("G-CALENDAR", "internal: a lead-%d read left its unit or step" % lead)
    dtype = X.dtype if X.dtype.kind == "f" else np.float64
    out = np.full(X.shape, np.nan, dtype=dtype)
    out[ok] = X[src[ok]]
    return out
