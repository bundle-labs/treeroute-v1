"""Deforestation package: the feature script (plan 1.5). It builds the engineered lag columns of owner ruling
J2 (a) (= ruling K1) and the livestock hold columns of owner ruling L3 on the annual target. Nothing else: every
other tree column is read as it is from the features store (features/build_store.py) or the K store
(features/build_store_k.py), and the region router uses no context (plan 3.2).

Outputs (each declared in OUTPUTS with derived_from, operation, a backward-only window, reads_target):
  <parent>_lag1  for the 18 annual aggregates <base>_mean/_min/_max of the 6 LAG1_BASES (the SPEI block and
                 AMO): the parent's value of the SAME unit one calendar year earlier.
  <parent>_hold2021  for the 6 HOLD_PARENTS (aglw_*): the parent's value on rows up to HOLD_THROUGH_YEAR (2021);
                 on a row of a later year (2022, 2023) the SAME unit's 2021 value (calendar predecessor
                 year - 2021 steps back; a missing predecessor gives NaN, R30 decides). See THE LIVESTOCK HOLD.
  <parent>_lag2  for the LAG2_PARENTS (phenology_sos_doy): the parent's value of the SAME unit two calendar years
                 earlier. See THE PHENOLOGY LAG-2 COLUMN.
Why (OWNER_RULINGS_2026-10-05.md J2 a): "Columns missing in a test year (spei_01m/03m/06m/12m/24m, amo): keep
them through a dataset-owned engineered lag-12 column (derived_from the parent, operation lag 12); the raw
parent stays banned (incomplete)." On this annual target the 12-month lag is one step: the aggregate of the
previous calendar year. The parents' 2023 aggregates are empty (aggregate_time is D34-strict and the SPEI and
AMO series stop in 2022-12 / 2023-01), so each parent is banned 'incomplete' in ban.yaml and enters only
through its lag column, which reads 2022 for 2023.

Contract with the engine (treeroute/pipeline/data.py, 'feature script hook'): OUTPUTS {column: store facts in
the store-catalog schema} and build(frame, keys) -> DataFrame with exactly the OUTPUTS columns, one row per
frame row in the frame's order. frame holds the key columns, the engine's integer step and every
derived_from source (read from the features store: annual rows, so one step is one calendar year), with
sentinels masked and NO lag applied.

HOW THE FACTS ARE MADE (derived, never typed). Each output's facts come from its parent's entry in the
features store catalog that dataset.yaml includes (read through treeroute.package.load.load_includes, which
checks its sha256). The parent must be a calendar-year aggregate (cadence 1 year, stamp period_end, window
{1 year, backward}, no reach past its year end); anything else is refused (FeatureBuildError), never
guessed. A lag of one year moves the content to year t-1, so the output is declared over the two years
t-1..t (a backward superset whose forward edge is the row's own year end: R8 reads only the forward edge,
so the declaration can only raise a lag), keeping the parent's reach before its window start. R8 then gives
the output lag 0 on the annual target: the nowcast of year t reads year t-1's aggregate. dtype, units,
scope, legal range, product family, lineage, baseline period, absent groups and fact_status are the
parent's (fact_status stays 'unverified': the owner signs timing facts separately). observed_through is NOT
inherited: it is written in the parent's content time ('2022-12' for SPEI, '2023-01' for AMO), while in row
time the lag column's last observed value sits one year later (the 2023 row holds the 2022 aggregate), so a
copied value would mislead; the provenance text records the parent's value instead.

FIRST YEAR (R4, owner ruling J5). R4 counts Y0 from the driver stores' first year (2002) plus the largest look-back
of a kept column: R8's lag, plus k of a declared 'lag k unit=year' operation (J5). The lag-1 outputs declare
'lag k=1' and the lag-2 output 'lag k=2', so R4 sees their shifts: Y0 = 2004 (owner ruling N S17 a), from the
lag-2 columns (this script's phenology_sos_doy_lag2 and the K store's K5 trio). A row before the store's first
year + k reads a predecessor the store does not hold: R30 (NaN), never a silent value.

THE LIVESTOCK HOLD (owner ruling L3, OWNER_RULINGS_2026-10-05.md section L, 2026-10-06; review/PENDING_DEFO_L.md
item 5). The store's 2022 and 2023 aglw_* layers are not observations: they are the 2021 layer times INDIA's FAOSTAT
ratios, written for every region (panel store catalog provenance; observed_through 2021). L3: "Each package builds an
engineered column that holds the real 2021 layer for 2022-2023 (backward-only, declared). The raw aglw_* are banned
... The fixed columns are 'watch', lagged one year by R8, and the hold is disclosed." HOLD_THROUGH_YEAR must equal the
parent's store fact observed_through, or the script refuses. Facts: the parent's (dtype, units, cadence {1, year},
scope, stamp, window {1, year, backward}, legal range, product family, observed_through, fact_status) with
derived_from, reads_target false and operation 'hold_last_observed through_year=2021 unit=year'; fill_values and
near_sentinel_optout dropped (the frame arrives masked); the parent's reviewed_by/date (the owner's L1 c signature on
the store facts) are NOT copied: this script signs nothing, the derived facts stay 'assumed'. catalog.yaml declares
each hold column co_measured_with_target (as its parent, amended J3), so R8 lags it one year: the 2022 row reads the
2021 layer, the 2023 row reads the hold column's 2022 value, which is the 2021 layer again (two years old). The
declared window is the row's own year; a held row's content (2021) ends earlier, so the declaration can only raise a
lag. Not a 'lag k' operation (R4 counts only those; the hold reads back only after 2021, far from Y0). The raw
parents are banned 'incomplete' in ban.yaml (L3 names post_window_snapshot, which G-LINEAGE refuses as the source of
a feature-script output: OWNER item there).

THE PHENOLOGY LAG-2 COLUMN (owner ruling N S28 a, OWNER_RULINGS_2026-10-06.md: "defo phenology as an engineered
lag-2 column (like K5)"; FREEZE_SIGNOFF_SHEET.md S28; SIGNOFF_REVIEW.md S27/S28). The MCD12Q2 phenology of year y is
fitted on the years y-1, y and y+1 (MCD12Q2 User Guide V6.1), and the panel store catalog signs its window {1 year,
centred} + reach_after_max {1 year}: year y's content runs to the end of y+1. Read one year back (R8's lag 1 on
the raw column) it can hold data of the predicted year, so the raw column is 'conditional' (out) in ban.yaml; two
years back its content ends the day before the predicted year starts. Facts (_lag2_facts, derived, never typed):
the parent's value facts (units, scope, legal range, product family, lineage, absent groups, fact_status) with
derived_from, reads_target false, operation 'lag k=2 unit=year', stamp period_start and window {2 years, backward}
(+ the parent's reach_before_max, if any), as K5 declares the MOD44B lag-2 columns (features/build_store_k.py
k5_entry): content from 1 January t-2 to 31 December t-1, so R8 gives lag 0 and R4 counts 0 + 2. The engine's timing
helper treeroute.timing.content_interval checks, for every year of the engine's reference calendar
(timing.calendar REFERENCE_FIRST_YEAR, REFERENCE_YEARS: every calendar position) at import and for every row year
in build(), that the parent's content of year t-2 lies inside the declared content of year t and ends before year t
starts; anything else is refused (FeatureBuildError). The J2 (a) helper (_lag_facts) refuses this parent
(period_centre with a reach), hence the separate helper. observed_through is not inherited (content time vs row
time, as for the lag-1 columns). This script signs nothing: an S5 signature is written by
datasets/_tools/apply_signoff.py into the SIGNOFF block below.

TRAILING ONLY AND CALENDAR ONLY (G-CALENDAR). The look-back reads the SAME unit's predecessor exactly k steps
earlier through the engine's predecessor lookup (treeroute.io.steps.predecessor_index), never the adjacent
row; a unit without that predecessor gets NaN (R30), never a neighbour's value. No output reads the target,
fits a model or draws a random number.
"""
# Provenance: OWNER_RULINGS_2026-10-05.md J2 (a); review/proposed/defo_ban_proposed.yaml (the 18 parents banned
# 'incomplete': 2023 100% missing in D:/defo_features, measured 2026-10-05 from the parquet footers);
# datasets/ndvi/features/build.py LAG12_BASES (the same six bases on the monthly target);
# features/defo_features_store_catalog.yaml (the parents' facts); OWNER_RULINGS_2026-10-05.md L3 and
# review/PENDING_DEFO_L.md item 5 (the hold; datasets/pm25/features/build.py HOLD_PARENTS, the same columns monthly);
# OWNER_RULINGS_2026-10-06.md N S28 a and SIGNOFF_REVIEW.md S27/S28 (the phenology lag-2 column; MCD12Q2 User Guide
# V6.1, D:/treeroute/recreview_20261006/mcd12q2_ug_v61.txt:21, :55-56: fitted on the product year and the years
# before and after).

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from treeroute.io.steps import predecessor_index, step_bounds
from treeroute.package.load import load_dataset_file, load_includes
from treeroute.package.schema import Window
from treeroute.timing import content_interval
from treeroute.timing.calendar import REFERENCE_FIRST_YEAR, REFERENCE_YEARS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
# origin: owner ruling J2 (a): the columns missing in a test year (the SPEI block, AMO)
LAG1_BASES = ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
# origin: features/build_store.py STATS (defo_matrix.py:156-166: mean, min and max of every time-varying column)
STATS = ("mean", "min", "max")
LAG_STEPS = 1                 # one step of the annual target = the ruled 12 months
# origin: owner ruling L3: the yearly livestock columns whose 2022-2023 layers are not observations (store
# observed_through 2021)
HOLD_PARENTS = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD_THROUGH_YEAR = 2021
# origin: owner ruling N S28 a (OWNER_RULINGS_2026-10-06.md): defo phenology as an engineered lag-2 column (like K5,
# whose MOD44B lag is 2 years: features/build_store_k.py K5_LAG)
LAG2_PARENTS = ("phenology_sos_doy",)
LAG2_STEPS = 2
# the parent's owner signature is not copied onto a derived column (module docstring, THE LIVESTOCK HOLD)
_NOT_COPIED = ("fill_values", "near_sentinel_optout", "reviewed_by", "date", "provenance", "derived_from",
               "operation", "reads_target")
