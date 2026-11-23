"""The last-value rule (owner ruling J2 d, the owner rulings file's section J; engine constant C18).

  - last_value_max_steps  C18 (months) in target steps: floor(C18 x steps per year / months per year).
  - fill_last_value       a tree feature missing at a step INSIDE its record takes the most recent
                          EARLIER value of the same unit, never a later value, and every fill is counted
                          per column (LastValueRecord, for the run record).

The ruling (J2 d): "a tree feature missing in a month INSIDE its record takes the most recent EARLIER
value of the same unit, at most 2 months back (engine constant), never a later value; every fill is
counted per column; longer gaps fall back to R30."

Where it runs (the caller's order; this module does not wire itself in): after R8's lags (apply_lags for
same-step columns, join_coarser_column for coarser ones) and after the verdicts (apply_verdicts: banned
and conditional columns are gone), on the kept TREE features only, and before R30, so that R30's shares
(ColumnReader.measure) count what is STILL missing and FitContext 0-fills only that. Router context is
never filled here: a fit row whose context is missing leaves the router fit (owner ruling G1), and a
scored row with missing context refuses. The rule is pure: same rows, same order, same index; the input
frame is not changed.

Definitions (per tree feature and per unit; steps are the target's integer steps, io.steps):
  - the unit's RECORD of the column runs from its first to its last step holding a value (a finite
    number) among the rows given; pass every row of each unit (the base rows), or the record is cut
    short;
  - a GAP is a run of steps without a value strictly between two steps with a value, s_a < s_b; its
    length is s_b - s_a - 1 calendar steps, so a step with no row at all inside the run counts too;
  - a gap of at most C18 steps (last_value_max_steps) is FILLED: every missing row in it takes the value
    at s_a, the most recent earlier value of the same unit, which is at most C18 steps back;
  - left to R30 (still missing, counted): a gap longer than C18 ('gap_longer'), the steps before the
    unit's first value, and a unit with no value at all ('head'), the steps after its last value
    ('tail': not inside the record).
A fill value is always a value of the SAME unit at a STRICTLY EARLIER step (re-verified on every fill);
a later VALUE never enters. What the rule does read from later steps is PRESENCE only: whether the
unit's column holds a value somewhere in the next C18 steps (the gap must close within the maximum to
be inside the record and not too long). A later value's size can never change any output.

READING (owner confirmation asked; the code follows the first reading): (1) "longer gaps fall back to
R30" is read per GAP: a gap longer than C18 is left WHOLE to R30, and its first C18 steps are not
filled either. The other reading (each missing step looks back up to C18 steps, so the first C18 steps
of a long gap carry the last value and only the rest falls to R30) would fill more rows. (2) The
maximum is converted to target steps by flooring (a fill never reaches more than C18 months back): 2
steps on a monthly target, 0 on an annual one (no fill on annual data: one step back is 12 months),
floor(2 x 46 / 12) = 7 on 46 composites a year. Regular steps other than one month or one year are
refused, as io.steps refuses them (F8).

Inputs are read by attribute (a cadence has kind, length, unit, composites_per_year), as io.steps
reads them; engine code may not import the proposed types (G-IMPORT).
"""
# Provenance: owner ruling J2 (d), 2026-10-05 (OWNER_RULINGS_2026-10-05.md section J); engine constant
# C18.last_value_max_months (engine_constants.py); the R30 0-fill it runs before (fit/context.py).

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute.errors import RefusedError
from treeroute.io.steps import COMPOSITE_OF_YEAR, REGULAR, as_int_array, cadence_view

RULE = "J2d"
CONSTANT_ID = "C18.last_value_max_months"
_SHOW = 5

# The per-column counts of a LastValueRecord, in record order.
COUNTS = ("missing", "filled", "gap_longer", "head", "tail")


