"""The time and donor-row derive rules (plan Section 2): R1-R11, R22, and the plan-time records of R23
and R28 (whose approved home is layer/).

SCIENCE bodies for the owner-approved signatures of the proposed derive_rules module, with the decisions
of SIGNATURES_FOR_REVIEW.md (proposed defaults accepted) and the owner rulings file (which wins where
it differs). Each rule is a pure function: it reads its arguments only, writes nothing, draws nothing,
and returns a Derived (value, inputs with hashes, margins, flags). A rule that cannot give a value raises
DeriveRefusal (or TimingRefusal from the timing rules it calls) naming the rule and the fix.

Split independence: no rule here reads split.yaml. The groups (R3) and the donor rows (R22, R23) come in
as arguments; under leave one region out (owner rulings D, E) the caller passes every group, and R3
counts the joined rows (owner ruling F2: a valid label AND the kept drivers present). R9 compares
content epochs with the cuts' days (cut_days gives the day form of R11's step cuts). The router,
unit, bank, batching, smoke and missing-value rules (R12-R21, R30) are in router_rules.py and
unit_rules.py; derive_all is in orchestrate.py.

Guards the approved signatures cannot carry, for derive_all and the run to call:
check_r08_covers_kept_columns (R4's refusal of an empty lag map while kept columns exist) and
check_r23_matches_run (the run's c equals the plan-time R23 record); c_from_donor_y is R23's one formula,
shared with layer.c_for_cut.

Inputs are read by attribute name and enum-valued facts by their value string, so the approved shapes,
this package's copies (derive.shapes) and the package schema's plain strings all work.
"""

import datetime as _dt
import math
from enum import Enum
from fractions import Fraction
from numbers import Integral, Real
from typing import Any, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from treeroute import engine_constants as K
from treeroute import timing
from treeroute.io import steps as _steps

from .derived import (DeriveRefusal, borderline_flags, constants_used, make_derived, sha256_of_array,
                      sha256_of_json)
from .shapes import (Cadence, CadenceKind, Derived, Lag, LeadPlan, LeadUnit, Link,
                     SeasonKeyKind, SeasonKeySpec, StepUnit, TestWindowPlan, Windows)

# value strings of the facts (compared as text, see the module docstring)
REGULAR, COMPOSITE, STATIC, EPOCH, IRREGULAR = ("regular", "composite_of_year", "static", "epoch",
                                                "irregular")
DAY, MONTH, YEAR = "day", "month", "year"
P_YEAR, P_MONTH, P_DOY, P_DATE = "year", "month", "day_of_year", "date"
FIT = "fit"
GUARD = "guard"
PICKED_SCOPE = "picked"            # D16: the donor-row rules read the PICKED donor units
NO_LAG_KINDS = (STATIC, EPOCH, IRREGULAR)   # R8: cadences without steps to lag by, listed by kind
SHORT_RECORD = "short record"
CADENCE_FIELDS = ("kind", "length", "unit", "composites_per_year", "composite_days")
_SHOW = 5


def _value(x: Any) -> Any:
    return x.value if isinstance(x, Enum) else x


def _int(x: Any, what: str, rule: str) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (Integral, np.integer)):
        raise DeriveRefusal(rule, "%s must be a whole number, got %r" % (what, x),
                            fix="pass a whole number")
    return int(x)


def _round_half_up(x: Fraction) -> int:
    """R10 / D4: round half up on an exact fraction (0.5 -> 1, 1.5 -> 2)."""
    return math.floor(x + Fraction(1, 2))


def _require_half_up() -> None:
    if K.LEAD_ROUNDING != "half_up":
        raise DeriveRefusal("R10", "engine constant C6.lead_rounding is %r; the rules implement "
                            "'half_up' only" % (K.LEAD_ROUNDING,),
                            fix="an engine version change must change the rounding code too")


def _cadence_parts(cadence: Any, what: str, rule: str) -> Tuple[str, Optional[int], Optional[str]]:
    """(kind, length, unit) of a cadence as plain values; a composite's length is its days (the
    approved composite_days, or the store form's {length, unit: day})."""
    if cadence is None:
        raise DeriveRefusal(rule, "%s has no cadence" % what, fix="pass the R1 cadence")
    kind = _value(getattr(cadence, "kind", None))
    length = getattr(cadence, "length", None)
    unit = _value(getattr(cadence, "unit", None))
    if kind == COMPOSITE:
        days = getattr(cadence, "composite_days", None)
        length, unit = (days if days is not None else length), DAY
    if length is not None:
        length = _int(length, what + " cadence length", rule)
    return kind, length, unit


# ===================================================================================================
# R1 cadence
class _Spacing(NamedTuple):
    """The spacing of consecutive rows of the SAME unit on one time line, measured on every unit."""
    order: np.ndarray              # row order that sorts by (unit, time)
    c: np.ndarray                  # unit code per sorted row
    t: np.ndarray                  # time per sorted row
    same: np.ndarray               # sorted rows i and i + 1 belong to one unit
    spaced: np.ndarray             # codes of the units with at least one gap (two rows or more)
    mins: np.ndarray               # smallest gap per spaced unit
    maxs: np.ndarray               # largest gap per spaced unit
    gaps_per_unit: np.ndarray      # gaps per spaced unit
    lonely: np.ndarray             # codes of the units with one row
    summary: Dict[str, Any]        # what derived.json records


def _unit_spacing(codes: np.ndarray, coord: np.ndarray, uniques: Any, line: str,
                  rule: str) -> _Spacing:
    order = np.lexsort((coord, codes))
    c, t = codes[order], coord[order]
    same = c[1:] == c[:-1]
    gaps = (t[1:] - t[:-1])[same]
    gap_unit = c[1:][same]
    repeated = gaps == 0
    if repeated.any():
        where = np.flatnonzero(same)[repeated][:_SHOW] + 1
        examples = [(str(uniques[c[i]]), int(t[i])) for i in where]
        raise DeriveRefusal(rule, "%d rows repeat a (unit, time) key, e.g. %s (time on the %s line)"
                            % (int(repeated.sum()), examples, line),
                            fix="the target table holds one row per unit and time (plan 1.2)")
    if gaps.size:
        starts = np.flatnonzero(np.r_[True, gap_unit[1:] != gap_unit[:-1]])
        mins = np.minimum.reduceat(gaps, starts)
        maxs = np.maximum.reduceat(gaps, starts)
        spaced = gap_unit[starts]
        gaps_per_unit = np.diff(np.r_[starts, gaps.size])
    else:
        mins = maxs = spaced = gaps_per_unit = np.zeros(0, dtype=np.int64)
    regular = mins == maxs
    lonely = np.setdiff1d(np.arange(len(uniques)), spaced)
    steps_seen, counts = np.unique(mins[regular], return_counts=True)
    pairs = pd.DataFrame({"u": gap_unit, "d": gaps}).drop_duplicates()
    summary = {"units_by_spacing": {int(k): int(v) for k, v in
                                    pairs["d"].value_counts().sort_index().items()},
               "regular_units_by_step": {int(s): int(n) for s, n in zip(steps_seen, counts)},
               "irregular_units": int((~regular).sum()), "single_row_units": int(len(lonely))}
    return _Spacing(order, c, t, same, spaced, mins, maxs, gaps_per_unit, lonely, summary)


def _date_anchor(days: np.ndarray) -> Optional[Tuple[str, np.ndarray, str]]:
    """(time line, coordinate on it, description) when every date sits at the same place in its year
    (the same month and day) or in its month (the same day, or the last day of each month): such dates
    carry a year or a month only. None otherwise, and for a table with one date."""
    if np.unique(days).size < 2:
        return None
    year, month, _ = _steps._split_days(days)
    dom = days - _steps._month_start(year, month) + 1
    if (month == month[0]).all() and (dom == dom[0]).all():
        return YEAR, year, "every date is month %d, day %d of its year" % (month[0], dom[0])
    months = year * K.MONTHS_PER_YEAR + month - 1
    if (dom == dom[0]).all():
        return MONTH, months, "every date is day %d of its month" % dom[0]
    if (_steps._split_days(days + 1)[1] != month).all():
        return MONTH, months, "every date is the last day of its month"
    return None


def _names(uniques: Any, codes: np.ndarray) -> List[str]:
    return [str(uniques[u]) for u in codes[:_SHOW]]


def _month_or_year_grid(rule: str, sp: _Spacing, line: str, uniques: Any, inputs: Dict[str, Any],
                        hashes: Dict[str, str], anchor: Optional[str]) -> Derived:
    """R1 on a month or year time line: a grid with one shared step, or a refusal (events need a date
    that carries its day)."""
    regular = sp.mins == sp.maxs
    context = "" if anchor is None else "%s, so the rows are read on the %s time line: " % (anchor, line)
    events_clause = ("events are keyed by a date, plan 1.2" if anchor is None else "event dates that "
                     "all fall on one place of the %s carry no day, and R10 counts event leads in "
                     "days" % line)
    events_fix = ("key events by a date column" if anchor is None
                  else "give events their true visit dates")
    if len(sp.spaced) == 0:
        raise DeriveRefusal(rule, "%severy unit has one row: no step can be seen" % context,
                            fix="read the whole target table (a grid holds every unit x step, plan "
                                "1.2), or %s" % events_fix)
    if len(sp.lonely) or not regular.all():
        raise DeriveRefusal(
            rule, "%son a %s time line %d units have one row (e.g. %s) and %d units have irregular "
            "spacing (e.g. %s); neither a grid (every unit shares one step) nor events (%s)"
            % (context, line, len(sp.lonely), _names(uniques, sp.lonely), int((~regular).sum()),
               _names(uniques, sp.spaced[~regular]), events_clause),
            fix="complete the census (NaN labels for invalid rows), or %s" % events_fix)
    by_step = sp.summary["regular_units_by_step"]
    if len(by_step) > 1:
        raise DeriveRefusal(rule, "%sunits are each regular but with different steps %s (units per "
                            "step); R1 knows one shared step (grid) or irregular dates (events), D2"
                            % (context, by_step), fix="split the target into tables with one step")
    cadence = Cadence(kind=CadenceKind.REGULAR, length=int(next(iter(by_step))),
                      unit=StepUnit.MONTH if line == MONTH else StepUnit.YEAR)
    return make_derived(rule, cadence, inputs, hashes)