YEAR = {"kind": "regular", "length": 1, "unit": "year"}
YEAR_STEP = SimpleNamespace(**YEAR)
# observed_through is not inherited (module docstring: content time vs row time)
_INHERITED = ("dtype", "units", "product_family", "baseline_period")


class FeatureBuildError(Exception):
    """The feature script refuses (fail loudly; nothing is guessed)."""


def lag_column(parent):
    return "%s_lag%d" % (parent, LAG_STEPS)


def parents():
    return tuple("%s_%s" % (base, stat) for base in LAG1_BASES for stat in STATS)


def lag2_column(parent):
    return "%s_lag%d" % (parent, LAG2_STEPS)


def hold_column(parent):
    return "%s_hold%d" % (parent, HOLD_THROUGH_YEAR)


def _value(x):
    return getattr(x, "value", x)


def _source_facts():
    dataset = load_dataset_file(PACKAGE_ROOT)
    stores, _ = load_includes(PACKAGE_ROOT, dataset)
    out = {}
    for path, catalog in sorted(stores.items()):
        for column, facts in catalog.columns.items():
            if column in out:
                raise FeatureBuildError("column %r is declared by two included store catalogs" % column)
            out[column] = facts
    return out


def _lag_facts(parent, facts):
    cad = facts.cadence
    if (_value(cad.kind), cad.length, _value(cad.unit)) != ("regular", 1, "year"):
        raise FeatureBuildError("parent %r has cadence %s; the lag columns read calendar-year aggregates only"
                                % (parent, cad))
    w = facts.window
    if (_value(facts.stamp) != "period_end" or w is None or w.length != 1 or _value(w.unit) != "year"
            or _value(w.align) != "backward" or w.reach_after_max is not None or w.max_length is not None):
        raise FeatureBuildError("parent %r is not a calendar-year aggregate (stamp %r, window %s): its lag "
                                "column's window is not derived here" % (parent, _value(facts.stamp), w))
    out = {k: _value(getattr(facts, k)) for k in _INHERITED if getattr(facts, k, None) is not None}
    out.update({"cadence": dict(YEAR), "scope": _value(facts.scope), "stamp": "period_end",
                "fill_values": [], "fact_status": _value(facts.fact_status),
                "derived_from": [parent], "reads_target": False,
                "operation": "lag k=%d unit=year" % LAG_STEPS})
    if isinstance(out.get("baseline_period"), tuple):
        out["baseline_period"] = list(out["baseline_period"])
    window = {"length": 1 + LAG_STEPS, "unit": "year", "align": "backward"}
    if w.reach_before_max is not None:
        window["reach_before_max"] = w.reach_before_max.model_dump()
    out["window"] = window
    if facts.legal_range is not None:
        out["legal_range"] = [float(facts.legal_range[0]), float(facts.legal_range[1])]
    if facts.lineage is not None:
        out["lineage"] = facts.lineage.model_dump()
    if facts.absent_groups:
        out["absent_groups"] = dict(facts.absent_groups)
    out["provenance"] = ("owner ruling J2 (a): engineered lag column of %s, the calendar-year aggregate of year "
                         "t-1 (k = 1 year, same unit, calendar predecessor); the parent stays banned "
                         "(incomplete: its 2023 aggregate is empty); window declared {2 years, backward}: year "
                         "t-1's content inside a superset whose forward edge is year t's end; the parent is "
                         "observed through %s (its content time), so in row time this column's last observed "
                         "value sits one year later; features/build.py"
                         % (parent, _value(getattr(facts, "observed_through", None)) or "(not stated)"))
    return out