@dataclass(frozen=True)
class LastValueRecord:
    """What fill_last_value did, per tree feature (all counts are rows of the frame given).

    missing     rows without a value before the rule;
    filled      rows the rule filled (each from the same unit's most recent earlier value);
    gap_longer  rows inside the record whose gap is longer than the maximum (left to R30);
    head        rows before the unit's first value, or in a unit with no value (left to R30);
    tail        rows after the unit's last value (left to R30).
    missing == filled + gap_longer + head + tail for every column (checked when built)."""
    max_months: int
    max_steps: int
    rows: int
    units: int
    columns: Tuple[str, ...]
    missing: Mapping[str, int]
    filled: Mapping[str, int]
    gap_longer: Mapping[str, int]
    head: Mapping[str, int]
    tail: Mapping[str, int]

    def left_to_r30(self, column: str) -> int:
        """Rows of the column still missing after the rule (R30 counts and 0-fills them)."""
        return int(self.missing[column] - self.filled[column])

    def total_filled(self) -> int:
        return int(sum(self.filled.values()))

    def as_dict(self) -> Dict[str, Any]:
        """The run-record entry: the rule, the constant (id and value), the step maximum and, per column
        in the order given, its counts and what is left to R30. JSON-ready."""
        per_column = {}
        for c in self.columns:
            entry = {name: int(getattr(self, name)[c]) for name in COUNTS}
            entry["left_to_r30"] = self.left_to_r30(c)
            per_column[c] = entry
        return {"rule": RULE, "constant": {CONSTANT_ID: int(self.max_months)},
                "max_steps": int(self.max_steps), "rows": int(self.rows), "units": int(self.units),
                "filled_rows": self.total_filled(),
                "columns_filled": sum(1 for c in self.columns if self.filled[c] > 0),
                "columns": per_column}

    def summary_line(self) -> str:
        """The one line fill_last_value prints, so the fills are never silent."""
        left = {name: int(sum(getattr(self, name).values())) for name in ("gap_longer", "head", "tail")}
        top = sorted((c for c in self.columns if self.filled[c] > 0), key=lambda c: (-self.filled[c], c))
        shown = ", ".join("%s %d" % (c, self.filled[c]) for c in top[:_SHOW])
        return ("last value (%s, %s = %d months = %d steps), %d rows, %d tree features: %d rows filled in %d "
                "columns%s; left to R30: %d in gaps longer than the maximum, %d before a unit's first value, "
                "%d after its last" % (RULE, CONSTANT_ID, self.max_months, self.max_steps, self.rows,
                                       len(self.columns), self.total_filled(), len(top),
                                       " (most: %s)" % shown if top else "", left["gap_longer"],
                                       left["head"], left["tail"]))


def _int(x: Any, what: str) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise RefusedError(RULE, "%s must be an integer, got %r" % (what, x))
    return int(x)


# Provenance: owner ruling J2 (d) ("at most 2 months back"); C6's conversion of months to steps (steps =
# months x steps per year / 12), floored here because the maximum is a bound.
def last_value_max_steps(target_cadence: Any) -> int:
    """C18 in target steps: floor(C18 months x steps per year / months per year).

    Rule: J2 (d), C18. Steps per year: months per year for a one-month step, 1 for a one-year step,
    composites_per_year for a composite-of-year step. Floored, so a fill never reaches more than C18
    months back: 2 on a monthly target, 0 on an annual one.
    Refuses: a negative or non-integer C18; a regular step other than one month or one year (io.steps
    refuses them too, F8); a static, epoch or irregular cadence (no steps to look back over)."""
    months = _int(K.LAST_VALUE_MAX_MONTHS, CONSTANT_ID)
    if months < 0:
        raise RefusedError(RULE, "%s is negative (%d)" % (CONSTANT_ID, months))
    view = cadence_view(target_cadence)
    if view.kind == REGULAR and view.unit == "month" and view.length == 1:
        per_year = int(K.MONTHS_PER_YEAR)
    elif view.kind == REGULAR and view.unit == "year" and view.length == 1:
        per_year = 1
    elif view.kind == COMPOSITE_OF_YEAR:
        per_year = int(view.composites_per_year)
    else:
        raise RefusedError(RULE, "the last-value rule needs a one-month, one-year or composite-of-year target "
                           "step, got %s (length %r, unit %r)" % (view.kind, view.length, view.unit),
                           fix="steps other than one month, one year or a composite are refused until ruled "
                               "(F8)")
    return (months * per_year) // int(K.MONTHS_PER_YEAR)