def _composite_of_year(rule: str, sp: _Spacing, year: np.ndarray, doy: np.ndarray, uniques: Any,
                       inputs: Dict[str, Any], hashes: Dict[str, str]) -> Optional[Derived]:
    """R1 composite-of-year (D3) on a day time line: the Derived, a refusal, or None when the rows
    show no composite calendar (the caller then reads events)."""
    year_s, doy_s = year[sp.order], doy[sp.order]
    step = sp.t[1:] - sp.t[:-1]
    same_year = sp.same & (year_s[1:] == year_s[:-1])
    within = step[same_year]
    inputs["within_year_spacings"] = ({int(k): int(v) for k, v in
                                       zip(*np.unique(within, return_counts=True))}
                                      if within.size else {})
    if within.size == 0:
        return None
    values, counts = np.unique(within, return_counts=True)
    n0 = int(values[int(np.argmax(counts))])               # the usual within-year spacing
    if n0 < 2:
        return None
    off = (doy_s - 1) % n0 != 0                             # rows that do not start a composite
    broken = within != n0
    i = np.flatnonzero(sp.same & ~same_year)                # pairs (i, i + 1) across a year end
    y_prev, y_next, d_prev, d_next = year_s[i], year_s[i + 1], doy_s[i], doy_s[i + 1]
    late = d_next != 1                                      # a later unit-year that misses composite 1
    early = d_prev + n0 <= _steps._days_in_year(y_prev)    # a year that stops before its last composite
    skipped = y_next != y_prev + 1                          # a whole year missing
    inputs["composite_check"] = {
        "usual_within_year_spacing": n0, "rows_off_grid": int(off.sum()),
        "within_year_pairs_off_spacing": int(broken.sum()), "year_end_crossings": int(i.size),
        "later_unit_years_starting_after_day_one": int(late.sum()),
        "unit_years_ending_before_their_last_composite": int(early.sum()),
        "crossings_skipping_a_year": int(skipped.sum())}
    reset_seen = bool(i.size) and not late.any()
    on_grid = not off.any() and not broken.any()
    if not (reset_seen or on_grid):
        return None
    evidence = ("every later unit-year restarts on 1 January" if reset_seen else
                "every row starts a %d-day composite counted from 1 January" % n0)

    def at(mask: np.ndarray, *cols: np.ndarray) -> List[Tuple[Any, ...]]:
        rows = np.flatnonzero(mask)[:_SHOW]
        return [(str(uniques[sp.c[i[r] + 1]]),) + tuple(int(col[r]) for col in cols) for r in rows]

    problems = []
    if len(sp.lonely):
        problems.append("%d units have one row (e.g. %s)" % (len(sp.lonely),
                                                             _names(uniques, sp.lonely)))
    if broken.any():
        problems.append("its spacing breaks inside a year: within-year spacings %s (row pairs per "
                        "spacing)" % inputs["within_year_spacings"])
    if off.any():
        problems.append("%d rows off the %d-day grid" % (int(off.sum()), n0))
    if not i.size:
        problems.append("no unit crosses a year end, so the 1 January restart is never seen")
    if late.any():
        problems.append("%d unit-years after a unit's first year start after 1 January, e.g. (unit, "
                        "year, day_of_year) %s" % (int(late.sum()), at(late, y_next, d_next)))
    if early.any():
        problems.append("%d unit-years stop before their last composite, e.g. (unit, year, last "
                        "day_of_year) %s" % (int(early.sum()), at(early, y_prev, d_prev)))
    if skipped.any():
        problems.append("%d gaps skip a whole year, e.g. (unit, year, next year) %s"
                        % (int(skipped.sum()), at(skipped, y_prev, y_next)))
    if problems:
        raise DeriveRefusal(rule, "a composite-of-year calendar (%s; usual within-year spacing %d "
                            "days) that is not a complete grid: %s" % (evidence, n0, "; ".join(problems)),
                            fix="complete the census (NaN labels for invalid rows), or check the "
                                "day_of_year column")
    per_year = int(((doy_s - 1) // n0 + 1).max())
    inputs["composite_days"], inputs["composites_per_year_observed"] = n0, per_year
    cadence = Cadence(kind=CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=per_year,
                      composite_days=n0)
    return make_derived(rule, cadence, inputs, hashes)


def _day_grid(rule: str, sp: _Spacing, year: np.ndarray, doy: np.ndarray, uniques: Any,
              inputs: Dict[str, Any], hashes: Dict[str, str]) -> Derived:
    """R1 on a day time line: a regular N-day grid, a composite-of-year grid, events, or a refusal."""
    regular = sp.mins == sp.maxs
    showing = sp.gaps_per_unit >= 2              # a unit with 3 rows or more shows whether it is regular
    by_step = sp.summary["regular_units_by_step"]
    doy_s = doy[sp.order]

    # one regular step shared by every unit
    if not len(sp.lonely) and regular.all() and len(by_step) == 1:
        n = int(next(iter(by_step)))
        if n >= 2 and ((doy_s - 1) % n == 0).all():
            raise DeriveRefusal(
                rule, "every unit shows one regular %d-day step and every row starts a %d-day period "
                "counted from 1 January, so the rows fit both a regular %d-day step and a %d-day "
                "composite-of-year calendar; no year end in the data tells them apart (composites "
                "restart on 1 January, which shows as a shorter gap at a year end)" % (n, n, n, n),
                fix="read the whole target table: a year end where the spacing restarts, or keeps "
                    "its %d days, tells the two apart" % n)
        cadence = Cadence(kind=CadenceKind.REGULAR, length=n, unit=StepUnit.DAY)
        return make_derived(rule, cadence, inputs, hashes)

    # the units that show a step are all regular: a grid core, refused if anything breaks it
    if showing.any() and regular[showing].all():
        core = {int(s): int(k) for s, k in zip(*np.unique(sp.mins[showing], return_counts=True))}
        if len(core) > 1:
            raise DeriveRefusal(rule, "units are each regular but with different day steps %s (units "
                                "with 3 rows or more, per step), D2" % core,
                                fix="split the target into tables with one step")
        n = int(next(iter(core)))
        other = ~showing & (sp.mins != n)
        if not (len(sp.lonely) or other.any()):
            raise DeriveRefusal(rule, "internal: a regular %d-day grid reached the refusal" % n,
                                fix="report this engine bug")
        raise DeriveRefusal(
            rule, "every unit with 3 rows or more is regular at %d days (%d units), but %d units have "
            "one row (e.g. %s) and %d units have two rows at another spacing (e.g. %s); neither a "
            "grid (every unit shares one step) nor events (dates irregular per unit)%s"
            % (n, core[n], len(sp.lonely), _names(uniques, sp.lonely), int(other.sum()),
               _names(uniques, sp.spaced[other]), ", D2" if other.any() else ""),
            fix="complete the census (NaN labels for invalid rows), or split the target into tables "
                "with one step")

    composite = _composite_of_year(rule, sp, year, doy, uniques, inputs, hashes)
    if composite is not None:
        return composite
    shown = int((showing & regular).sum())
    flags = ("regular_units_in_events:%d" % shown,) if shown else ()
    return make_derived(rule, Cadence(kind=CadenceKind.IRREGULAR), inputs, hashes, flags=flags)


# Provenance: plan 2.1 R1; composite-of-year clause (8- and 16-day composites restart 1 January).
def derive_r01_cadence(unit_ids: np.ndarray, time_values: Mapping[str, np.ndarray],
                       time_facts: Mapping[str, Any]) -> Derived:
    """The target's cadence and step: one regular step (grid), a composite-of-year grid, or events.

    Rule: R1 (D2, D3). The calendar parts come from the key_time facts (io.steps reads and cross-checks
    them: every column has a fact and every fact a column, parts in range, a date agrees with any
    explicit part). The finest part sets the time line: a date, or year + day_of_year, gives days; year
    + month gives months; year alone gives years. On a day time line whose dates all sit at the same
    place in their year (the same month and day) or in their month (the same day, or the last day of
    each month), the dates carry a year or a month only: a date column is then read on the year or
    month time line (the anchor is recorded), and a year + day_of_year calendar is refused (declare
    the parts that step uses). The spacing between consecutive rows of the SAME unit is measured on
    every unit, never a sample; a repeated (unit, time) is refused.
    Month or year time line: every unit has at least two rows and shows one spacing, and all units show
    the SAME one -> grid (1 month, 1 year, k months, ...). Anything else is refused (events need a date
    that carries its day: plan 1.2 keys a visit by its date and R10 counts event leads in days).
    Day time line, in this order:
      - Regular grid: every unit has at least two rows and all show the SAME one spacing N. When
        N >= 2 and every row starts an N-day period counted from 1 January, the rows fit a regular
        N-day step and an N-day composite-of-year calendar alike (no year end shows a restart): refused.
      - Grid core: when every unit with 3 rows or more (a unit with two rows has one gap and shows no
        regularity) is regular at one spacing N but a unit has one row, or two rows at another spacing,
        it is refused, as the month line refuses it; regular at DIFFERENT spacings is refused (D2).
      - Composite-of-year (D3): the usual within-year spacing N (the most common gap between rows of
        one unit in one year) is >= 2 days and the rows show the calendar, either because every
        unit-year after a unit's first restarts on 1 January (the reset is seen), or because every row
        starts an N-day composite counted from 1 January and every within-year spacing is N. It is then
        accepted only as a complete grid: every within-year spacing N; every row on the grid; at least
        one year end crossed; every unit-year after a unit's first starting on 1 January (a unit's
        first year may start later, at the edge of its record); every unit-year before a unit's last
        reaching its last composite (day_of_year + N passes the year's last day); no whole year
        missing; no unit with one row. Otherwise refused, never read as events. The composite length is
        N; composites per year is the largest composite number observed ((day_of_year - 1) / N + 1).
      - Events: anything else (single visits, or dates irregular per unit). Units with 3 rows or more
        that are regular anyway are counted and flagged 'regular_units_in_events:<n>'.
    Returns Derived[Cadence]; inputs record the calendar parts, the time line (and any date anchor),
    the rows and units, how many units showed each spacing (with the units that showed none or
    several), and on a day line the within-year spacings and the composite checks.
    Refuses: an empty table; a time column without a calendar-part fact or a fact without a column
    (and every other calendar refusal of io.steps); a missing unit id; a repeated (unit, time); a
    calendar part it cannot place (a month without a year, a day_of_year without a year, a month that
    disagrees with year + day_of_year); every case the list above refuses.
    """
    rule = "R1"
    rows, parts, column_of = _steps._calendar(time_values, time_facts)
    if rows == 0:
        raise DeriveRefusal(rule, "the target table is empty", fix="read the target table first")
    units = np.asarray(unit_ids)
    if units.ndim != 1 or len(units) != rows:
        raise DeriveRefusal(rule, "unit ids have shape %s but the time columns hold %d rows"
                            % (units.shape, rows), fix="pass one unit id per target row")
    codes, uniques = pd.factorize(units, sort=False)
    if (codes < 0).any():
        raise DeriveRefusal(rule, "%d rows have no unit id" % int((codes < 0).sum()),
                            fix="every target row needs its unit id (plan 1.2)")

    # the time line
    if P_DATE in column_of:
        line, coord = DAY, parts[P_DATE]
    elif P_DOY in column_of:
        if P_YEAR not in column_of:
            raise DeriveRefusal(rule, "a day_of_year column needs a year column (or a date column)",
                                fix="declare the year's key_time column")
        coord = _steps._year_start(parts[P_YEAR]) + parts[P_DOY] - 1
        if P_MONTH in column_of:
            month_of_day = _steps._split_days(coord)[1]
            bad = month_of_day != parts[P_MONTH]
            if bad.any():
                raise DeriveRefusal(rule, "column %r disagrees with year + day_of_year on %d rows"
                                    % (column_of[P_MONTH], int(bad.sum())),
                                    fix="check the calendar-part facts")
        line = DAY
    elif P_MONTH in column_of:
        if P_YEAR not in column_of:
            raise DeriveRefusal(rule, "a month column needs a year column (or a date column)",
                                fix="declare the year's key_time column")
        line = MONTH
        coord = parts[P_YEAR] * K.MONTHS_PER_YEAR + parts[P_MONTH] - 1
    else:
        line, coord = YEAR, parts[P_YEAR]
    coord = np.asarray(coord, dtype=np.int64)
    n_units = len(uniques)
    inputs: Dict[str, Any] = {
        "calendar_parts": {column: part for part, column in sorted(column_of.items())},
        "rows": int(rows), "units": int(n_units)}
    hashes = {"unit_ids": sha256_of_array(units)}
    for column in sorted(time_values):
        hashes["time:" + column] = sha256_of_array(time_values[column])

    anchor = None
    if line == DAY:
        anchored = _date_anchor(coord)
        if anchored is not None:
            new_line, new_coord, anchor = anchored
            if P_DATE not in column_of:
                raise DeriveRefusal(rule, "a year + day_of_year calendar in which %s: the rows carry %s "
                                    "only, not a day" % (anchor, "a year" if new_line == YEAR
                                                         else "a month"),
                                    fix="declare the calendar parts that step uses (%s), or one date "
                                        "column" % ("year" if new_line == YEAR else "year + month"))
            inputs["date_anchor"] = anchor
            line, coord = new_line, np.asarray(new_coord, dtype=np.int64)
    sp = _unit_spacing(codes, coord, uniques, line, rule)
    inputs["time_line"] = line
    inputs.update(sp.summary)
    if line in (MONTH, YEAR):
        return _month_or_year_grid(rule, sp, line, uniques, inputs, hashes, anchor)
    return _day_grid(rule, sp, parts[P_YEAR], parts[P_DOY], uniques, inputs, hashes)


# ===================================================================================================
# R2 season key
# Provenance: plan 2.1 R2; U-2 (annual data: one constant class).
def derive_r02_season_key(cadence: Any, observed_composites_per_year: Optional[int]) -> Derived:
    """The season key (a step's position within its year) and the number of steps per year.

    Rule: R2 (D4, D5). One month: month-of-year, months-per-year steps (C6). k months with k dividing
    the months of a year: the step's position in its year, months-per-year / k steps. One year: ONE
    constant class, 1 step per year (U-2). Composite-of-year: the composite number, steps per year =
    the composites per year observed in the data. Events: the month of the event date, steps per year
    None.
    Refuses: STATIC or EPOCH cadence; a composite grid without observed_composites_per_year, or whose
    cadence records a different count; observed_composites_per_year given for any other cadence; a
    regular N-day step with no year reset (D5, accepted: its season key is not defined until the owner
    defines it; the 365.25 / N rounded half up steps per year (D4) is printed in the refusal); k
    months with k not dividing the months of a year, and k years with k > 1 (their position in the
    year drifts, the same gap as D5; steps per year would not be a whole number).
    """
    rule = "R2"
    kind, length, unit = _cadence_parts(cadence, "the target", rule)
    if observed_composites_per_year is not None and kind != COMPOSITE:
        raise DeriveRefusal(rule, "observed_composites_per_year is given for a %s cadence" % kind,
                            fix="pass it for composite-of-year grids only")
    inputs: Dict[str, Any] = {"cadence": _fact_dict(cadence, CADENCE_FIELDS)}
    if kind in (STATIC, EPOCH):
        raise DeriveRefusal(rule, "a %s cadence cannot be a target's" % kind,
                            fix="R1 gives the target a grid or events")
    if kind == IRREGULAR:
        spec = SeasonKeySpec(kind=SeasonKeyKind.EVENT_MONTH, steps_per_year=None)
    elif kind == COMPOSITE:
        if observed_composites_per_year is None:
            raise DeriveRefusal(rule, "a composite-of-year grid needs the composites per year observed "
                                "in the data", fix="pass R1's composites_per_year")
        observed = _int(observed_composites_per_year, "observed_composites_per_year", rule)
        recorded = getattr(cadence, "composites_per_year", None)
        if recorded is not None and _int(recorded, "composites_per_year", rule) != observed:
            raise DeriveRefusal(rule, "the cadence records %r composites per year but %d were observed"
                                % (recorded, observed), fix="pass R1's own outcome")
        if observed < 1:
            raise DeriveRefusal(rule, "observed composites per year is %d" % observed,
                                fix="pass R1's composites_per_year")
        inputs["observed_composites_per_year"] = observed
        spec = SeasonKeySpec(kind=SeasonKeyKind.COMPOSITE_NUMBER, steps_per_year=observed)
    elif kind == REGULAR:
        if length is None or length < 1 or unit not in (DAY, MONTH, YEAR):
            raise DeriveRefusal(rule, "a regular cadence needs a positive length and a unit, got %r"
                                % (cadence,), fix="pass R1's cadence")
        inputs["constants"] = constants_used("C6.months_per_year", "C6.days_per_year")
        if unit == MONTH and length == 1:
            spec = SeasonKeySpec(kind=SeasonKeyKind.MONTH_OF_YEAR, steps_per_year=K.MONTHS_PER_YEAR)
        elif unit == MONTH and K.MONTHS_PER_YEAR % length == 0:
            spec = SeasonKeySpec(kind=SeasonKeyKind.STEP_POSITION_IN_YEAR,
                                 steps_per_year=K.MONTHS_PER_YEAR // length)
        elif unit == YEAR and length == 1:
            spec = SeasonKeySpec(kind=SeasonKeyKind.CONSTANT, steps_per_year=1)
        elif unit == DAY:
            per_year = _round_half_up(Fraction(repr(K.DAYS_PER_YEAR)) / length)
            raise DeriveRefusal(rule, "a regular %d-day step with no year reset: its steps drift across "
                                "years, and the plan defines no season key for it (D5); its steps per "
                                "year would be 365.25 / %d rounded half up = %d"
                                % (length, length, per_year),
                                fix="owner decision D5: define the season key of such data first")
        else:
            raise DeriveRefusal(rule, "a regular %d-%s step: its position in the year drifts and its "
                                "steps per year are not a whole number; the plan defines no season "
                                "key for it (the gap D5 names)" % (length, unit),
                                fix="owner decision: define the season key of such data first")
    else:
        raise DeriveRefusal(rule, "unknown cadence kind %r" % (kind,), fix="pass R1's cadence")
    return make_derived(rule, spec, inputs)


# ===================================================================================================
# R3 coverage end
# Provenance: plan 2.1 R3 ("reads only whether rows exist, never their values"); D6 (valid-label rows);
# owner ruling F2 (count only rows that have BOTH a valid label AND the kept drivers present: the joined
# rows).
def count_valid_rows_per_group_year(group_ids: np.ndarray, years: np.ndarray, label_is_valid: np.ndarray,
                                    drivers_present: np.ndarray,
                                    groups: Tuple[str, ...]) -> Mapping[Tuple[str, int], int]:
    """{(group, year): number of JOINED rows}, for the listed groups only (R3 input; D6, F2).

    A row counts when its label is VALID (D6; a boolean per row, e.g. LabelView.validity) AND its kept
    drivers are present (owner ruling F2: the joined rows). drivers_present is the caller's boolean
    per row, from the driver stores only (never a label): every driver store that holds a kept
    column has a row for the row's unit at the row's step, and a store that declares the row's group
    absent counts as present (declared absences are allowed silently, ruling F8). It is presence of
    the joined row, not the absence of missing values: a kept column that is missing on a joined
    row, or vanishes in a test year, is R30's to flag, not R3's to cut.
    Reads validity and presence only, never a value. Rows of groups not listed are not counted. A
    listed group with no counted row gets no key (R3 refuses it).
    Refuses: arrays of different lengths; a validity or presence array that is not boolean;
    duplicate groups.
    """
    rule = "R3"
    g = np.asarray(group_ids, dtype=object)
    y = _steps.as_int_array(years, "years", rule)
    v = np.asarray(label_is_valid)
    d = np.asarray(drivers_present)
    if not (g.ndim == v.ndim == d.ndim == 1) or not (len(g) == len(y) == len(v) == len(d)):
        raise DeriveRefusal(rule, "group ids, years, validity and driver presence have lengths %d, %d, "
                            "%d, %d" % (len(g), len(y), len(v), len(d)),
                            fix="pass one entry per target row")
    if v.dtype.kind != "b":
        raise DeriveRefusal(rule, "validity must be boolean (valid / not), got dtype %s" % v.dtype,
                            fix="pass the validity flags, never label values")
    if d.dtype.kind != "b":
        raise DeriveRefusal(rule, "driver presence must be boolean (joined / not), got dtype %s"
                            % d.dtype, fix="pass the driver stores' row presence (ruling F2)")
    listed = _group_set(groups, rule)
    keep = v & d & pd.Series(g).isin(listed).to_numpy()
    frame = pd.DataFrame({"g": g[keep], "y": y[keep]})
    counts = frame.groupby(["g", "y"], sort=True).size()
    return {(str(k[0]), int(k[1])): int(n) for k, n in counts.items()}


def _group_set(groups: Any, rule: str) -> Tuple[str, ...]:
    if isinstance(groups, str) or not isinstance(groups, (tuple, list)):
        raise DeriveRefusal(rule, "groups must be a tuple of group names, got %r" % (groups,),
                            fix="pass the group set as a tuple")
    names = tuple(groups)
    bad = [x for x in names if not isinstance(x, str) or not x]
    if bad:
        raise DeriveRefusal(rule, "group names are non-empty text, got %r" % (bad[:_SHOW],),
                            fix="pass group names")
    if len(set(names)) != len(names):
        raise DeriveRefusal(rule, "the group set names a group twice", fix="pass a set")
    if not names:
        raise DeriveRefusal(rule, "the group set is empty", fix="pass the groups R3 judges")
    return tuple(sorted(names))


# Provenance: plan 2.1 R3; convention C3 (robust to a few late groups); D6, D7.
def derive_r03_coverage_end(rows_per_group_year: Mapping[Tuple[str, int], int],
                            groups: Tuple[str, ...], is_events: bool) -> Derived:
    """Y_end: the last year in which at least half the given groups have at least 90% of their usual
    yearly rows.

    Rule: R3 (C3, D6, D7, owner ruling F2). The groups come in as an ARGUMENT: under leave one region
    out every group is tested, so the caller passes every group (split.groups_under_loro); the
    argument is named 'groups' (the LORO addendum renames the approved 'test_groups'). The rule never
    reads a split.
    Grid: a group's usual count is the median of its counts over every calendar year from its first to
    its last year with rows, zero-row years included (D7); a group qualifies in year Y when its count
    in Y is at least 90% of that median (C3); Y qualifies when at least half the groups qualify (C3).
    The years scanned run from the first to the last year with any row. Y_end is the last qualifying
    year. Events: the last year with any row. The counts are the JOINED rows: a valid label (D6) and
    the kept drivers present (F2), see count_valid_rows_per_group_year; the rule sees counts only,
    never a value.
    Returns Derived[int]; margins: the chosen year's share of qualifying groups against C3's share
    (grids); inputs: every group's median and the share in each scanned year. A group whose median is 0
    qualifies in every year by the formula; it is flagged 'zero_median:<group>'.
    Refuses: a count key whose group is not in the set, a negative count or a non-integer key; a group
    with no row at all; no year qualifies.
    """
    rule = "R3"
    listed = _group_set(groups, rule)
    counts: Dict[str, Dict[int, int]] = {g: {} for g in listed}
    for key, n in rows_per_group_year.items():
        try:
            group, year = key
        except (TypeError, ValueError):
            raise DeriveRefusal(rule, "count keys are (group, year) pairs, got %r" % (key,),
                                fix="pass {(group, year): count}")
        if group not in counts:
            raise DeriveRefusal(rule, "counts hold group %r, which is not in the group set" % (group,),
                                fix="pass counts over the given groups only")
        year = _int(year, "the year of %r" % (key,), rule)
        n = _int(n, "the count of %r" % (key,), rule)
        if n < 0:
            raise DeriveRefusal(rule, "count of %r is negative (%d)" % (key, n), fix="pass row counts")
        counts[group][year] = counts[group].get(year, 0) + n
    empty = [g for g in listed if sum(counts[g].values()) == 0]
    if empty:
        raise DeriveRefusal(rule, "%d groups have no row at all, e.g. %s" % (len(empty), empty[:_SHOW]),
                            fix="every judged group needs rows (check the store or the group set)")
    with_rows = sorted({y for g in listed for y, n in counts[g].items() if n > 0})
    first, last = with_rows[0], with_rows[-1]
    inputs: Dict[str, Any] = {
        "groups": list(listed), "is_events": bool(is_events),
        "counted": "joined rows: a valid label (D6) and the kept drivers present (F2)",
        "rows_per_group_year": {g: {str(y): n for y, n in sorted(counts[g].items())} for g in listed}}
    hashes = {"rows_per_group_year_raw": sha256_of_json(
        sorted([str(g), int(y), int(n)] for g in listed for y, n in counts[g].items()))}
    if is_events:
        inputs["rule"] = "events: the last year with any row"
        return make_derived(rule, last, inputs, hashes)

    group_share = K.COVERAGE_GROUP_SHARE
    row_share = Fraction(repr(K.COVERAGE_ROW_SHARE))
    medians: Dict[str, float] = {}
    flags: List[str] = []
    for g in listed:
        years_g = [y for y, n in counts[g].items() if n > 0]
        span = range(min(years_g), max(years_g) + 1)
        medians[g] = float(np.median([counts[g].get(y, 0) for y in span]))
        if medians[g] == 0:
            flags.append("zero_median:" + g)
    shares: Dict[int, float] = {}
    chosen: List[int] = []
    needed = Fraction(repr(group_share)) * len(listed)
    for y in range(first, last + 1):
        qualifying = sum(1 for g in listed
                         if Fraction(counts[g].get(y, 0)) >= row_share * Fraction(repr(medians[g])))
        shares[y] = qualifying / len(listed)
        if qualifying >= needed:
            chosen.append(y)
    inputs["median_rows_per_group"] = medians
    inputs["qualifying_share_by_year"] = {str(y): s for y, s in shares.items()}
    inputs["constants"] = constants_used("C3.coverage_group_share", "C3.coverage_row_share")
    if not chosen:
        raise DeriveRefusal(rule, "no year has at least %s of the %d groups at %s of their usual rows "
                            "(best share %.3f)" % (group_share, len(listed), K.COVERAGE_ROW_SHARE,
                                                   max(shares.values())),
                            fix="check the store's coverage and the group set")
    y_end = chosen[-1]
    margins, more = borderline_flags(shares[y_end], {"C3.coverage_group_share": group_share})
    return make_derived(rule, y_end, inputs, hashes, margins, tuple(flags) + more)


# ===================================================================================================
# R4 first year
def _lag_years(lag: Any) -> int:
    """A lag in whole years, rounded up (R4): k steps of the column's own cadence (D22)."""
    rule = "R4"
    name = getattr(lag, "column", "<unnamed>")
    k = _int(getattr(lag, "steps", None), "the lag of %s" % name, rule)
    if k < 0:
        raise DeriveRefusal(rule, "column %s has a negative lag (%d)" % (name, k), fix="rerun R8")
    if k == 0:
        return 0
    kind, length, unit = _cadence_parts(getattr(lag, "column_cadence", None), "column %s" % name, rule)
    if kind == REGULAR and unit == MONTH and length:
        return -(-(k * length) // K.MONTHS_PER_YEAR)
    if kind == REGULAR and unit == YEAR and length:
        return k * length
    if kind == REGULAR and unit == DAY and length:
        return math.ceil(Fraction(k * length) / Fraction(repr(K.DAYS_PER_YEAR)))
    if kind == COMPOSITE and length:
        # from the first composite of a year, k composites back: whole years of composites
        per_year = getattr(lag.column_cadence, "composites_per_year", None)
        per_year = (_int(per_year, "composites_per_year of %s" % name, rule) if per_year is not None
                    else -(-_days_in_common_year() // length))
        return -(-k // per_year)
    raise DeriveRefusal(rule, "column %s: a %s cadence has no lag in years" % (name, kind),
                        fix="R8 lags regular and composite columns only")


def _days_in_common_year() -> int:
    return _dt.date(3, 1, 1).toordinal() - _dt.date(2, 1, 1).toordinal()


# Provenance: plan 2.1 R4; C4; D8 (the first year of the target table, read only as a lag source); owner
# ruling J5, 2026-10-05 (OWNER_RULINGS_2026-10-05.md section J: "R4 counts from the first year of the DRIVER
# stores (the lag sources), not the target's first year, so a lagged column never reads a year the store
# does not have"), which rules on the proposed signature's OWNER DECISION about "first data year".
def derive_r04_first_year(first_data_year: int, lags: Mapping[str, Any]) -> Derived:
    """Y0: the first data year plus the largest computed lag, rounded up to whole years.

    Rule: R4 (C4, D8, owner ruling J5). first_data_year is the first year of the DRIVER stores the lag
    sources read (J5), never before the target's first year: derive_all passes the latest first year
    among the stores that hold a lag source (a kept column whose R8 lag is above 0), measured on the
    target's rows, or the target's first year when no column has a lag (_r04_first_data_year in
    orchestrate.py). So a lagged column never reads a year before its store's first year. (D8's
    old reading, the first year of the target table, is what J5 replaces; the two agree when every
    lag-source store starts in the target's first year.) derive_all passes R8's lags with one J5
    addition (orchestrate._r04_lags): a column whose facts declare derived_from and the operation
    'lag k=<k> unit=<unit>' reads its parent k steps further back than its R8 lag says, so its lag here
    is R8's plus k (in its own steps). Each lag is counted in its column's own
    steps (D22) and turned into whole years, rounded up: k months -> ceil(k / months-per-year); k years
    -> k; k composites -> ceil(k / composites per year); k N-day steps -> ceil(k x N / 365.25) (C6's year
    length). Only lag sources count (C4): a column with a lag of 0, or one that starts late inside its
    store, does not move Y0 (R30 handles it); the history block does not count.
    Returns Derived[int]; inputs record every column's lag in steps and in years and the column(s)
    that set the maximum. An empty lag map gives Y0 = the first data year, flagged 'no_lag_sources'.
    Refuses: a lag map key that differs from its Lag's column; a negative lag; a lag on a cadence
    without steps. (The refusal of an empty map while kept columns exist needs the kept-column list,
    which this signature does not carry: check_r08_covers_kept_columns makes it, and derive_all
    calls it before this rule.)
    """
    rule = "R4"
    first = _int(first_data_year, "first_data_year", rule)
    per_column: Dict[str, Dict[str, int]] = {}
    for name in sorted(lags):
        lag = lags[name]
        if getattr(lag, "column", None) != name:
            raise DeriveRefusal(rule, "lag map key %r holds the lag of %r" % (name, getattr(
                lag, "column", None)), fix="key each lag by its column")
        per_column[name] = {"steps": _int(lag.steps, "the lag of %s" % name, rule),
                            "years": _lag_years(lag),
                            "cadence": _fact_dict(getattr(lag, "column_cadence", None),
                                                  CADENCE_FIELDS)}
    flags: Tuple[str, ...] = ()
    if per_column:
        largest = max(v["years"] for v in per_column.values())
        setters = [n for n, v in per_column.items() if v["years"] == largest]
    else:
        largest, setters, flags = 0, [], ("no_lag_sources",)
    inputs = {"first_data_year": first, "lags": per_column, "largest_lag_years": largest,
              "set_by": setters,
              "constants": constants_used("C4.first_year_from_lag_sources_only",
                                          "C6.months_per_year", "C6.days_per_year")}
    return make_derived(rule, first + largest, inputs, flags=flags)


# Provenance: plan 2.1 R4 ("R8 must run first"); the approved R4 refusal "an empty lag map when kept
# columns exist", which needs the kept-column list derive_r04_first_year's signature does not carry.
def check_r08_covers_kept_columns(kept_columns: Tuple[str, ...], r08: Derived) -> None:
    """R4's guard: the lag map R4 reads is R8's outcome over EXACTLY the kept columns.

    Rule: R4 (its refusal of an empty lag map while kept columns exist: R8 must run first). derive_all
    calls it with the kept columns (after verdicts) right before derive_r04_first_year. Every kept
    column must be one R8 handled: lagged (in R8's value) or listed as static, epoch or irregular in
    R8's inputs; and R8 must have handled no column that is not kept (a lag of a dropped column would
    move Y0). So an empty lag map passes only when every kept column is static, epoch or irregular (R4
    then flags 'no_lag_sources').
    Returns None. Refuses: r08 that is not R8's Derived; kept columns that are not a tuple of distinct
    non-empty names; a kept column R8 did not handle; a column R8 handled that is not kept.
    """
    rule = "R4"
    if not isinstance(r08, Derived) or r08.rule_id != "R8":
        raise DeriveRefusal(rule, "the lag map must come from R8's Derived, got %r"
                            % (type(r08).__name__,), fix="run derive_r08_feature_lags first")
    if isinstance(kept_columns, str) or not isinstance(kept_columns, (tuple, list)):
        raise DeriveRefusal(rule, "kept columns must be a tuple of names, got %r" % (kept_columns,),
                            fix="pass the kept columns after verdicts")
    kept = tuple(kept_columns)
    if any(not isinstance(c, str) or not c for c in kept) or len(set(kept)) != len(kept):
        raise DeriveRefusal(rule, "kept columns must be distinct non-empty names",
                            fix="pass the kept columns after verdicts")
    handled = set(r08.value)
    for listed in NO_LAG_KINDS:
        handled.update(r08.inputs.get(listed, ()))
    missing = sorted(set(kept) - handled)
    if missing:
        raise DeriveRefusal(rule, "R8 did not handle %d kept columns, e.g. %s: the lag map %s"
                            % (len(missing), missing[:_SHOW], "is empty" if not r08.value
                               else "is not R8's over the kept columns"),
                            fix="R8 must run first, on the kept columns")
    extra = sorted(handled - set(kept))
    if extra:
        raise DeriveRefusal(rule, "R8 handled %d columns that are not kept, e.g. %s; their lags would "
                            "move Y0" % (len(extra), extra[:_SHOW]),
                            fix="run R8 on the kept columns only")


# ===================================================================================================
# R5 - R7 windows
# Provenance: plan 2.1 R5; C1; C2; plan 3.3 (the five packages never reach the ladder).
def derive_r05_test_window(y0: int, y_end: int) -> Derived:
    """The test window: the last 4 years up to Y_end, with the short-record ladder.

    Rule: R5 (C1, C2). Normally C1's 4 test years and C2's 3 inner-score years, which need 4 + 3 + 1
    inner-fit year = 8 years from Y0 to Y_end. With fewer: first the inner score drops to 2 years
    (needs 7), then the test window to 3 years (needs 6); each step taken is flagged 'short record'.
    Returns Derived[TestWindowPlan]; margins: the years available against each ladder threshold.
    Refuses: fewer than 6 years from Y0 to Y_end (3 test + 2 inner score + 1 inner fit).
    """
    rule = "R5"
    y0, y_end = _int(y0, "y0", rule), _int(y_end, "y_end", rule)
    n = y_end - y0 + 1
    full = K.TEST_YEARS + K.INNER_SCORE_YEARS + K.INNER_FIT_MIN_YEARS
    step1 = K.TEST_YEARS + K.INNER_SCORE_YEARS_SHORT_RECORD + K.INNER_FIT_MIN_YEARS
    step2 = K.TEST_YEARS_SHORT_RECORD + K.INNER_SCORE_YEARS_SHORT_RECORD + K.INNER_FIT_MIN_YEARS
    inputs = {"y0": y0, "y_end": y_end, "years_available": n,
              "years_needed": {"full": full, "inner_score_short": step1, "test_short": step2},
              "constants": constants_used("C1.test_years", "C1.test_years_short_record",
                                          "C2.inner_score_years", "C2.inner_score_years_short_record",
                                          "C2.inner_fit_min_years")}
    if n < step2:
        raise DeriveRefusal(rule, "Y0 %d to Y_end %d holds %d years; the shortest record the ladder "
                            "allows is %d (%d test + %d inner score + %d inner fit)"
                            % (y0, y_end, n, step2, K.TEST_YEARS_SHORT_RECORD,
                               K.INNER_SCORE_YEARS_SHORT_RECORD, K.INNER_FIT_MIN_YEARS),
                            fix="the package is refused: it needs a longer record")
    ladder: List[str] = []
    test_n, score_n = K.TEST_YEARS, K.INNER_SCORE_YEARS
    if n < full:
        score_n = K.INNER_SCORE_YEARS_SHORT_RECORD
        ladder.append("%s: inner score %d" % (SHORT_RECORD, score_n))
    if n < step1:
        test_n = K.TEST_YEARS_SHORT_RECORD
        ladder.append("%s: test %d" % (SHORT_RECORD, test_n))
    plan = TestWindowPlan(test_years=tuple(range(y_end - test_n + 1, y_end + 1)),
                          inner_score_years=score_n, ladder_steps=tuple(ladder))
    margins, flags = borderline_flags(n, {"years_needed_full": full,
                                          "years_needed_inner_score_short": step1,
                                          "years_needed_test_short": step2})
    return make_derived(rule, plan, inputs, margins=margins, flags=tuple(ladder) + flags)


def _consecutive_years(years: Any, what: str, rule: str) -> Tuple[int, ...]:
    if isinstance(years, (str, bytes)) or not isinstance(years, Sequence):
        raise DeriveRefusal(rule, "%s must be a sequence of years, got %r" % (what, years),
                            fix="pass the R5 test years")
    out = tuple(_int(y, what, rule) for y in years)
    if not out:
        raise DeriveRefusal(rule, "%s is empty" % what, fix="pass the R5 test years")
    if any(b - a != 1 for a, b in zip(out, out[1:])):
        raise DeriveRefusal(rule, "%s %s are not consecutive years in order" % (what, list(out)),
                            fix="pass the R5 test years")
    return out


# Provenance: plan 2.1 R6.
def derive_r06_train_end(test_years: Tuple[int, ...]) -> Derived:
    """Donor train end: the year before the test window.

    Rule: R6. Every donor label and every router row is at or before this year (FitContext enforces).
    Returns Derived[int]. Refuses: test years that are empty or not consecutive (in order).
    """
    rule = "R6"
    years = _consecutive_years(test_years, "test years", rule)
    return make_derived(rule, years[0] - 1, {"test_years": list(years)})


# Provenance: plan 2.1 R7; C2.
def derive_r07_inner_windows(y0: int, y_end: int, plan: Any, train_end: int) -> Derived:
    """Inner windows: score = the years before the test window; fit = Y0 to the year before score.

    Rule: R7 (C2). Score = the plan's inner-score length (3, or 2 under the ladder) of years ending at
    the train end; fit = Y0 to the year before the score window.
    Returns Derived[Windows] with every window filled; margins: the inner-fit length against C2's
    one-year floor.
    Refuses: an inner-fit window shorter than 1 year; a train end that is not the year before the
    plan's test window; a test window that does not end at Y_end; an inner-score length below 1.
    """
    rule = "R7"
    y0, y_end = _int(y0, "y0", rule), _int(y_end, "y_end", rule)
    train_end = _int(train_end, "train_end", rule)
    test_years = _consecutive_years(getattr(plan, "test_years", None), "the plan's test years", rule)
    score_n = _int(getattr(plan, "inner_score_years", None), "the plan's inner_score_years", rule)
    if test_years[-1] != y_end:
        raise DeriveRefusal(rule, "the test window ends %d, not at Y_end %d" % (test_years[-1], y_end),
                            fix="pass R5's plan for this Y_end")
    if train_end != test_years[0] - 1:
        raise DeriveRefusal(rule, "train end %d is not the year before the test window (%d)"
                            % (train_end, test_years[0]), fix="pass R6's train end")
    if score_n < 1:
        raise DeriveRefusal(rule, "inner score length %d" % score_n, fix="pass R5's plan")
    score = tuple(range(train_end - score_n + 1, train_end + 1))
    fit = (y0, score[0] - 1)
    fit_years = fit[1] - fit[0] + 1
    inputs = {"y0": y0, "y_end": y_end, "test_years": list(test_years), "train_end": train_end,
              "inner_score_years": score_n, "constants": constants_used("C2.inner_fit_min_years")}
    if fit_years < K.INNER_FIT_MIN_YEARS:
        raise DeriveRefusal(rule, "the inner fit would run %d to %d (%d years); at least %d is needed"
                            % (fit[0], fit[1], fit_years, K.INNER_FIT_MIN_YEARS),
                            fix="the record is too short for the windows (R5 ladder)")
    windows = Windows(y0=y0, y_end=y_end, test_years=test_years, train_end=train_end,
                      inner_fit=fit, inner_score=score)
    margins, flags = borderline_flags(fit_years, {"C2.inner_fit_min_years": K.INNER_FIT_MIN_YEARS})
    return make_derived(rule, windows, inputs, margins=margins, flags=flags)


# ===================================================================================================
# R8 feature lags
def _window_record(window: Any) -> Optional[Dict[str, Any]]:
    out = _fact_dict(window, ("length", "unit", "align", "max_length", "fact_status"))
    if out is not None:
        for field in ("reach_after_max", "reach_before_max"):
            reach = getattr(window, field, None)
            if reach is not None:
                out[field] = {"value": float(reach.value), "unit": _value(reach.unit)}
    return out


def _facts_read(column: Any) -> Dict[str, Any]:
    return {"stamp": _value(getattr(column, "stamp", None)),
            "cadence": _fact_dict(getattr(column, "cadence", None), CADENCE_FIELDS),
            "window": _window_record(getattr(column, "window", None)),
            "fact_status": _value(getattr(column, "fact_status", None)),
            "co_measured_with_target": getattr(column, "co_measured_with_target", None)}


def _as_cadence(cadence: Any, what: str, rule: str) -> Cadence:
    """Any cadence (the approved shape, the store catalog's {kind, length, unit} form) as the approved
    Cadence, so a Lag written to derived.json holds the approved shape."""
    if isinstance(cadence, Cadence):
        return cadence
    kind, length, unit = _cadence_parts(cadence, what, rule)
    try:
        kind_enum = CadenceKind(kind)
        unit_enum = StepUnit(unit) if unit is not None else None
    except ValueError:
        raise DeriveRefusal(rule, "%s has an unknown cadence %r / %r" % (what, kind, unit),
                            fix="declare the cadence fact (plan 1.3)")
    if kind_enum == CadenceKind.COMPOSITE_OF_YEAR:
        per_year = getattr(cadence, "composites_per_year", None)
        return Cadence(kind=kind_enum, composites_per_year=(None if per_year is None else
                                                            _int(per_year, what, rule)),
                       composite_days=length)
    if kind_enum == CadenceKind.REGULAR:
        return Cadence(kind=kind_enum, length=length, unit=unit_enum)
    return Cadence(kind=kind_enum)


def _fact_dict(obj: Any, names: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    out = {}
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            out[name] = _value(value)
    return out


# Provenance: plan 2.1 R8 (see timing.compute_lag for the ruled cases); 5 G-LAG.
def derive_r08_feature_lags(columns: Mapping[str, Any], target: Any, target_cadence: Any) -> Derived:
    """One computed lag for every kept, time-varying non-key column.

    Rule: R8 (G-LAG; D22-D25 through timing). Computes timing.compute_lag's lag for every given column
    that has steps to lag by; nothing types a lag. The lag is built from ONE timing.lag_trace call per
    column (compute_lag is lag_trace's steps and floor reason with the column's cadence; a unit test
    keeps the two equal). Columns without steps get no lag and are listed by kind in the inputs: a
    static column under 'static'; an epoch column under 'epoch' (it enters through its freeze epoch,
    R9, and G-EPOCH checks its 'freeze' verdict); an irregular (event-dated) column under 'irregular'
    (it is joined as of each row's issue date). Inputs record, per lagged column, the facts read
    (stamp, window with its reach facts, cadence, co_measured_with_target, the target's computed_from)
    and timing.lag_trace's record (content lag, per-reference maxima and where they are reached, the
    floor reason, unanswered facts). A column whose floor fact is unanswered is flagged
    'unanswered:<column>:<fact>' (G-FACTS blocks it at the headline).
    Returns Derived[{column: Lag}]; each Lag has compute_lag's steps and floor reason, with its column
    cadence written in the approved Cadence shape (a store catalog's composite {length, unit: day}
    becomes composite_days).
    Refuses: a map key that differs from its column's name; any column compute_lag refuses (unknown
    window without a signed bound, a step that does not hold the target's step, an unknown target
    window, ...).
    """
    rule = "R8"
    lags: Dict[str, Lag] = {}
    records: Dict[str, Any] = {}
    no_lag: Dict[str, List[str]] = {listed: [] for listed in NO_LAG_KINDS}
    flags: List[str] = []
    for name in sorted(columns):
        column = columns[name]
        if getattr(column, "name", None) != name:
            raise DeriveRefusal(rule, "column map key %r holds the facts of %r"
                                % (name, getattr(column, "name", None)), fix="key facts by name")
        kind = _value(getattr(getattr(column, "cadence", None), "kind", None))
        if kind in NO_LAG_KINDS:
            no_lag[kind].append(name)
            continue
        trace = timing.lag_trace(column, target, target_cadence)
        lags[name] = Lag(column=trace.column, steps=trace.steps,
                         column_cadence=_as_cadence(getattr(column, "cadence", None),
                                                    "column %s" % name, rule),
                         floor_reason=trace.floor_reason)
        record = _facts_read(column)
        record.update({"steps": trace.steps, "content_steps": trace.content_steps,
                       "nowcast_steps": trace.nowcast_steps, "issue_steps": trace.issue_steps,
                       "worst_nowcast_position": trace.worst_nowcast_position,
                       "worst_issue_position": trace.worst_issue_position,
                       "positions": trace.positions, "floor_reason": trace.floor_reason,
                       "unanswered": list(trace.unanswered)})
        records[name] = record
        flags.extend("unanswered:%s:%s" % (name, fact) for fact in trace.unanswered)
    computed_from = getattr(target, "computed_from", None) or ()
    inputs = {"columns": records, **no_lag,
              "target": {"name": getattr(target, "name", None),
                         "computed_from": [computed_from] if isinstance(computed_from, str)
                         else list(computed_from),
                         "stamp": _value(getattr(target, "stamp", None)),
                         "window": _window_record(getattr(target, "window", None))},
              "target_cadence": _fact_dict(target_cadence, CADENCE_FIELDS)}
    return make_derived(rule, lags, inputs, flags=tuple(flags))


# ===================================================================================================
# R10 leads
# Provenance: plan 2.1 R10; C6; owner ruling I1 (2026-10-05: 6 and 12 months plus the nowcast, replacing
# Q41 a's 1/3/6/12); plan 3.2 (annual: 6 and 12 months merge into 1 year).
def derive_r10_leads(season: Any, is_events: bool) -> Derived:
    """Leads: the C6.lead_months leads (6 and 12 months, owner ruling I1) in the data's own step, rounded
    half up, merged when equal.

    Rule: R10 (C6). Grids: steps = months x steps_per_year / months-per-year, computed exactly and
    rounded half up (monthly: 6 and 12; annual: both round to 1 year and merge); the "under one step"
    test comes after rounding, so a lead that rounds to 0 is not run and is listed as not supplied; leads
    that round to the same step are merged (merged lists every lead that took more than one requested
    month). Events: days = months x 365.25 / months-per-year, rounded half up (183, 365). Lead 0 always
    runs as the contract and is never listed.
    Returns Derived[LeadPlan]; inputs record the exact value before rounding per requested month.
    Refuses: a grid with steps_per_year missing or below 1; an event season key on a grid or a grid key
    on events; a lead rounding rule other than half up in the engine constants.
    """
    rule = "R10"
    _require_half_up()
    kind = _value(getattr(season, "kind", None))
    spy = getattr(season, "steps_per_year", None)
    if bool(is_events) != (kind == SeasonKeyKind.EVENT_MONTH.value):
        raise DeriveRefusal(rule, "season key %r does not match is_events=%r" % (kind, is_events),
                            fix="pass R2's outcome and R1's events flag")
    months = tuple(_int(m, "requested lead", rule) for m in K.LEAD_MONTHS)
    exact: Dict[int, Fraction] = {}
    if is_events:
        unit = LeadUnit.DAYS
        year_days = Fraction(repr(K.DAYS_PER_YEAR))
        for m in months:
            exact[m] = Fraction(m) * year_days / K.MONTHS_PER_YEAR
    else:
        if spy is None:
            raise DeriveRefusal(rule, "a grid needs steps_per_year (R2)", fix="pass R2's outcome")
        spy = _int(spy, "steps_per_year", rule)
        if spy < 1:
            raise DeriveRefusal(rule, "steps_per_year is %d" % spy, fix="pass R2's outcome")
        unit = LeadUnit.STEPS
        for m in months:
            exact[m] = Fraction(m * spy, K.MONTHS_PER_YEAR)
    by_lead: Dict[int, List[int]] = {}
    not_supplied: List[int] = []
    for m in months:
        lead = _round_half_up(exact[m])
        if lead < 1:
            not_supplied.append(m)
        else:
            by_lead.setdefault(lead, []).append(m)
    leads = tuple(sorted(by_lead))
    merged = {lead: tuple(ms) for lead, ms in sorted(by_lead.items()) if len(ms) > 1}
    plan = LeadPlan(requested_months=months, leads=leads, lead_unit=unit, merged=merged,
                    not_supplied=tuple(not_supplied), contract_lead_zero=bool(K.LEAD_ZERO_CONTRACT))
    inputs = {"season_key": _value(kind), "steps_per_year": spy if not is_events else None,
              "is_events": bool(is_events),
              "before_rounding": {str(m): "%s/%s" % (v.numerator, v.denominator)
                                  for m, v in exact.items()},
              "constants": constants_used("C6.lead_months", "C6.months_per_year", "C6.days_per_year",
                                          "C6.lead_rounding", "C6.lead_zero_contract")}
    flags = tuple("merged:%d<-%s" % (lead, "+".join(str(m) for m in ms)) for lead, ms in merged.items())
    flags += tuple("not_supplied:%d" % m for m in not_supplied)
    return make_derived(rule, plan, inputs, flags=flags)


# ===================================================================================================
# R11 cuts
# Provenance: plan 2.1 R11 (see timing.fit_cut_step, timing.guard_cut_step, timing.cuts_for_leads).
def derive_r11_cuts(windows: Any, leads: Any, target_cadence: Any) -> Derived:
    """Both cuts for every lead, lead 0 included, written to derived.json.

    Rule: R11. Calls timing.cuts_for_leads; FitContext reads only these cuts, no module recomputes
    one. For grids the inputs also record the last step of the train end year and of the inner-fit end
    year (timing.year_last_step), the steps the cuts are counted back from.
    Returns Derived[{lead: CutPair}]. Refuses: whatever timing.cuts_for_leads refuses.
    """
    rule = "R11"
    cuts = timing.cuts_for_leads(windows, leads, target_cadence)
    inputs: Dict[str, Any] = {
        "windows": {name: getattr(windows, name, None) for name in
                    ("y0", "y_end", "test_years", "train_end", "inner_fit", "inner_score")},
        "leads": list(getattr(leads, "leads", ())), "lead_unit": _value(getattr(leads, "lead_unit", None)),
        "target_cadence": _fact_dict(target_cadence, CADENCE_FIELDS)}
    if _value(getattr(target_cadence, "kind", None)) != IRREGULAR:
        inputs["train_end_step"] = timing.year_last_step(windows.train_end, target_cadence)
        inputs["inner_fit_end_step"] = timing.year_last_step(windows.inner_fit[1], target_cadence)
    return make_derived(rule, dict(cuts), inputs)


# ===================================================================================================
# R9 freeze epochs
_DAYS = LeadUnit.DAYS.value


def _cut_pair_days(lead: Any, cut: Any, rule: str) -> Tuple[int, int]:
    """(fit cut day, guard cut day) of one lead's cut record: a CutDays, or an R11 CutPair of an
    event target (lead unit 'days': its cuts are days already). A step-unit CutPair is refused: a
    step is not a day (cut_days turns it into the last day of the cut step)."""
    if hasattr(cut, "fit_cut_day") and hasattr(cut, "guard_cut_day"):
        return (_int(cut.fit_cut_day, "the fit cut day of lead %r" % (lead,), rule),
                _int(cut.guard_cut_day, "the guard cut day of lead %r" % (lead,), rule))
    unit = _value(getattr(cut, "lead_unit", None))
    if unit == _DAYS and hasattr(cut, "fit_cut") and hasattr(cut, "guard_cut"):
        return (_int(cut.fit_cut, "the fit cut of lead %r" % (lead,), rule),
                _int(cut.guard_cut, "the guard cut of lead %r" % (lead,), rule))
    raise DeriveRefusal(rule, "lead %r: the cut is in %r, not days; a freeze epoch is a day, so R9 "
                        "compares it with the cut's last day" % (lead, unit),
                        fix="pass cut_days(R11 cuts, target cadence)")


# Provenance: plan 2.1 R9 (the freeze epoch is compared with a cut, D19: whole days, inclusive); R11's
# grid cuts are integer steps (D28). NOT an approved signature: the approved derive_r09_freeze_epochs
# takes the cuts but no calendar, so the day form is built here (flagged for the owner).
def cut_days(cuts: Mapping[int, Any], target_cadence: Any) -> Dict[int, Any]:
    """R11's cuts as days, the form R9 compares content epochs with: {lead: CutDays}.

    Grids: each cut step becomes its LAST calendar day (io.steps.step_bounds), so a content epoch on
    any day of the cut step is 'at or before the cut' (D19, inclusive). Events: the cuts are days
    already and are copied.
    Refuses: an empty cut map; a lead key that differs from its cut's lead; a step-unit cut on an
    irregular cadence or a day-unit cut on a grid; whatever step_bounds refuses.
    """
    from .shapes import CutDays                     # the record is engine-only (see shapes)
    rule = "R9"
    if not cuts:
        raise DeriveRefusal(rule, "no cut to convert", fix="pass R11's cuts")
    irregular = _value(getattr(target_cadence, "kind", None)) == IRREGULAR
    out: Dict[int, Any] = {}
    for lead in sorted(cuts):
        cut = cuts[lead]
        if _int(getattr(cut, "lead", None), "the lead of a cut", rule) != _int(lead, "a lead", rule):
            raise DeriveRefusal(rule, "cut map key %r holds the cut of lead %r"
                                % (lead, getattr(cut, "lead", None)), fix="pass R11's cuts")
        unit = _value(getattr(cut, "lead_unit", None))
        if (unit == _DAYS) != irregular:
            raise DeriveRefusal(rule, "lead %r: a %s cut on a %s target" % (
                lead, unit, "event" if irregular else "grid"), fix="pass R11's cuts of this target")
        if irregular:
            fit_day, guard_day = int(cut.fit_cut), int(cut.guard_cut)
        else:
            _, last = _steps.step_bounds(np.array([int(cut.fit_cut), int(cut.guard_cut)],
                                                  dtype=np.int64), target_cadence)
            fit_day, guard_day = int(last[0]), int(last[1])
        out[int(lead)] = CutDays(lead=int(lead), lead_unit=LeadUnit(unit), fit_cut_day=fit_day,
                                 guard_cut_day=guard_day)
    return out


# Provenance: plan 2.1 R9; plan 1.4 (freeze: the epoch is computed); D27 (each cut uses the epoch at or
# before its OWN cut, so derived.json holds both keys).
def derive_r09_freeze_epochs(freeze_epochs_available: Mapping[str, Sequence[int]],
                             cuts: Mapping[int, Any]) -> Derived:
    """The frozen epoch of every 'freeze' column at both cuts of every lead.

    Rule: R9 (D19, D27). Calls timing.freeze_epoch per (column, lead, cut kind): at the lead's FIT cut
    and at its GUARD cut, each the latest content epoch at or before that cut's own day (D27), so no
    value observed after a cut enters a fit at that cut. Both keys are always written, so
    io.apply_freezes reads the entry of the cut in use. Epochs and cuts are Day ordinals: the cuts
    come as cut_days(R11 cuts, target cadence) (a CutDays per lead), or as R11's own CutPairs on an
    event target, whose cuts are days.
    Returns Derived[{column: {lead: {cut kind: epoch Day}}}]: the approved {(column, lead, cut kind):
    epoch} map, nested so derived.json can hold it (its keys are text or whole numbers). An empty
    epoch map (no 'freeze' verdict) gives an empty value, flagged 'no_freeze_columns'.
    Refuses: an empty cut map; a column with no epoch, or an epoch that is not a whole day; a
    step-unit cut (pass cut_days); any column with no epoch at or before a cut (timing.freeze_epoch:
    the column cannot be frozen there and must be banned).
    """
    rule = "R9"
    if not cuts:
        raise DeriveRefusal(rule, "no cut: R9 needs R11's cuts", fix="pass cut_days(R11 cuts, cadence)")
    days = {int(lead): _cut_pair_days(lead, cuts[lead], rule) for lead in sorted(cuts)}
    value: Dict[str, Dict[int, Dict[str, int]]] = {}
    epochs_read: Dict[str, List[int]] = {}
    for column in sorted(freeze_epochs_available):
        if not isinstance(column, str) or not column:
            raise DeriveRefusal(rule, "freeze columns are named by text, got %r" % (column,),
                                fix="key the epochs by column name")
        epochs = [_int(e, "a content epoch of %s" % column, rule)
                  for e in freeze_epochs_available[column]]
        if not epochs:
            raise DeriveRefusal(rule, "column %s has no content epoch" % column,
                                fix="the store must list the column's content epochs")
        epochs_read[column] = sorted(set(epochs))
        value[column] = {}
        for lead, (fit_day, guard_day) in days.items():
            value[column][lead] = {FIT: timing.freeze_epoch(epochs, fit_day),
                                   GUARD: timing.freeze_epoch(epochs, guard_day)}
    inputs = {"content_epochs": epochs_read,
              "cut_days": {str(lead): {FIT: f, GUARD: g} for lead, (f, g) in days.items()},
              "rule": "latest content epoch at or before each cut's own last day (D19, D27)"}
    flags = () if value else ("no_freeze_columns",)
    return make_derived(rule, value, inputs, flags=flags)


# ===================================================================================================
# R22, R23: donor-row rules (label-only donor view, D16)
def _donor_y(donor: Any, rule: str) -> np.ndarray:
    """The donor view's labels, checked: the PICKED donor units (D16), valid labels only, one
    dimension, at least one row, one unit id, time and group per row, and every row dated at or before
    the view's cut (times and cut in one unit: steps on a grid, days for events)."""
    for field in ("y", "row_key_hash", "unit_scope", "cut", "cut_kind", "lead", "unit_ids", "times",
                  "group_of_row"):
        if not hasattr(donor, field):
            raise DeriveRefusal(rule, "the donor view has no %r (a label-only donor view, "
                                "vault.DonorLabels, is expected)" % field,
                                fix="pass LabelView.donor_labels(...)")
    scope = _value(donor.unit_scope)
    if scope != PICKED_SCOPE:
        raise DeriveRefusal(rule, "the donor view's unit scope is %r; the donor-row rules read the "
                            "picked donor units (D16)" % (scope,),
                            fix="pass the donor labels of the picked donor units")
    y = np.asarray(donor.y)
    if y.ndim != 1 or y.dtype.kind not in "iuf":
        raise DeriveRefusal(rule, "donor y must be a one-dimensional numeric array, got %s %s"
                            % (y.dtype, y.shape), fix="pass the donor view's labels")
    if y.size == 0:
        raise DeriveRefusal(rule, "the donor view holds no row", fix="check the donor units and cut")
    if y.dtype.kind == "f" and not np.isfinite(y).all():
        raise DeriveRefusal(rule, "donor y holds %d non-finite values; the donor view holds valid "
                            "labels only" % int((~np.isfinite(y)).sum()),
                            fix="build the donor view with LabelView.donor_labels")
    for field in ("unit_ids", "times", "group_of_row"):
        shape = np.asarray(getattr(donor, field)).shape
        if shape != y.shape:
            raise DeriveRefusal(rule, "donor %s has shape %s but y has %s: the view holds one entry "
                                "per donor row" % (field, shape, y.shape),
                                fix="build the donor view with LabelView.donor_labels")
    times = np.asarray(donor.times)
    if times.dtype.kind not in "iu":
        raise DeriveRefusal(rule, "donor times have dtype %s; they are whole steps (grids) or days "
                            "(events), the unit of the cut" % times.dtype,
                            fix="build the donor view with LabelView.donor_labels")
    cut = _int(donor.cut, "the donor view's cut", rule)
    late = times > cut
    if late.any():
        raise DeriveRefusal(rule, "%d donor rows are dated after the view's cut %d (latest %d); a donor "
                            "view holds rows at or before its cut (G-FITCUT)"
                            % (int(late.sum()), cut, int(times.max())),
                            fix="build the donor view with LabelView.donor_labels at the cut")
    return y


def _donor_record(donor: Any) -> Dict[str, Any]:
    groups = getattr(donor, "groups", ())
    return {"unit_scope": _value(donor.unit_scope), "cut": int(donor.cut),
            "cut_kind": _value(donor.cut_kind), "lead": int(donor.lead),
            "groups": list(groups) if groups is not None else [], "rows": int(np.asarray(donor.y).size)}


def _legal_range(legal_range: Any, rule: str) -> Tuple[float, float]:
    try:
        low, high = legal_range
    except (TypeError, ValueError):
        raise DeriveRefusal(rule, "the legal range must be (min, max), got %r" % (legal_range,),
                            fix="pass the target's cited legal range")
    for what, x in (("min", low), ("max", high)):
        if isinstance(x, (bool, np.bool_)) or not isinstance(x, (Real, np.number)):
            raise DeriveRefusal(rule, "legal range %s must be a number, got %r" % (what, x),
                                fix="pass the target's cited legal range")
    low, high = float(low), float(high)
    if math.isnan(low) or math.isnan(high) or not low < high:
        raise DeriveRefusal(rule, "the legal range [%r, %r] needs min < max" % (low, high),
                            fix="cite the product's documented valid range (plan 1.3)")
    return low, high


# Provenance: plan 2.1 R22 (plan 2.4); replaces the upper-bound guess at adaptation.py:341-350; Q36 a (a
# legal minimum below 0 gives identity only); D16.
def derive_r22_links(legal_range: Tuple[float, float], donor: Any) -> Derived:
    """The link set: identity always; log(y+c) and arcsine only when the facts and donor rows allow.

    Rule: R22, G-DONOR (D16). Identity always. log(y+c) when the legal minimum is >= 0, the donor rows
    hold a positive value, and donor y has more than 2 distinct values. Arcsine when the legal range is
    [0, UB] with UB finite (the cited fact, never guessed from data) and donor y has more than 2
    distinct values. Donor y is a label-only donor view at the NOWCAST fit cut (lead 0, cut kind fit)
    over the PICKED donor units (D16), which the caller passes in; its row-key hash is recorded, so the
    run can refuse a FitContext that hands out different rows.
    Returns Derived[links in the fixed order identity, log_c, arcsine]; margins: the distinct-value
    count against the more-than-2 threshold.
    Refuses: a legal range with min >= max (or not two numbers); a donor view whose scope is not
    'picked' (D16), that is not at lead 0's fit cut, that holds no row or a non-finite label, whose
    per-row arrays differ in length, or that holds a row dated after its cut.
    """
    rule = "R22"
    low, high = _legal_range(legal_range, rule)
    y = _donor_y(donor, rule)
    if _value(donor.cut_kind) != FIT or int(donor.lead) != 0:
        raise DeriveRefusal(rule, "the donor view is at lead %r, cut kind %r; R22 reads the nowcast "
                            "fit cut" % (donor.lead, _value(donor.cut_kind)),
                            fix="pass the donor labels at lead 0's fit cut")
    distinct = int(np.unique(y).size)
    positive = int((y > 0).sum())
    above = K.LINK_DISTINCT_VALUES_ABOVE
    enough = distinct > above
    links = [Link.IDENTITY]
    if low >= 0 and positive > 0 and enough:
        links.append(Link.LOG_C)
    if low == 0 and math.isfinite(high) and enough:
        links.append(Link.ARCSINE)
    inputs = {"legal_range": [low, high], "donor": _donor_record(donor),
              "donor_distinct_values": distinct, "donor_positive_rows": positive,
              "constants": constants_used("S2.link_distinct_values_above")}
    margins, flags = borderline_flags(distinct, {"S2.link_distinct_values_above": above})
    return make_derived(rule, tuple(links), inputs, {"donor_row_key_hash": str(donor.row_key_hash)},
                        margins, flags)


# Provenance: plan 2.4 R23; pm25_adaptation.py:572-577 (C_LOG = np.percentile(ypos, 1), ypos = finite
# positive donor y); D62 (numpy's default linear interpolation).
def c_from_donor_y(y: np.ndarray) -> Tuple[float, int]:
    """R23's formula, ONE implementation for the plan-time record (derive_r23_c_for_cut) and the run's
    layer.c_for_cut: c = the 1st percentile (S2) of the positive finite values of y, by numpy's
    default linear interpolation (D62).

    Returns (c, number of positive finite values); c > 0.
    Refuses: y that is not a one-dimensional numeric array; no positive finite value (log_c is then not
    in the link set, R22).
    """
    rule = "R23"
    arr = np.asarray(y)
    if arr.ndim != 1 or arr.dtype.kind not in "iuf":
        raise DeriveRefusal(rule, "y must be a one-dimensional numeric array, got %s %s"
                            % (arr.dtype, arr.shape), fix="pass the donor rows' labels")
    values = arr.astype(np.float64)
    positive = values[np.isfinite(values) & (values > 0)]
    if positive.size == 0:
        raise DeriveRefusal(rule, "donor y has no positive finite value; log(y+c) is not in the link "
                            "set (R22)", fix="do not build a log link for this target")
    c = float(np.percentile(positive, K.LOG_C_QUANTILE * 100.0))
    if not c > 0:
        raise DeriveRefusal(rule, "internal: c = %r is not positive" % c, fix="report this engine bug")
    return c, int(positive.size)


# Provenance: plan 2.4 R23 (F8: one c per cut); pm25_adaptation.py:572-577 (c = np.percentile(ypos, 1));
# D62 (linear interpolation), D63 option a (one c per LEAD cut, from donor rows at that lead's FIT cut).
def derive_r23_c_for_cut(donor: Any) -> Derived:
    """R23 plan-time record: c = the 1st percentile of positive donor-row y at or before one lead's
    fit cut.

    Rule: R23, G-DONOR (D16, D62, D63 a). The approved home of R23 is layer.c_for_cut (run time, on
    FitContext's DonorRows); this is its plan-time record, from the label-only donor view of the same
    rows, so derived.json shows c before the run. One c per lead cut, from the donor view at that
    lead's FIT cut over the picked donor units (the caller passes it); it serves that lead's decision
    or guard surface and its test pass. The value comes from c_from_donor_y, the one formula layer's
    c_for_cut must call too, and the run checks the two agree with check_r23_matches_run (same row-key
    hash, same c). Per-fold c (the donor-fold surface) is layer's alone: plan time has no folds.
    Written with the lead, cut kind and cut it belongs to and the donor view's row-key hash.
    Returns Derived[float] (c > 0).
    Refuses: a donor view whose scope is not 'picked' (D16), that is not at a fit cut (D63 a), that
    holds no row or a non-finite label, whose per-row arrays differ in length, or that holds a row
    dated after its cut; no positive donor value (log_c is then not in the link set).
    """
    rule = "R23"
    y = _donor_y(donor, rule)
    if _value(donor.cut_kind) != FIT:
        raise DeriveRefusal(rule, "the donor view is at a %r cut; one c per lead comes from that "
                            "lead's fit cut (D63 a)" % (_value(donor.cut_kind),),
                            fix="pass the donor labels at the lead's fit cut")
    c, positive_rows = c_from_donor_y(y)
    inputs = {"donor": _donor_record(donor), "positive_rows": positive_rows,
              "percentile_method": "linear (numpy default, D62)",
              "constants": constants_used("S2.log_c_quantile")}
    return make_derived(rule, c, inputs, {"donor_row_key_hash": str(donor.row_key_hash)})


# Provenance: plan 2.1 R22 ("the run refuses if FitContext.donor_rows at the same cut hands out different
# rows"), applied to R23's record the same way; plan 4.1 step 2 (the run refuses a derived.json that
# differs from the one plan showed).
def check_r23_matches_run(entry: Derived, lead: int, cut: int, run_c: float,
                          run_row_key_hash: str) -> None:
    """The run's check that layer.c_for_cut's c at one lead's fit cut is the plan-time R23 record.

    Rule: R23, G-DONOR. The run calls it at every lead cut where it computes c: the plan-time entry
    must be for the same lead and cut, be built from the same donor rows (row-key hash) and hold the
    same c. Both sides call c_from_donor_y on the same rows, so c is compared exactly.
    Returns None. Refuses: an entry that is not an R23 Derived; a different lead or cut; a different
    row-key hash; a different c.
    """
    rule = "R23"
    if not isinstance(entry, Derived) or entry.rule_id != rule:
        raise DeriveRefusal(rule, "the plan-time record must be R23's Derived, got %r"
                            % (type(entry).__name__,), fix="pass derived.json's R23 entry of the cut")
    donor = entry.inputs.get("donor", {})
    lead, cut = _int(lead, "lead", rule), _int(cut, "cut", rule)
    if (donor.get("lead"), donor.get("cut")) != (lead, cut):
        raise DeriveRefusal(rule, "the plan-time c is for lead %r, cut %r; the run asks lead %d, cut %d"
                            % (donor.get("lead"), donor.get("cut"), lead, cut),
                            fix="compare the entry of the same lead cut")
    planned_hash = entry.input_hashes.get("donor_row_key_hash")
    if planned_hash != str(run_row_key_hash):
        raise DeriveRefusal(rule, "the run's donor rows at lead %d, cut %d differ from plan's (row-key "
                            "hash %s, plan %s)" % (lead, cut, run_row_key_hash, planned_hash),
                            fix="the run refuses: FitContext must hand out the rows plan read")
    if not isinstance(run_c, (Real, np.floating)) or float(run_c) != float(entry.value):
        raise DeriveRefusal(rule, "the run's c at lead %d, cut %d is %r; plan's is %r"
                            % (lead, cut, run_c, entry.value),
                            fix="layer.c_for_cut must call c_from_donor_y on the same rows")


# ===================================================================================================
# R28 clip bounds
# Provenance: plan 2.4 R28, 5 G-CLIP ("the target's legal range, applied to every back-transformed
# prediction AND every baseline"); plan 1.3 (the range sets the links and the clip).
def derive_r28_clip_bounds(legal_range: Tuple[float, float]) -> Derived:
    """R28 plan-time record: the clip bounds, the target's cited legal range as (min, max); max may be
    infinite.

    Rule: R28, G-CLIP. The approved home of R28 is layer.clip_to_legal, which clips with the target's
    legal range; this record writes the same range to derived.json so plan shows the bounds the run
    clips to (both read the one cited fact). An infinite bound is written 'inf' / '-inf' and recorded
    as unbounded in the inputs.
    Returns Derived[(min, max)]. Refuses: a range that is not two numbers, holds NaN, or has min >= max.
    """
    rule = "R28"
    low, high = _legal_range(legal_range, rule)
    inputs = {"legal_range": [low, high], "lower_unbounded": math.isinf(low),
              "upper_unbounded": math.isinf(high)}
    return make_derived(rule, (low, high), inputs)