def _year_period(year):
    first, last = step_bounds(np.array([int(year)], dtype=np.int64), YEAR_STEP)
    return int(first[0]), int(last[0])


def check_lag2_window(parent, facts, declared, years):
    """For every row year t: the parent's content of year t - LAG2_STEPS lies inside the declared content of year t,
    and that content ends before year t starts (treeroute.timing.content_interval). Returns the number of checks."""
    pv = SimpleNamespace(name=parent, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
                         fact_status=facts.fact_status)
    lv = SimpleNamespace(name=lag2_column(parent), cadence=YEAR_STEP, stamp=declared["stamp"],
                         window=Window.model_validate(declared["window"]), fact_status=declared["fact_status"])
    n = 0
    for t in sorted({int(y) for y in years}):
        a0, a1 = content_interval(pv, _year_period(t - LAG2_STEPS))
        b0, b1 = content_interval(lv, _year_period(t))
        start_t = _year_period(t)[0]
        if not (b0 <= a0 and a1 <= b1 and b1 < start_t):
            raise FeatureBuildError("%s %d: the parent's content of %d (days %d-%d) is not inside the declared content "
                                    "(days %d-%d) ending before the year starts (day %d)"
                                    % (lag2_column(parent), t, t - LAG2_STEPS, a0, a1, b0, b1, start_t))
        n += 1
    return n


