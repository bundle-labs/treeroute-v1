"""Sentinel masking at read (plan 1.3 fill_values / near_sentinel_optout; plan 5 G-SENTINEL, read).

SCIENCE body for the owner-approved signature mask_sentinels (treeroute/_proposed/io_science.py).

The rule, generic for every store:
  - a value equal to one of the column's DECLARED fill values, or with abs >= 1e30, becomes NaN;
  - a value with abs >= 2^30 that survives is FLAGGED (counted), never masked, unless the column
    opts out (near_sentinel_optout);
  - integer columns are cast to float64 first, so a sentinel is removed, never recast;
  - key-role columns are never touched;
  - the target column is never masked: it is REFUSED if it holds a declared fill or abs >= 1e30
    (owner ruling D30: the ingest writes invalid labels as NaN).
The provider codes themselves (for example the panel's integer NoData codes) are STORE facts, read
from the column's fill_values; the engine holds only the two magnitudes, as engine constants
(S5.sentinel_mask_abs, S5.sentinel_flag_abs). This runs before any lag, window, aggregation or fill.
The legal range is the real check (G-RANGE), not this function.

A fill value is compared in float64 and, for a float32 or float16 column, also in the column's own
type, because a writer that stored a fill in float32 rounded it (a float32 column cannot hold
-2^31 + 1, so that code is stored as -2^31).

Facts are read by attribute (the proposed common.ColumnFacts, or any object with ``role``,
``fill_values`` and ``near_sentinel_optout``); engine code may not import the proposed types.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Tuple

import numpy as np
import pandas as pd

from treeroute.engine_constants import SENTINEL_FLAG_ABS, SENTINEL_MASK_ABS
from treeroute.errors import RefusedError

KEY_ROLES = ("key_unit", "key_group", "key_time")
TARGET_ROLE = "target"


@dataclass(frozen=True)
class SentinelReport:
    """Per column: values masked (declared fill or abs >= 1e30) and values flagged (abs >= 2^30).

    ``masked`` holds every non-key, non-target column read (0 included). ``flagged_near_sentinel``
    holds every non-key column that does not opt out (the target included, report only); an
    opted-out column is not counted and does not appear."""
    masked: Mapping[str, int]
    flagged_near_sentinel: Mapping[str, int]


def _value(x: Any) -> Any:
    return x.value if isinstance(x, Enum) else x


def _fact(facts: Any, name: str, column: str) -> Any:
    try:
        return getattr(facts, name)
    except AttributeError:
        raise RefusedError("G-SENTINEL", "the facts of column %r have no %r" % (column, name)) from None


def _fills(facts: Any, column: str) -> Tuple[float, ...]:
    raw = _fact(facts, "fill_values", column)
    if raw is None:
        raw = ()
    out = []
    for f in raw:
        if isinstance(f, (bool, np.bool_)) or not isinstance(f, (int, float, np.integer, np.floating)):
            raise RefusedError("G-SENTINEL", "column %r: fill value %r is not a number" % (column, f))
        if np.isnan(f):
            raise RefusedError("G-SENTINEL", "column %r declares NaN as a fill value; NaN is already "
                               "missing" % column)
        out.append(float(f))
    return tuple(out)


def _hits(values: np.ndarray, fills: Tuple[float, ...]) -> np.ndarray:
    """True where a value equals a declared fill (float64, and the column's own float type) or has
    abs >= the mask magnitude. NaN is never a hit."""
    v64 = values.astype(np.float64)
    hit = np.zeros(len(values), dtype=bool)
    narrow = values.dtype.kind == "f" and values.dtype != np.float64
    for f in fills:
        hit |= v64 == f
        if narrow:
            with np.errstate(over="ignore"):
                cast = np.array(f, dtype=values.dtype)
            if np.isfinite(cast):
                hit |= values == cast
    with np.errstate(invalid="ignore"):
        hit |= np.abs(v64) >= SENTINEL_MASK_ABS
    return hit


def _near(values: np.ndarray, hit: np.ndarray) -> int:
    v64 = values.astype(np.float64)
    with np.errstate(invalid="ignore"):
        return int((np.isfinite(v64) & ~hit & (np.abs(v64) >= SENTINEL_FLAG_ABS)).sum())


# Provenance: panel_sentinel.py:27-84 (exact codes, abs >= 1e30, never mask keys/targets, cast ints
# to float first); presplit_cc/leak_audit.py:66; plan 1.3 (fill_values, near_sentinel_optout),
# plan 5 G-SENTINEL. The panel's codes are STORE facts, never engine literals.
def mask_sentinels(frame: pd.DataFrame, facts: Mapping[str, Any]) -> Tuple[pd.DataFrame, SentinelReport]:
    """Mask declared fill values and abs >= 1e30 to NaN at read, before anything is derived; flag
    abs >= 2^30.

    Rule: G-SENTINEL (read), D30. Returns a new frame (same rows, index and column order) and the
    report; the input frame is not changed. Non-numeric measurement columns (text, dates, booleans)
    cannot hold a numeric code and pass through unchanged, counted 0.
    Refuses: a column in the frame without facts; a repeated column name; a target that holds a
    declared fill or abs >= 1e30 (D30); fill values declared for a non-numeric column; a NaN or
    non-numeric fill value; facts without role, fill_values or near_sentinel_optout.
    """
    if not isinstance(frame, pd.DataFrame):
        raise RefusedError("G-SENTINEL", "frame must be a pandas DataFrame, got %s" % type(frame).__name__)
    names = list(frame.columns)
    twice = sorted({str(c) for c in names if names.count(c) > 1})
    if twice:
        raise RefusedError("G-SENTINEL", "the frame holds these columns more than once: %s" % twice)
    missing = [c for c in names if c not in facts]
    if missing:
        raise RefusedError("G-SENTINEL", "columns without facts: %s (every column read needs its "
                           "facts: G-CLOSED)" % missing)
    out = frame.copy(deep=True)
    masked: Dict[str, int] = {}
    flagged: Dict[str, int] = {}
    for column in names:
        f = facts[column]
        role = _value(_fact(f, "role", column))
        if role in KEY_ROLES:
            continue
        fills = _fills(f, column)
        optout = bool(_fact(f, "near_sentinel_optout", column))
        series = frame[column]
        if pd.api.types.is_bool_dtype(series) or not pd.api.types.is_numeric_dtype(series):
            if fills:
                raise RefusedError("G-SENTINEL", "column %r (dtype %s) is not numeric but declares "
                                   "fill values" % (column, series.dtype))
            if role != TARGET_ROLE:
                masked[column] = 0
            if not optout:
                flagged[column] = 0
            continue
        if pd.api.types.is_integer_dtype(series):
            values = series.astype(np.float64).to_numpy()     # cast first: remove, never recast
        elif isinstance(series.dtype, np.dtype):
            values = series.to_numpy(copy=True)
        else:                                                 # a pandas extension float dtype
            values = series.to_numpy(dtype=np.float64, na_value=np.nan)
        hit = _hits(values, fills)
        if not optout:
            flagged[column] = _near(values, hit)
        if role == TARGET_ROLE:
            if hit.any():
                raise RefusedError(
                    "G-SENTINEL", "the target column %r holds %d values equal to a declared fill or "
                    "with abs >= %g; the target is never masked (D30)" % (column, int(hit.sum()),
                                                                          SENTINEL_MASK_ABS),
                    fix="the ingest must write invalid labels as NaN")
            continue
        values = values.copy()
        values[hit] = np.nan
        out[column] = pd.Series(values, index=frame.index, name=column)
        masked[column] = int(hit.sum())
    return out, SentinelReport(masked=masked, flagged_near_sentinel=flagged)
