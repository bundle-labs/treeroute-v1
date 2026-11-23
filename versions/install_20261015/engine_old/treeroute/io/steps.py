"""Integer time on grids (plan 2.1 R1, 2.4 R30, 4.1 step 3; 5 G-CALENDAR, G-SUPPORT, G-LOCK).

SCIENCE bodies for the owner-approved signatures of treeroute/_proposed/io_science.py:
  - step_index        R1: the integer step index of every row, from its calendar parts. Never a
                      timestamp (the timestamp bug class, F1).
  - step_bounds       R1, R8: the first and last calendar day of each integer step.
  - build_dense_grid  R30: the KEYS-ONLY dense unit x step grid over the target census.
  - predecessor_index G-CALENDAR: the row exactly k steps back in the same unit, or -1.
Helper (no signature of its own): step_containing, the step that holds a day (the inverse of
step_bounds), for the aggregation and the coarser-column join.

Owner rulings used (SIGNATURES_FOR_REVIEW.md, proposed defaults accepted by the owner):
  - D28: monthly index = year x months-per-year + month, without subtracting 1; annual = year;
    composite-of-year = year x composites per year + composite number.
  - D3: the composite number comes from day_of_year; the composite length is R1's composite_days.
  - D29 (a regular N-day step counts from the first observed day of the WHOLE target table) is NOT
    applied: neither the rows given to step_index nor the cadence carry that origin, so a chunk or a
    driver table at the same cadence would get its own numbering and a (unit, step) join would pair
    the wrong periods. step_index and step_bounds therefore refuse every regular step other than
    one month or one year until the R1 outcome carries an origin (owner decision). No current
    package declares such a cadence.

Types. The shared shapes live in treeroute/_proposed/common.py, which engine code may not import
(G-IMPORT). So the inputs are read by attribute (duck typing): a cadence has ``kind``, ``length``,
``unit`` and, for composites, ``composites_per_year`` and ``composite_days``; an enum member is
read through its ``.value``, so the proposed enums and plain strings both work. DenseGrid below has
exactly the fields of the proposed common.DenseGrid; it moves there when common.py is signed.

Days are proleptic Gregorian ordinals (datetime.date.toordinal), the proposed common.Day.
"""

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

from treeroute.engine_constants import MONTHS_PER_YEAR
from treeroute.errors import RefusedError

# Calendar parts (plan 1.3 key_time facts) and cadence kinds (plan 1.3 store fact 'cadence').
YEAR, MONTH, DAY_OF_YEAR, DATE = "year", "month", "day_of_year", "date"
CALENDAR_PARTS = (YEAR, MONTH, DAY_OF_YEAR, DATE)
REGULAR, COMPOSITE_OF_YEAR, STATIC, EPOCH, IRREGULAR = (
    "regular", "composite_of_year", "static", "epoch", "irregular")
CADENCE_KINDS = (REGULAR, COMPOSITE_OF_YEAR, STATIC, EPOCH, IRREGULAR)
STEP_UNITS = ("day", "month", "year")

# The Unix epoch as numpy counts it, read from numpy rather than typed (no year literal).
_EPOCH_DATE = np.datetime64(0, "D").astype(object)
_EPOCH_ORDINAL = _EPOCH_DATE.toordinal()
_EPOCH_YEAR = _EPOCH_DATE.year
_SHOW = 5  # examples printed in a refusal


@dataclass(frozen=True)
class DenseGrid:
    """KEYS ONLY: every unit x step inside the coverage (plan 2.4 R30, 4.1 step 3). No label, no
    feature. Units are sorted by id; the grid position of (unit r, step first_step + j) is
    r x n_steps + j. Same fields as the proposed common.DenseGrid."""
    unit_ids: Tuple[str, ...]
    group_of_unit: Tuple[str, ...]
    first_step: int
    n_steps: int


@dataclass(frozen=True)
class CadenceView:
    """A cadence read by attribute and normalised: kind and unit as plain strings; for composites,
    composite_days (proposed field, or the store form's length in days) and composites_per_year."""
    kind: str
    length: Optional[int]
    unit: Optional[str]
    composites_per_year: Optional[int]
    composite_days: Optional[int]