def _names(tree_features: Any, frame: pd.DataFrame) -> Tuple[str, ...]:
    if isinstance(tree_features, str) or not isinstance(tree_features, (tuple, list)):
        raise RefusedError(RULE, "tree_features must be a tuple of column names, got %r" % (tree_features,),
                           fix="pass the kept tree features after verdicts (apply_verdicts' tree_features)")
    names = tuple(tree_features)
    bad = [c for c in names if not isinstance(c, str) or not c]
    if bad:
        raise RefusedError(RULE, "tree feature names must be non-empty strings, got %r" % (bad[:_SHOW],))
    twice = sorted({c for c in names if names.count(c) > 1})
    if twice:
        raise RefusedError(RULE, "tree features named more than once: %s" % twice)
    absent = [c for c in names if c not in frame.columns]
    if absent:
        raise RefusedError(RULE, "%d tree features are not columns of the frame: %s"
                           % (len(absent), absent[:20]),
                           fix="pass the lagged frame that holds every kept tree feature")
    return names


def fill_last_value(frame: pd.DataFrame, unit_codes: np.ndarray, steps: np.ndarray,
                    tree_features: Sequence[str], target_cadence: Any) -> Tuple[pd.DataFrame, LastValueRecord]:
    """Fill each tree feature's short gaps inside its record from the same unit's most recent EARLIER
    value; never a later value. Counted per column, and the summary printed.

    Rule: J2 (d), C18 (the module docstring defines record, gap, filled and left-to-R30, and states the
    two readings the code follows). Row i of a tree feature that has no value (NaN) is filled when its
    unit holds a value at an earlier step s_a and at a later step s_b with no value in between, and the
    gap s_b - s_a - 1 is at most last_value_max_steps(target_cadence); it then takes the value at s_a,
    the same unit's most recent earlier value. Every other missing row stays NaN for R30. Columns not in
    tree_features (router context, report columns) and rows that hold a value are returned unchanged.
    Integer and boolean tree features hold no NaN, so nothing is filled in them. Same rows, order, index
    and dtypes; the input frame is not changed.
    The keys arrive as unit_codes and steps (integers, one per frame row), as apply_lags takes them; the
    rows may come in any order (they are sorted by unit and step internally, never assumed adjacent).
    Returns (the filled frame, LastValueRecord); LastValueRecord.as_dict() is the run-record entry.
    Refuses: a frame that is not a DataFrame or repeats a column name; unit codes or steps that are not
    one integer per row; a (unit, step) given twice (G-CALENDAR); tree_features that is not a tuple of
    distinct names, or names a column the frame lacks; a tree feature that is not numeric, or holds an
    infinite value (G-SENTINEL: sentinels are masked at read, so an infinite value is not a gap); a
    target cadence the rule has no step maximum for (last_value_max_steps); (internal) a fill whose
    source is not the same unit at an earlier step within the maximum, or whose counts do not add up.
    """
    if not isinstance(frame, pd.DataFrame):
        raise RefusedError(RULE, "frame must be a pandas DataFrame, got %s" % type(frame).__name__)
    cols = list(frame.columns)
    repeated = sorted({str(c) for c in cols if cols.count(c) > 1})
    if repeated:
        raise RefusedError(RULE, "the frame holds these columns more than once: %s" % repeated)
    units = as_int_array(unit_codes, "unit codes", rule=RULE)
    s = as_int_array(steps, "steps", rule=RULE)
    n = len(frame)
    if len(units) != n or len(s) != n:
        raise RefusedError(RULE, "unit codes (%d) and steps (%d) must be one per frame row (%d)"
                           % (len(units), len(s), n))
    names = _names(tree_features, frame)
    max_months = _int(K.LAST_VALUE_MAX_MONTHS, CONSTANT_ID)
    max_steps = last_value_max_steps(target_cadence)

    order = np.lexsort((s, units))                    # by unit, then step
    us, ss = units[order], s[order]
    if n > 1:
        dup = (us[1:] == us[:-1]) & (ss[1:] == ss[:-1])
        if dup.any():
            i = np.flatnonzero(dup)[:_SHOW]
            raise RefusedError("G-CALENDAR", "%d rows repeat a (unit, step), e.g. %s"
                               % (int(dup.sum()), list(zip(us[i].tolist(), ss[i].tolist()))))

    out = frame.copy(deep=True)
    counts: Dict[str, Dict[str, int]] = {name: {} for name in COUNTS}
    for c in names:
        values = frame[c].to_numpy()
        kind = values.dtype.kind
        if kind not in "fiub":
            raise RefusedError(RULE, "tree feature %r has dtype %s; tree features are numeric" % (c, values.dtype))
        tally = dict.fromkeys(COUNTS, 0)
        if kind == "f":
            if np.isinf(values).any():
                raise RefusedError("G-SENTINEL", "tree feature %r holds %d infinite values; sentinels are masked "
                                   "at read, so an infinite value is not a gap"
                                   % (c, int(np.isinf(values).sum())),
                                   fix="mask the fill value at read (io.sentinel), or fix the store")
            gap_rows = np.isnan(values)
            if gap_rows.any():
                filled_values, tally = _fill_one(c, values, gap_rows, order, us, ss, max_steps)
                out[c] = pd.Series(filled_values, index=frame.index, name=c)
        for name in COUNTS:
            counts[name][c] = int(tally[name])

    record = LastValueRecord(max_months=max_months, max_steps=max_steps, rows=n,
                             units=int(len(np.unique(units))) if n else 0, columns=names,
                             missing=counts["missing"], filled=counts["filled"],
                             gap_longer=counts["gap_longer"], head=counts["head"], tail=counts["tail"])
    print(record.summary_line())
    return out, record