def _lag2_facts(parent, facts):
    """The facts of <parent>_lag2 (owner ruling N S28 a): the parent's value facts, declared {LAG2_STEPS years,
    backward} from period_start, checked against the parent's content on the reference calendar."""
    cad = facts.cadence
    if (_value(cad.kind), cad.length, _value(cad.unit)) != ("regular", 1, "year"):
        raise FeatureBuildError("lag-2 parent %r has cadence %s; the lag-2 column reads one value per calendar year"
                                % (parent, cad))
    if getattr(facts, "reads_target", None):
        raise FeatureBuildError("lag-2 parent %r reads the target" % parent)
    if facts.window is None or _value(facts.window.align) == "unknown":
        raise FeatureBuildError("lag-2 parent %r has no known window: its content cannot be placed" % parent)
    out = {"dtype": "float64", "units": facts.units, "cadence": dict(YEAR), "scope": _value(facts.scope),
           "stamp": "period_start", "fill_values": [], "fact_status": _value(facts.fact_status),
           "derived_from": [parent], "reads_target": False, "operation": "lag k=%d unit=year" % LAG2_STEPS}
    window = {"length": LAG2_STEPS, "unit": "year", "align": "backward"}
    if facts.window.reach_before_max is not None:
        window["reach_before_max"] = facts.window.reach_before_max.model_dump()
    out["window"] = window
    if facts.legal_range is not None:
        out["legal_range"] = [float(facts.legal_range[0]), float(facts.legal_range[1])]
    if getattr(facts, "product_family", None):
        out["product_family"] = facts.product_family
    if facts.lineage is not None:
        out["lineage"] = facts.lineage.model_dump()
    if facts.absent_groups:
        out["absent_groups"] = dict(facts.absent_groups)
    first = REFERENCE_FIRST_YEAR + LAG2_STEPS
    n = check_lag2_window(parent, facts, out, range(first, first + REFERENCE_YEARS))
    w = facts.window
    reach = (" + reach_after_max {%g, %s}" % (w.reach_after_max.value, _value(w.reach_after_max.unit))
             if w.reach_after_max is not None else "")
    out["provenance"] = (
        "owner ruling N S28 a (OWNER_RULINGS_2026-10-06.md: 'defo phenology as an engineered lag-2 column (like K5)'): "
        "the same unit's %s of calendar year t-%d (calendar predecessor, backward only; NaN when the store holds no "
        "such year); the parent (stamp %s, window {%g, %s, %s}%s) describes year t-%d up to its reach, inside the "
        "declared window {%d years backward} from period_start of year t, which ends the day before the predicted "
        "year starts (checked by treeroute.timing.content_interval on %d reference years at import and on every row "
        "year in build); the raw parent is conditional (out at lag 1: its reach runs one year past its year); the "
        "parent is observed through %s (its content time); features/build.py"
        % (parent, LAG2_STEPS, _value(facts.stamp), w.length, _value(w.unit), _value(w.align), reach, LAG2_STEPS,
           LAG2_STEPS, n, _value(getattr(facts, "observed_through", None)) or "(not stated)"))
    return out