# ---------------------------------------------------------------------------------------------------
# small readers shared by the io science modules
def fact_value(value: Any, what: str) -> str:
    """The plain string of an enum member (its .value) or of a string; anything else is refused."""
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        raise RefusedError("G-FACTS", "%s must be an enum member or a string, got %r" % (what, value))
    return value


def _opt_int(value: Any, what: str) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise RefusedError("R1", "%s must be an integer, got %r" % (what, value))
    return int(value)


def cadence_view(cadence: Any) -> CadenceView:
    """Normalise a cadence (proposed common.Cadence, or the store catalog's form) for the rules."""
    try:
        kind = fact_value(cadence.kind, "cadence.kind")
    except AttributeError:
        raise RefusedError("R1", "a cadence needs a 'kind', got %r" % (cadence,)) from None
    if kind not in CADENCE_KINDS:
        raise RefusedError("R1", "unknown cadence kind %r (known: %s)" % (kind, ", ".join(CADENCE_KINDS)))
    length = _opt_int(getattr(cadence, "length", None), "cadence.length")
    unit_raw = getattr(cadence, "unit", None)
    unit = None if unit_raw is None else fact_value(unit_raw, "cadence.unit")
    if unit is not None and unit not in STEP_UNITS:
        raise RefusedError("R1", "unknown cadence unit %r (known: %s)" % (unit, ", ".join(STEP_UNITS)))
    per_year = _opt_int(getattr(cadence, "composites_per_year", None), "cadence.composites_per_year")
    days = _opt_int(getattr(cadence, "composite_days", None), "cadence.composite_days")
    if kind == COMPOSITE_OF_YEAR and unit == "day" and length is not None:
        # the store catalog's form: {kind: composite_of_year, length: N, unit: day}
        if days is not None and days != length:
            raise RefusedError("R1", "a composite-of-year cadence gives its length twice and the two "
                               "disagree (length %d days, composite_days %d)" % (length, days))
        days = length
    if kind == REGULAR and (length is None or unit is None or length < 1):
        raise RefusedError("R1", "a regular cadence needs a positive length and a unit, got %r" % (cadence,))
    if kind == COMPOSITE_OF_YEAR:
        if days is None or days < 1:
            raise RefusedError("R1", "a composite-of-year cadence needs its composite length in days")
        if per_year is None or per_year < 1:
            raise RefusedError("R1", "a composite-of-year cadence needs composites_per_year (the R1 "
                               "outcome); got %r" % (cadence,))
    return CadenceView(kind, length, unit, per_year, days)


def cadence_identity(view: CadenceView) -> Tuple[Any, ...]:
    """What makes two cadences the same step: kind plus (length, unit) for a regular step, kind plus
    (composites_per_year, composite_days) for composites, the kind alone otherwise. The raw fields
    are not compared, so the store form and the proposed form of one composite cadence are equal."""
    if view.kind == REGULAR:
        return (view.kind, view.length, view.unit)
    if view.kind == COMPOSITE_OF_YEAR:
        return (view.kind, view.composites_per_year, view.composite_days)
    return (view.kind,)


