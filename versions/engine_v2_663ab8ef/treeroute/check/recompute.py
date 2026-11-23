"""Recompute one engineered column from its DECLARATION: the reference G-DERIVED compares the feature script
against (plan 1.5, 5 G-DERIVED, G-LOCK).

SCIENCE body for the owner-approved signature io_science.recompute_declared_operation (owner ruling A; D89,
D90 proposed defaults accepted). It lives in treeroute/check/ because io/ is outside the check build's write
scope; the owner may move it into io/ unchanged.

Every look-back goes through the keys-only dense grid: a grid position is (unit row r, step first_step + j)
= r x n_steps + j, and a read k steps back is the predecessor lookup io.steps.predecessor_index on the
grid's own keys (G-CALENDAR), never a row shift. A missing predecessor gives NaN. Trailing only: a driver-
derived value ends at its own row. Target-derived operations would read the label vault through
LabelView.asof_rows with the row's step - 1 as its newest readable step; no package declares one today,
so they are refused as 'not built' (fail loudly) rather than guessed.

The operations, as declared in a store column's 'operation' text (the feature scripts' spellings):
  (none), one source                    a copy of the source (router context built from a key or static column)
  lag k=<k> unit=<u>                    the source k units earlier (k turned into the column's own steps)
  hold_last_observed through_year=<y> unit=year
                                        the source on rows of a year up to y; on a later row the same unit's
                                        value in year y at the same position in the year
  trailing_mean w=<w> unit=<u> min_count=<m>
                                        the mean of the finite source values over the w steps ending at the
                                        row; NaN when fewer than m are finite (also trailing_sum, _min, _max)
  cumulative stat=sum reset_month=<m> unit=month
                                        the sum of the finite values since the latest step whose calendar
                                        month is m (or the record's first step); NaN at a missing step
  cumulative stat=ewm_mean alpha=<a> adjust=false unit=month
                                        pandas' ewm(alpha=a, adjust=False, ignore_na=False).mean() along the
                                        unit's steps from its first step (an independent implementation)
  years_since event='<col> <op> <t>' unit=<u> no_event=nan
                                        steps since the latest step whose source meets the event test (0 at
                                        an event step); NaN before the first event. READING (owner to confirm):
                                        a missing step makes the count unknown until the next event, since
                                        nobody can tell whether an event happened in it
  calendar_harmonic <sin|cos> order=<n> angle=<a>*pi*(month-<b>)/<c>
                                        fn(n x a x pi x (month - b) / c) of the row's calendar month
Anything else is refused (RecomputeRefusal): an undeclared or unrecomputable engineered column.
"""
# Provenance: plan 1.5 (the operation list: lag k; trailing mean, sum, min or max over w; cumulative; years
# since; neighbour aggregate; aggregate_time; aggregate_space), 5 G-DERIVED, G-LOCK; the operation spellings
# of the packages' feature scripts (OUTPUTS facts); owner ruling A (D89, D90).

import datetime as _dt
import math
import re
import warnings
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.io.steps import predecessor_index, step_bounds

KEY_TIME_ROLE = "key_time"
_LAG = re.compile(r"lag k=([0-9]+) unit=([a-z_]+)")
_HOLD = re.compile(r"hold_last_observed through_year=([0-9]+) unit=year")
_TRAILING = re.compile(r"trailing_(mean|sum|min|max) w=([0-9]+) unit=([a-z_]+)(?: min_count=([0-9]+))?")
_CUM_SUM = re.compile(r"cumulative stat=sum reset_month=([0-9]+) unit=month")
_EWM = re.compile(r"cumulative stat=ewm_mean alpha=([0-9.eE+-]+) adjust=false unit=month")
_SINCE = re.compile(r"years_since event='([^' ]+) (>=|>|<=|<|==) ([-0-9.eE+]+)' unit=([a-z_]+) no_event=nan")
_HARMONIC = re.compile(r"calendar_harmonic (sin|cos) order=([0-9]+) angle=([0-9.]+)\*pi\*\(month-([0-9.]+)\)/([0-9.]+)")
_OPS = {">=": np.greater_equal, ">": np.greater, "<=": np.less_equal, "<": np.less, "==": np.equal}


class RecomputeRefusal(RefusedError):
    """An operation the recompute cannot rebuild from its declaration (G-DERIVED refuses the column)."""

    def __init__(self, message: str) -> None:
        super().__init__("G-DERIVED", message, fix="declare the column with an operation of plan 1.5")


def _v(x: Any) -> Any:
    return getattr(x, "value", x)