def _fill_one(column: str, values: np.ndarray, gap_rows: np.ndarray, order: np.ndarray, us: np.ndarray,
              ss: np.ndarray, max_steps: int) -> Tuple[np.ndarray, Dict[str, int]]:
    """One float column: (its values with the bridged gaps filled, its counts). Positions below are in
    (unit, step) order; ``order`` maps them back to frame rows."""
    have = ~gap_rows[order]
    fin = np.flatnonzero(have)                         # positions holding a value
    miss = np.flatnonzero(~have)                       # positions without one
    tally = dict.fromkeys(COUNTS, 0)
    tally["missing"] = int(len(miss))
    if len(fin) == 0:                                  # no value anywhere: every gap is a head gap
        tally["head"] = int(len(miss))
        return values.copy(), tally
    k = np.searchsorted(fin, miss)                     # values before each missing position
    prev = fin[np.maximum(k - 1, 0)]                   # the nearest earlier position with a value
    nxt = fin[np.minimum(k, len(fin) - 1)]             # the nearest later position with a value
    has_prev = (k > 0) & (us[prev] == us[miss])        # same unit: the unit's most recent earlier value
    has_next = (k < len(fin)) & (us[nxt] == us[miss])  # same unit: a later value exists (presence only)
    inside = has_prev & has_next
    gap = np.where(inside, ss[nxt] - ss[prev] - 1, 0)  # calendar steps strictly between the two values
    ok = inside & (gap <= max_steps)
    src, dst = prev[ok], miss[ok]
    # the proof every fill carries: same unit, strictly earlier step, at most the maximum back, a value
    if len(dst) and not ((us[src] == us[dst]).all() and (ss[src] < ss[dst]).all()
                         and (ss[dst] - ss[src] <= max_steps).all() and have[src].all()):
        raise RefusedError(RULE, "internal: a last-value fill of %r read another unit, a later step, a step "
                           "beyond the maximum or a missing value" % column)
    tally["filled"] = int(ok.sum())
    tally["gap_longer"] = int((inside & ~ok).sum())
    tally["head"] = int((~has_prev).sum())
    tally["tail"] = int((has_prev & ~has_next).sum())
    if tally["filled"] + tally["gap_longer"] + tally["head"] + tally["tail"] != tally["missing"]:
        raise RefusedError(RULE, "internal: the last-value counts of %r do not add up to its missing rows"
                           % column)
    filled = values.copy()
    filled[order[dst]] = values[order[src]]
    return filled, tally


__all__ = ["RULE", "CONSTANT_ID", "COUNTS", "LastValueRecord", "last_value_max_steps", "fill_last_value"]