def as_int_array(values: Any, what: str, rule: str = "R1") -> np.ndarray:
    """A 1-D int64 array. Integers pass; floats only when every value is a finite whole number;
    booleans, strings and other objects are refused (a key is never guessed from text)."""
    arr = np.asarray(values)
    if arr.ndim != 1:
        raise RefusedError(rule, "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    kind = arr.dtype.kind
    if kind == "b":
        raise RefusedError(rule, "%s holds booleans, not integers" % what)
    if kind in "iu":
        if kind == "u" and arr.size and int(arr.max()) > np.iinfo(np.int64).max:
            raise RefusedError(rule, "%s holds values beyond the int64 range" % what)
        return arr.astype(np.int64)
    if kind == "f":
        if arr.size and not np.isfinite(arr).all():
            raise RefusedError(rule, "%s holds %d non-finite values" % (what, int((~np.isfinite(arr)).sum())))
        if arr.size and not (arr == np.floor(arr)).all():
            raise RefusedError(rule, "%s holds values that are not whole numbers" % what)
        if arr.size and np.abs(arr).max() > float(2 ** 53):
            raise RefusedError(rule, "%s holds values too large to be exact integers" % what)
        return arr.astype(np.int64)
    if kind == "O":
        bad = [v for v in arr.tolist() if isinstance(v, bool) or not isinstance(v, (int, np.integer))]
        if bad:
            raise RefusedError(rule, "%s holds values that are not integers, e.g. %r" % (what, bad[:_SHOW]))
        return np.array([int(v) for v in arr.tolist()], dtype=np.int64)
    raise RefusedError(rule, "%s has dtype %s; integers are needed" % (what, arr.dtype))


def _examples(mask: np.ndarray, *arrays: np.ndarray) -> list:
    idx = np.flatnonzero(mask)[:_SHOW]
    return [tuple(a[i].item() if hasattr(a[i], "item") else a[i] for a in arrays) for i in idx]


# ---------------------------------------------------------------------------------------------------
# calendar arithmetic on day counts (numpy datetime64[D], counted from the Unix epoch)
def _is_leap(year: np.ndarray) -> np.ndarray:
    return (year % 4 == 0) & ((year % 100 != 0) | (year % 400 == 0))


def _days_in_year(year: np.ndarray) -> np.ndarray:
    return np.where(_is_leap(year), 366, 365).astype(np.int64)


def _year_start(year: np.ndarray) -> np.ndarray:
    """Day count (from the Unix epoch) of 1 January of each year."""
    return (year - _EPOCH_YEAR).astype("datetime64[Y]").astype("datetime64[D]").astype(np.int64)


def _month_start(year: np.ndarray, month: np.ndarray) -> np.ndarray:
    months = (year - _EPOCH_YEAR) * MONTHS_PER_YEAR + (month - 1)
    return months.astype("datetime64[M]").astype("datetime64[D]").astype(np.int64)


def _split_days(days: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(year, month, day_of_year) of each day count."""
    d = days.astype("datetime64[D]")
    y = d.astype("datetime64[Y]")
    year = y.astype(np.int64) + _EPOCH_YEAR
    month = (d.astype("datetime64[M]") - y.astype("datetime64[M]")).astype(np.int64) + 1
    doy = (d - y.astype("datetime64[D]")).astype(np.int64) + 1
    return year, month, doy


def _as_days(values: Any, what: str) -> np.ndarray:
    """Whole calendar days as day counts from the Unix epoch. datetime64 values and datetime.date
    objects are accepted; NaT, a time of day other than midnight, and text are refused."""
    arr = np.asarray(values)
    if arr.ndim != 1:
        raise RefusedError("R1", "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    if arr.dtype.kind == "O":
        out = []
        for v in arr.tolist():
            if isinstance(v, datetime.datetime):
                if v.time() != datetime.time(0) or v.tzinfo is not None:
                    raise RefusedError("R1", "%s holds a time of day or a time zone (%r); a date "
                                       "column holds whole days" % (what, v))
                v = v.date()
            if not isinstance(v, datetime.date):
                raise RefusedError("R1", "%s holds %r, not a date" % (what, v))
            out.append(v.toordinal() - _EPOCH_ORDINAL)
        return np.array(out, dtype=np.int64)
    if arr.dtype.kind != "M":
        raise RefusedError("R1", "%s has dtype %s; a date column holds dates" % (what, arr.dtype))
    if np.isnat(arr).any():
        raise RefusedError("R1", "%s holds %d missing dates (NaT)" % (what, int(np.isnat(arr).sum())))
    days = arr.astype("datetime64[D]")
    if (days.astype(arr.dtype) != arr).any():
        raise RefusedError("R1", "%s holds a time of day; a date column holds whole days" % what)
    return days.astype(np.int64)


def days_to_ordinals(days: np.ndarray) -> np.ndarray:
    """Day counts from the Unix epoch to proleptic Gregorian ordinals (common.Day)."""
    return days.astype(np.int64) + _EPOCH_ORDINAL


# ---------------------------------------------------------------------------------------------------
def _calendar(time_columns: Mapping[str, Any], time_facts: Mapping[str, Any]) -> Tuple[int, Dict[str, np.ndarray], Dict[str, str]]:
    """Read and cross-check the calendar parts. Returns (rows, {part: values}, {part: column})."""
    if set(time_columns) != set(time_facts):
        raise RefusedError("R1", "time columns %s and their calendar-part facts %s name different "
                           "columns" % (sorted(time_columns), sorted(time_facts)))
    if not time_columns:
        raise RefusedError("R1", "no time column was given")
    column_of: Dict[str, str] = {}
    for column in sorted(time_facts):
        part = fact_value(time_facts[column], "the calendar part of %r" % column)
        if part not in CALENDAR_PARTS:
            raise RefusedError("R1", "column %r: unknown calendar part %r (known: %s)"
                               % (column, part, ", ".join(CALENDAR_PARTS)))
        if part in column_of:
            raise RefusedError("R1", "columns %r and %r both hold the calendar part %r"
                               % (column_of[part], column, part))
        column_of[part] = column
    parts: Dict[str, np.ndarray] = {}
    for part, column in column_of.items():
        if part == DATE:
            parts[part] = _as_days(time_columns[column], "time column %r" % column)
        else:
            parts[part] = as_int_array(time_columns[column], "time column %r" % column)
    lengths = {len(v) for v in parts.values()}
    if len(lengths) != 1:
        raise RefusedError("R1", "time columns have different lengths: %s"
                           % {column_of[p]: len(v) for p, v in parts.items()})
    rows = lengths.pop()

    if MONTH in parts:
        m = parts[MONTH]
        bad = (m < 1) | (m > MONTHS_PER_YEAR)
        if bad.any():
            raise RefusedError("R1", "column %r: %d months outside 1..%d, e.g. %s"
                               % (column_of[MONTH], int(bad.sum()), MONTHS_PER_YEAR,
                                  _examples(bad, m)))
    if DAY_OF_YEAR in parts:
        d = parts[DAY_OF_YEAR]
        limit = _days_in_year(parts[YEAR]) if YEAR in parts else np.full(rows, 366, np.int64)
        bad = (d < 1) | (d > limit)
        if bad.any():
            raise RefusedError("R1", "column %r: %d days of year outside 1..365 (366 in a leap year), "
                               "e.g. %s" % (column_of[DAY_OF_YEAR], int(bad.sum()), _examples(bad, d)))

    if DATE in parts:
        year, month, doy = _split_days(parts[DATE])
        for part, derived in ((YEAR, year), (MONTH, month), (DAY_OF_YEAR, doy)):
            if part in parts:
                bad = parts[part] != derived
                if bad.any():
                    raise RefusedError("R1", "column %r disagrees with the date column %r on %d rows, "
                                       "e.g. %s" % (column_of[part], column_of[DATE], int(bad.sum()),
                                                    _examples(bad, parts[part], derived)))
        parts.setdefault(YEAR, year)
        parts.setdefault(MONTH, month)
        parts.setdefault(DAY_OF_YEAR, doy)
    return rows, parts, column_of


def _refuse_unused(column_of: Mapping[str, str], used: Tuple[str, ...], cadence_text: str) -> None:
    """An explicit calendar part the cadence's rule does not use is refused, unless a date column
    is present (every part is then checked against the date)."""
    if DATE in column_of:
        return
    extra = sorted(column_of[p] for p in column_of if p not in used)
    if extra:
        raise RefusedError("R1", "a %s step does not use the time column(s) %s; a calendar part the "
                           "cadence does not use suggests a wrong cadence fact" % (cadence_text, extra))


def _need(parts: Mapping[str, np.ndarray], needed: Tuple[str, ...], cadence_text: str) -> None:
    missing = [p for p in needed if p not in parts]
    if missing:
        raise RefusedError("R1", "a %s step needs the calendar part(s) %s (or a date column)"
                           % (cadence_text, ", ".join(missing)))


# Provenance: plan 2.1 R1 ("the step index is year x composites per year + composite number");
# pm25_forecast.py:103 and pm25_architecture.py:166 (monthly t = year x 12 + month).
def step_index(time_columns: Mapping[str, np.ndarray], time_facts: Mapping[str, Any],
               cadence: Any) -> np.ndarray:
    """Integer step index (int64) for every row, from its calendar parts. Never a timestamp.

    Rule: R1 (D28, D3).
    Monthly: year x months-per-year + month (D28, no 1 subtracted). Annual: year. Composite-of-
    year: year x composites per year + composite number, where the composite number is
    (day_of_year - 1) / composite_days + 1 and every day_of_year must sit on that spacing inside its
    year (D3). A date column may stand in for year, month and day_of_year; any explicit part must
    agree with it.
    Other regular steps (N days, or several months or years) are REFUSED: the contract counts them
    from a fixed origin, D29 names the first observed day of the whole target table, and neither
    these rows nor the cadence carry it (counting from the rows given would number a chunk or a
    driver table on its own, silently). They wait for the R1 outcome to carry the origin.
    Refuses: a calendar part out of range; composite spacing that breaks inside a year or a
    composite number above composites_per_year; a regular step other than one month or one year; a
    time column the cadence does not use (without a date column to check it against); IRREGULAR
    cadence (events use Day ordinals, not steps); STATIC and EPOCH cadences (no step).
    """
    view = cadence_view(cadence)
    if view.kind == IRREGULAR:
        raise RefusedError("R1", "an irregular cadence has no step index: events use day ordinals")
    if view.kind in (STATIC, EPOCH):
        raise RefusedError("R1", "a %s cadence has no step index" % view.kind)
    if view.kind == REGULAR and not (view.length == 1 and view.unit in ("month", "year")):
        raise _no_fixed_origin(view)
    rows, parts, column_of = _calendar(time_columns, time_facts)

    if view.kind == COMPOSITE_OF_YEAR:
        text = "composite-of-year"
        _need(parts, (YEAR, DAY_OF_YEAR), text)
        _refuse_unused(column_of, (YEAR, DAY_OF_YEAR), text)
        offset = parts[DAY_OF_YEAR] - 1
        off_grid = offset % view.composite_days != 0
        if off_grid.any():
            raise RefusedError("R1", "%d rows break the %d-day composite spacing inside their year "
                               "(day_of_year - 1 is not a multiple of %d), e.g. (year, day_of_year) %s"
                               % (int(off_grid.sum()), view.composite_days, view.composite_days,
                                  _examples(off_grid, parts[YEAR], parts[DAY_OF_YEAR])))
        number = offset // view.composite_days + 1
        over = number > view.composites_per_year
        if over.any():
            raise RefusedError("R1", "%d rows carry a composite number above composites_per_year = %d, "
                               "e.g. (year, number) %s" % (int(over.sum()), view.composites_per_year,
                                                           _examples(over, parts[YEAR], number)))
        return (parts[YEAR] * view.composites_per_year + number).astype(np.int64)

    # regular: one month or one year (every other regular step was refused above)
    if view.unit == "month":
        _need(parts, (YEAR, MONTH), "monthly")
        _refuse_unused(column_of, (YEAR, MONTH), "monthly")
        return (parts[YEAR] * MONTHS_PER_YEAR + parts[MONTH]).astype(np.int64)
    _need(parts, (YEAR,), "annual")
    _refuse_unused(column_of, (YEAR,), "annual")
    return parts[YEAR].astype(np.int64)


def _no_fixed_origin(view: CadenceView) -> RefusedError:
    """The refusal for a regular step whose index needs an origin the cadence does not carry."""
    return RefusedError(
        "R1", "a regular %d-%s step is counted from a fixed origin (D29: the first observed day of the "
        "whole target table), which the cadence does not carry; counting from the rows given would "
        "number each chunk or driver table on its own and a (unit, step) join would pair the wrong "
        "periods" % (view.length, view.unit),
        fix="owner decision: carry the origin in the R1 outcome, or rule on an origin that does not "
            "depend on the table")


# Provenance: plan 2.1 R1 (the last composite of a year is 5-6 days long).
def step_bounds(steps: np.ndarray, cadence: Any) -> Tuple[np.ndarray, np.ndarray]:
    """First and last calendar day (Day ordinals, inclusive) covered by each integer step.

    Rule: R1, R8. The inverse of step_index. Monthly and annual steps cover their calendar month or
    year. Composite-of-year: composite n of year Y starts on day (n - 1) x composite_days + 1 of Y
    and ends composite_days - 1 days later, or on 31 December, whichever comes first, so the last
    composite of a year is shorter than the rest.
    Refuses: IRREGULAR, STATIC or EPOCH cadence; a composite number that starts after 31 December;
    a regular step other than one month or one year, whose origin (D29) the cadence does not carry
    (step_index refuses it too).
    """
    view = cadence_view(cadence)
    if view.kind in (IRREGULAR, STATIC, EPOCH):
        raise RefusedError("R1", "a %s cadence has no step bounds" % view.kind)
    s = as_int_array(steps, "steps")
    if view.kind == COMPOSITE_OF_YEAR:
        year, n0 = np.divmod(s - 1, view.composites_per_year)
        start = _year_start(year)
        year_end = start + _days_in_year(year) - 1
        first = start + n0 * view.composite_days
        beyond = first > year_end
        if beyond.any():
            raise RefusedError("R1", "%d steps name a composite that starts after 31 December, e.g. "
                               "(year, number) %s" % (int(beyond.sum()), _examples(beyond, year, n0 + 1)))
        last = np.minimum(first + view.composite_days - 1, year_end)
        return days_to_ordinals(first), days_to_ordinals(last)
    if view.unit == "month" and view.length == 1:
        year, m0 = np.divmod(s - 1, MONTHS_PER_YEAR)
        first = _month_start(year, m0 + 1)
        nxt_year, nxt_m0 = np.divmod(s, MONTHS_PER_YEAR)
        last = _month_start(nxt_year, nxt_m0 + 1) - 1
        return days_to_ordinals(first), days_to_ordinals(last)
    if view.unit == "year" and view.length == 1:
        first = _year_start(s)
        last = first + _days_in_year(s) - 1
        return days_to_ordinals(first), days_to_ordinals(last)
    raise _no_fixed_origin(view)


def step_containing(days: np.ndarray, cadence: Any) -> np.ndarray:
    """The integer step (int64) of ``cadence`` whose calendar span holds each day (Day ordinals).

    Rule: R1 (helper). The inverse of step_bounds day by day: every day from step_bounds(s)[0]
    to step_bounds(s)[1] gives s back. Monthly: year x months-per-year + month (D28); annual: the
    year; composite-of-year: year x composites per year + (day_of_year - 1) / composite_days + 1.
    Used to find the coarser step a finer step nests in (aggregate_time, join_coarser_column).
    Refuses: IRREGULAR, STATIC or EPOCH cadence; a regular step other than one month or one year
    (no fixed origin, as step_index); a day whose composite number exceeds composites_per_year (the
    cadence's year count is too small for the calendar); days that are not integers.
    """
    view = cadence_view(cadence)
    if view.kind in (IRREGULAR, STATIC, EPOCH):
        raise RefusedError("R1", "a %s cadence has no steps to hold a day" % view.kind)
    ordinals = as_int_array(days, "days")
    year, month, doy = _split_days(ordinals - _EPOCH_ORDINAL)
    if view.kind == COMPOSITE_OF_YEAR:
        number = (doy - 1) // view.composite_days + 1
        over = number > view.composites_per_year
        if over.any():
            raise RefusedError("R1", "%d days fall in a composite numbered above composites_per_year "
                               "= %d, e.g. (year, number) %s" % (int(over.sum()), view.composites_per_year,
                                                                 _examples(over, year, number)))
        return (year * view.composites_per_year + number).astype(np.int64)
    if view.unit == "month" and view.length == 1:
        return (year * MONTHS_PER_YEAR + month).astype(np.int64)
    if view.unit == "year" and view.length == 1:
        return year.astype(np.int64)
    raise _no_fixed_origin(view)


# ---------------------------------------------------------------------------------------------------
def _ids(values: Any, what: str) -> np.ndarray:
    """Ids as a 1-D object array of non-empty strings (vectorised checks: a census has many rows)."""
    arr = np.asarray(values, dtype=object)
    if arr.ndim != 1:
        raise RefusedError("G-SUPPORT", "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    if len(arr) and pd.api.types.infer_dtype(arr, skipna=False) != "string":
        bad = [v for v in arr.tolist() if not isinstance(v, str)]
        raise RefusedError("G-SUPPORT", "%s must be non-empty strings; got %d others, e.g. %r"
                           % (what, len(bad), bad[:_SHOW]))
    if len(arr) and (arr == "").any():
        raise RefusedError("G-SUPPORT", "%s must be non-empty strings; %d are empty"
                           % (what, int((arr == "").sum())))
    return arr


# Provenance: plan 4.1 step 3, 2.4 R30 (the dense grid holds every unit x step); pm25_forecast.py:
# 122-159 (dense cell x month grid).
def build_dense_grid(unit_ids: np.ndarray, group_ids: np.ndarray, steps: np.ndarray,
                     coverage: Tuple[int, int]) -> DenseGrid:
    """Build the KEYS-ONLY dense unit x step grid over every row of the target census.

    Rule: R30, G-SUPPORT (census), G-LOCK. Keys only, never a label. Units sorted by id (plain
    code-point order of the strings, D37). n_steps = last - first + 1 of the coverage.
    Refuses: duplicate (unit, step); a missing unit x step inside the coverage (a hole in the
    census); a row whose step lies outside the coverage (the census and its coverage disagree); a
    unit in two groups; an empty census; ids that are not non-empty strings.
    """
    units = _ids(unit_ids, "unit ids")
    groups = _ids(group_ids, "group ids")
    s = as_int_array(steps, "steps", rule="G-SUPPORT")
    if not (len(units) == len(groups) == len(s)):
        raise RefusedError("G-SUPPORT", "unit ids (%d), group ids (%d) and steps (%d) differ in length"
                           % (len(units), len(groups), len(s)))
    if len(s) == 0:
        raise RefusedError("G-SUPPORT", "the target census has no rows")
    try:
        bounds = tuple(coverage)
    except TypeError:
        bounds = ()
    if len(bounds) != 2:
        raise RefusedError("G-SUPPORT", "coverage must be (first step, last step), got %r" % (coverage,))
    first = _opt_int(bounds[0], "the first step of the coverage")
    last = _opt_int(bounds[1], "the last step of the coverage")
    if first is None or last is None or first > last:
        raise RefusedError("G-SUPPORT", "coverage must be (first step, last step) with first <= last, "
                           "got %r" % (coverage,))
    outside = (s < first) | (s > last)
    if outside.any():
        raise RefusedError("G-SUPPORT", "%d target rows lie outside the coverage [%d, %d], e.g. "
                           "(unit, step) %s" % (int(outside.sum()), first, last,
                                                 _examples(outside, units, s)))
    first_seen_codes, seen_units = pd.factorize(units, sort=False)
    perm = np.argsort(np.asarray(seen_units, dtype=object), kind="stable")  # code-point order (D37)
    rank = np.empty(len(perm), dtype=np.int64)
    rank[perm] = np.arange(len(perm), dtype=np.int64)
    codes = rank[first_seen_codes]
    unit_list = [str(u) for u in np.asarray(seen_units, dtype=object)[perm].tolist()]
    group_codes, group_names = pd.factorize(groups, sort=False)
    pairs = np.unique(codes * len(group_names) + group_codes)
    groups_per_unit = np.bincount(pairs // len(group_names), minlength=len(unit_list))
    two = np.flatnonzero(groups_per_unit > 1)
    if len(two):
        shown = {unit_list[c]: sorted(str(g) for g in set(groups[codes == c].tolist())) for c in two[:_SHOW]}
        raise RefusedError("G-SUPPORT", "%d units belong to more than one group, e.g. %s" % (len(two), shown))
    group_of_code = np.empty(len(unit_list), dtype=np.int64)
    group_of_code[codes] = group_codes
    group_list = [str(group_names[g]) for g in group_of_code.tolist()]
    n_steps = last - first + 1
    flat = codes * n_steps + (s - first)
    order = np.argsort(flat, kind="stable")
    sorted_flat = flat[order]
    dup = np.zeros(len(s), dtype=bool)
    dup[order[1:]] = sorted_flat[1:] == sorted_flat[:-1]
    if dup.any():
        raise RefusedError("G-SUPPORT", "%d rows repeat a (unit, step) already in the census, e.g. %s"
                           % (int(dup.sum()), _examples(dup, units, s)))
    per_unit = np.bincount(codes, minlength=len(unit_list))
    short = np.flatnonzero(per_unit != n_steps)
    if len(short):
        holes = int((n_steps - per_unit[short]).sum())
        examples = []
        for c in short[:_SHOW]:
            have = np.zeros(n_steps, dtype=bool)
            have[s[codes == c] - first] = True
            examples.append((unit_list[c], int(np.flatnonzero(~have)[0] + first)))
        raise RefusedError("G-SUPPORT", "the census has %d holes (unit x step inside the coverage with "
                           "no row) in %d units, e.g. (unit, first missing step) %s; the ingest must "
                           "write a row with a NaN label for each" % (holes, len(short), examples))
    return DenseGrid(unit_ids=tuple(unit_list), group_of_unit=tuple(group_list),
                     first_step=first, n_steps=n_steps)


# Provenance: forecast_arms.py:127-171 (prev_index: search for (unit, step - lead), re-verify unit
# and step, -1 when absent, asserts never cross a unit).
def predecessor_index(unit_codes: np.ndarray, steps: np.ndarray, k: int) -> np.ndarray:
    """Position of each row's predecessor exactly k steps back in the same unit, or -1.

    Rule: G-CALENDAR. Rows in any order; the result indexes that same order. The predecessor is
    found by searching for (unit, step - k), never assumed to be the adjacent row, and every hit is
    re-verified (same unit, exactly k back). A unit with a gap has no predecessor there (-1).
    Refuses: k < 1 (or not an integer); duplicate (unit, step); (internal) a hit that crosses a unit
    or is not exactly k back.
    """
    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or k < 1:
        raise RefusedError("G-CALENDAR", "k must be an integer >= 1, got %r" % (k,))
    k = int(k)
    unit = as_int_array(unit_codes, "unit codes", rule="G-CALENDAR")
    step = as_int_array(steps, "steps", rule="G-CALENDAR")
    n = len(unit)
    if len(step) != n:
        raise RefusedError("G-CALENDAR", "unit codes (%d) and steps (%d) differ in length" % (n, len(step)))
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    uniq, code = np.unique(unit, return_inverse=True)
    lo = int(step.min())
    span = int(step.max()) - lo + 1 + k
    if len(uniq) * span >= 2 ** 62:
        raise RefusedError("G-CALENDAR", "the (unit, step) key space is too large for one int64 key")
    key = code.astype(np.int64) * span + (step - lo)
    order = np.argsort(key, kind="stable")
    ks = key[order]
    dup = np.zeros(n, dtype=bool)
    dup[order[1:]] = ks[1:] == ks[:-1]
    if dup.any():
        raise RefusedError("G-CALENDAR", "%d rows repeat a (unit, step), e.g. %s"
                           % (int(dup.sum()), _examples(dup, unit, step)))
    want = key - k
    pos = np.searchsorted(ks, want)
    posc = np.minimum(pos, n - 1)
    hit = (pos < n) & (ks[posc] == want)
    out = np.where(hit, order[posc], -1).astype(np.int64)
    good = np.flatnonzero(out >= 0)
    if not ((unit[out[good]] == unit[good]).all() and (step[good] - step[out[good]] == k).all()):
        raise RefusedError("G-CALENDAR", "internal: a predecessor crossed a unit or is not exactly "
                           "%d steps back" % k)
    return out