def _hold_facts(parent, facts):
    """The facts of <parent>_hold2021: the parent's store facts, with derived_from and the hold operation (L3)."""
    cad = facts.cadence
    if (_value(cad.kind), cad.length, _value(cad.unit)) != ("regular", 1, "year"):
        raise FeatureBuildError("hold parent %r has cadence %s; the L3 hold is for yearly columns" % (parent, cad))
    if str(facts.observed_through) != str(HOLD_THROUGH_YEAR):
        raise FeatureBuildError("hold parent %r: store observed_through %r is not HOLD_THROUGH_YEAR %d; the hold "
                                "must keep the last observed year" % (parent, facts.observed_through, HOLD_THROUGH_YEAR))
    if getattr(facts, "reads_target", None):
        raise FeatureBuildError("hold parent %r reads the target" % parent)
    out = facts.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    for field in _NOT_COPIED:
        out.pop(field, None)
    if _value(facts.fact_status) == "verified":
        out["fact_status"] = "assumed"              # never carried as verified onto a derived column
    out.update({"derived_from": [parent], "reads_target": False,
                "operation": "hold_last_observed through_year=%d unit=year" % HOLD_THROUGH_YEAR})
    out["provenance"] = (
        "owner ruling L3 (OWNER_RULINGS_2026-10-05.md section L): %s on rows up to %d; on a row of a later year the "
        "same unit's %d value (calendar predecessor, backward only), so the 2022-2023 layers (the 2021 layer times "
        "India's FAOSTAT ratios) are never read; facts are the parent's store facts without its signature "
        "(reviewed_by/date not copied: this script signs nothing); features/build.py"
        % (parent, HOLD_THROUGH_YEAR, HOLD_THROUGH_YEAR))
    return out


def _declare(facts):
    out = {}
    for parent in parents() + HOLD_PARENTS + LAG2_PARENTS:
        if parent not in facts:
            raise FeatureBuildError("parent %r is in no store catalog dataset.yaml includes" % parent)
    for parent in parents():
        out[lag_column(parent)] = _lag_facts(parent, facts[parent])
    for parent in LAG2_PARENTS:
        out[lag2_column(parent)] = _lag2_facts(parent, facts[parent])
    for parent in HOLD_PARENTS:
        out[hold_column(parent)] = _hold_facts(parent, facts[parent])
    return out


_FACTS = _source_facts()
OUTPUTS = _declare(_FACTS)