class _Grid(object):
    """Keys of a DenseGrid: unit row and step of every position, the predecessor lookup, and calendar parts."""

    def __init__(self, grid: Any, cadence: Any) -> None:
        self.n = int(grid.n_steps)
        self.first = int(grid.first_step)
        self.units = len(grid.unit_ids)
        size = self.units * self.n
        self.unit_row = np.repeat(np.arange(self.units, dtype=np.int64), self.n)
        self.step = np.tile(np.arange(self.first, self.first + self.n, dtype=np.int64), self.units)
        self.size = size
        self.cadence = cadence
        self._pred: Dict[int, np.ndarray] = {}
        self._year: Optional[np.ndarray] = None
        self._month: Optional[np.ndarray] = None

    def back(self, values: np.ndarray, k: int) -> np.ndarray:
        """values (one per position) read k steps back in the same unit (NaN where absent)."""
        if k == 0:
            return np.asarray(values, dtype=np.float64)
        if k not in self._pred:
            self._pred[k] = predecessor_index(self.unit_row, self.step, int(k))
        src = self._pred[k]
        out = np.full(self.size, np.nan)
        ok = src >= 0
        out[ok] = np.asarray(values, dtype=np.float64)[src[ok]]
        return out

    def _calendar(self) -> None:
        if self.cadence is None:
            raise RecomputeRefusal("the recompute needs the target cadence to read calendar years and months")
        steps = np.arange(self.first, self.first + self.n, dtype=np.int64)
        first, _ = step_bounds(steps, self.cadence)
        dates = [_dt.date.fromordinal(int(d)) for d in first.tolist()]
        self._year = np.tile(np.array([d.year for d in dates], dtype=np.int64), self.units)
        self._month = np.tile(np.array([d.month for d in dates], dtype=np.int64), self.units)

    @property
    def year(self) -> np.ndarray:
        if self._year is None:
            self._calendar()
        return self._year

    @property
    def month(self) -> np.ndarray:
        if self._month is None:
            self._calendar()
        return self._month

    def steps_per_year(self) -> int:
        kind = _v(getattr(self.cadence, "kind", None))
        unit = _v(getattr(self.cadence, "unit", None))
        length = int(getattr(self.cadence, "length", 1) or 1)
        if kind == "regular" and length == 1 and unit == "month":
            return int(K.MONTHS_PER_YEAR)
        if kind == "regular" and length == 1 and unit == "year":
            return 1
        raise RecomputeRefusal("a year-based operation on a %s step of %s %s is not built" % (kind, length, unit))


def _steps_of(k: int, unit: str, cadence: Any, what: str) -> int:
    """k units as a whole number of the GRID's steps (the target step)."""
    kind = _v(getattr(cadence, "kind", None))
    own = _v(getattr(cadence, "unit", None))
    length = int(getattr(cadence, "length", 1) or 1)
    if kind != "regular":
        raise RecomputeRefusal("%s: a %s target step is not built for this operation" % (what, kind))
    if unit == own:
        months = k
        per = length
    elif (unit, own) == ("year", "month"):
        months = k * int(K.MONTHS_PER_YEAR)
        per = length
    elif (unit, own) == ("month", "year"):
        months = k
        per = length * int(K.MONTHS_PER_YEAR)
    else:
        raise RecomputeRefusal("%s: a look-back in %s on a %s step cannot be counted" % (what, unit, own))
    if months % per:
        raise RecomputeRefusal("%s: %d %s is not a whole number of the grid's steps" % (what, k, unit))
    return months // per


def _source(sources: pd.DataFrame, name: str, size: int, what: str) -> np.ndarray:
    if name not in sources.columns:
        raise RecomputeRefusal("%s: its source %r is not available to the recompute" % (what, name))
    v = np.asarray(pd.to_numeric(sources[name], errors="coerce"), dtype=np.float64)
    if v.shape != (size,):
        raise RecomputeRefusal("%s: the source %r holds %d values for %d grid positions" % (what, name, v.size, size))
    return v


def _cum_sum(v: np.ndarray, g: _Grid, reset_month: int) -> np.ndarray:
    m = v.reshape(g.units, g.n)
    months = g.month.reshape(g.units, g.n)[0]
    out = np.full_like(m, np.nan)
    state = np.zeros(g.units)
    for j in range(g.n):
        if j == 0 or months[j] == reset_month:
            state = np.zeros(g.units)
        col = m[:, j]
        ok = np.isfinite(col)
        state = state + np.where(ok, col, 0.0)
        out[ok, j] = state[ok]
    return out.reshape(-1)


def _ewm(v: np.ndarray, g: _Grid, alpha: float) -> np.ndarray:
    m = pd.DataFrame(v.reshape(g.units, g.n).T)
    return m.ewm(alpha=alpha, adjust=False, ignore_na=False).mean().to_numpy().T.reshape(-1)


def _since(v: np.ndarray, g: _Grid, op: Any, threshold: float) -> np.ndarray:
    m = v.reshape(g.units, g.n)
    out = np.full_like(m, np.nan)
    count = np.full(g.units, np.nan)
    for j in range(g.n):
        col = m[:, j]
        obs = np.isfinite(col)
        with np.errstate(invalid="ignore"):
            event = obs & op(col, threshold)
        count = np.where(event, 0.0, np.where(obs, count + 1.0, np.nan))
        out[:, j] = count
    return out.reshape(-1)