def build(frame, keys):
    """Every OUTPUTS column on the frame's rows (see the module docstring)."""
    unit_col, step_col = keys["unit"], keys["step"]
    year_col = [c for c, part in keys["time"].items() if part == "year"]
    if len(year_col) != 1 or len(keys["time"]) != 1:
        raise FeatureBuildError("the catalog must hold one key_time column, with calendar part 'year', got %s"
                                % dict(keys["time"]))
    missing = [p for p in parents() + HOLD_PARENTS + LAG2_PARENTS if p not in frame.columns]
    if missing:
        raise FeatureBuildError("the frame lacks the sources %s" % missing[:5])
    steps = frame[step_col].to_numpy().astype(np.int64)
    years = frame[year_col[0]].to_numpy().astype(np.int64)
    if len(frame) and not np.array_equal(np.diff(steps), np.diff(years)):
        raise FeatureBuildError("the step column does not move with the calendar year (annual steps expected)")
    codes = pd.factorize(frame[unit_col].to_numpy(), sort=True)[0].astype(np.int64)
    prev = predecessor_index(codes, steps, LAG_STEPS)
    ok = prev >= 0
    out = {}
    for parent in parents():
        values = frame[parent].to_numpy(dtype=np.float64)
        lagged = np.full(len(frame), np.nan)
        lagged[ok] = values[prev[ok]]
        out[lag_column(parent)] = lagged
    # the lag-2 columns: the same unit's value two calendar years earlier (declared window re-checked on every row year)
    prev2 = predecessor_index(codes, steps, LAG2_STEPS)
    ok2 = prev2 >= 0
    for parent in LAG2_PARENTS:
        check_lag2_window(parent, _FACTS[parent], OUTPUTS[lag2_column(parent)], years)
        values = frame[parent].to_numpy(dtype=np.float64)
        lagged = np.full(len(frame), np.nan)
        lagged[ok2] = values[prev2[ok2]]
        out[lag2_column(parent)] = lagged
    # the L3 hold: rows up to 2021 the parent itself; a later row the same unit's 2021 row (backward only)
    after = years > HOLD_THROUGH_YEAR
    gaps = np.unique(years[after] - HOLD_THROUGH_YEAR)
    back = {int(gap): predecessor_index(codes, steps, int(gap)) for gap in gaps}
    for parent in HOLD_PARENTS:
        values = frame[parent].to_numpy(dtype=np.float64)
        held = np.where(after, np.nan, values)
        for gap, prev_g in back.items():
            rows = (years - HOLD_THROUGH_YEAR == gap) & (prev_g >= 0)
            held[rows] = values[prev_g[rows]]
        out[hold_column(parent)] = held
    return pd.DataFrame(out, index=frame.index, columns=list(OUTPUTS))

# >>> SIGNOFF BLOCK (written by datasets/_tools/apply_signoff.py; do not edit by hand) >>>
# The owner signed the composed timing facts of these outputs (FREEZE_SIGNOFF_SHEET.md S5): fact_status 'assumed' + reviewed_by
# owner + date, plan 1.3's spelling of a signed fact. Each entry: column -> (ruling id, date, rulings file).
# The parents' facts were signed first (S1-S4 or earlier rulings); a renamed or removed output fails
# loudly here (KeyError). Written by datasets/_tools/apply_signoff.py; edit the answers, not this block.
SIGNOFF_COLUMNS = {
    'V06_spei_12m_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V06_spei_12m_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'V06_spei_12m_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_buffalo_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_cattle_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_goats_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_horse_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_sheep_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_total_lsu_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'amo_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'amo_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'amo_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'phenology_sos_doy_lag2': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_01m_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_01m_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_01m_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_03m_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_03m_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_03m_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_06m_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_06m_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_06m_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_24m_max_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_24m_mean_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'spei_24m_min_lag1': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
}
for _signoff_column, (_signoff_ruling, _signoff_date, _signoff_file) in SIGNOFF_COLUMNS.items():
    _signoff_facts = OUTPUTS[_signoff_column]
    _signoff_facts.update({'fact_status': 'assumed', 'reviewed_by': 'owner', 'date': _signoff_date})
    _signoff_facts['provenance'] = '; '.join(x for x in (_signoff_facts.get('provenance'), 'signed by the owner %s (ruling %s, %s, FREEZE_SIGNOFF_SHEET.md S5)' % (_signoff_date, _signoff_ruling, _signoff_file)) if x)
del _signoff_column, _signoff_ruling, _signoff_date, _signoff_file, _signoff_facts
# <<< SIGNOFF BLOCK <<<