# Provenance: plan 1.5, 5 G-DERIVED, G-LOCK (the approved io_science signature; D89, D90 accepted).
def recompute_declared_operation(decl: Any, sources: pd.DataFrame, grid: Any, labels: Any, rows: np.ndarray,
                                 adjacency: Optional[pd.DataFrame], target_cadence: Any = None) -> np.ndarray:
    """Recompute one engineered column on given grid positions from its declaration.

    Rule: plan 1.5, G-DERIVED, G-LOCK. decl: the column's facts (name, operation, derived_from, reads_target,
    cadence); sources: the source columns, one row per grid position (masked; driver and key columns only,
    never the target); grid: the keys-only DenseGrid; labels: the label vault (target-derived operations);
    rows: the positions to return; adjacency: unused until a neighbour aggregate is declared;
    target_cadence (keyword addition): the grid's step, which the calendar operations and unit
    conversions need (taken from decl.cadence when absent).
    Returns float64 values for rows. Refuses (RecomputeRefusal): an operation not in the list; a
    target-derived operation (not built); a source the recompute was not given; a look-back that is not
    a whole number of the grid's steps.
    """
    name = getattr(decl, "name", "?")
    what = "engineered column %s" % name
    cadence = target_cadence if target_cadence is not None else getattr(decl, "cadence", None)
    g = _Grid(grid, cadence)
    rows = np.asarray(rows, dtype=np.int64)
    if rows.size and (rows.min() < 0 or rows.max() >= g.size):
        raise RecomputeRefusal("%s: sample positions lie off the grid (0..%d)" % (what, g.size - 1))
    if bool(getattr(decl, "reads_target", False)):
        raise RecomputeRefusal("%s reads the target: a target-derived recompute through the label vault is not "
                               "built (no package declares one)" % what)
    srcs = list(getattr(decl, "derived_from", ()) or ())
    op = str(getattr(decl, "operation", None) or "").strip()
    if not op:
        if len(srcs) != 1:
            raise RecomputeRefusal("%s declares no operation and %d sources" % (what, len(srcs)))
        return _source(sources, srcs[0], g.size, what)[rows]
    if len(srcs) != 1:
        raise RecomputeRefusal("%s: operation %r needs exactly one source, got %s" % (what, op, srcs))
    m = _LAG.fullmatch(op)
    if m:
        k = _steps_of(int(m.group(1)), m.group(2), cadence, what)
        return g.back(_source(sources, srcs[0], g.size, what), k)[rows]
    m = _HOLD.fullmatch(op)
    if m:
        through = int(m.group(1))
        v = _source(sources, srcs[0], g.size, what)
        per = g.steps_per_year()
        years = g.year
        out = v.copy()
        later = years > through
        for gap in sorted(set((years[later] - through).tolist())):
            sel = later & (years - through == gap)
            out[sel] = g.back(v, int(gap) * per)[sel]
        return out[rows]
    m = _TRAILING.fullmatch(op)
    if m:
        stat, w = m.group(1), _steps_of(int(m.group(2)), m.group(3), cadence, what)
        min_count = int(m.group(4)) if m.group(4) else 1
        v = _source(sources, srcs[0], g.size, what)
        stack = np.vstack([g.back(v, j) for j in range(w)])
        finite = np.isfinite(stack)
        count = finite.sum(axis=0)
        filled = np.where(finite, stack, np.nan)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if stat == "mean":
                res = np.nanmean(filled, axis=0) if finite.any() else np.full(g.size, np.nan)
            elif stat == "sum":
                res = np.nansum(filled, axis=0)
            elif stat == "min":
                res = np.nanmin(np.where(finite, stack, np.inf), axis=0)
            else:
                res = np.nanmax(np.where(finite, stack, -np.inf), axis=0)
        res = np.where(count >= min_count, res, np.nan)
        return res[rows]
    m = _CUM_SUM.fullmatch(op)
    if m:
        return _cum_sum(_source(sources, srcs[0], g.size, what), g, int(m.group(1)))[rows]
    m = _EWM.fullmatch(op)
    if m:
        return _ewm(_source(sources, srcs[0], g.size, what), g, float(m.group(1)))[rows]
    m = _SINCE.fullmatch(op)
    if m:
        col, test, threshold, unit = m.group(1), m.group(2), float(m.group(3)), m.group(4)
        if col != srcs[0]:
            raise RecomputeRefusal("%s: the event names %r but the source is %r" % (what, col, srcs[0]))
        _steps_of(1, unit, cadence, what)
        return _since(_source(sources, srcs[0], g.size, what), g, _OPS[test], threshold)[rows]
    m = _HARMONIC.fullmatch(op)
    if m:
        fn = np.sin if m.group(1) == "sin" else np.cos
        order, a, b, c = int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5))
        theta = a * math.pi * (g.month.astype(np.float64) - b) / c
        return fn(order * theta)[rows]
    raise RecomputeRefusal("%s: the operation %r is not one the recompute knows (plan 1.5 list)" % (what, op))


__all__ = ["RecomputeRefusal", "recompute_declared_operation"]
