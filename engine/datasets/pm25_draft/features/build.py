"""PM2.5 package: the feature script (plan 1.5). It makes the router context as shipped, the one engineered
tree column of the shipped feature list, and the six lag-12 columns of owner ruling J2 (a).

Outputs (each declared below with its store facts, so the engine's R8 lags it from facts, never by hand):
  ctx:month  router context: the calendar month of the row (1..12).            shipped CTX = ['month', ...]
  ctx:lat    router context: the unit's latitude (the panel's static lat).    shipped CTX = [..., 'lat']
  burn_lag1  tree feature:   GFED burned fraction of the SAME unit one month earlier (lag 1 of burn_frac:
             smoke is transported, pm25_architecture.py:178-181; shipped BURN_COLS = burn_frac, burn_lag1).
  <parent>_lag12 for the six parents of LAG12_PARENTS (spei_01m, spei_03m, spei_06m, V06_spei_12m, spei_24m,
             amo): the parent's value of the SAME unit exactly 12 calendar months earlier. Owner ruling J2 (a)
             (OWNER_RULINGS_2026-10-05.md): a column missing in a test year is kept through a dataset-owned
             engineered lag-12 column, derived_from the parent, operation lag 12; the raw parent stays banned
             (incomplete). The SPEI block ends 2022-12 and AMO 2023-01 (store facts observed_through), so the
             raw parents vanish in 2023; their lag-12 children read 2022 there and are complete.

Contract with the engine (treeroute/pipeline/data.py, 'feature script hook'):
    OUTPUTS: {column: its store facts, in the store-catalog schema (treeroute.package.schema.StoreColumn)}.
        The engine validates them and adds them to the package's store facts, so derive's R8 computes
        each column's lag from them (plan 1.5: "Every output column is declared: derived_from,
        operation, a backward-only window, reads_target").
    build(frame, keys) -> pandas.DataFrame
        frame  one row per (unit, step) the engine asks for, sorted by unit then step, holding the
               catalog's key columns, the engine's integer step (column keys['step']) and every source
               column that OUTPUTS' derived_from lists, with sentinels already masked and NO lag
               applied (plan 1.5: "The script gets a reader with sentinels already masked").
        keys   {'unit': <key_unit column>, 'group': <key_group column>, 'step': <step column>,
                'time': {<key_time column>: <calendar part>}}
        Returns exactly the OUTPUTS columns, one row per frame row, in the frame's order.

Trailing only (plan 1.5): burn_lag1 and the lag-12 columns read their source of the SAME unit exactly k steps
earlier through the engine's dense-grid predecessor lookup (G-CALENDAR: never a row shift); a missing
predecessor gives NaN (R30), never a neighbour's value. No column reads the target, fits a model or draws a
random number.

Every lag-k output's facts are COMPOSED from its parent's store facts, never typed (burn_lag1 with k = 1 from
burn_frac, the lag-12 columns with k = 12): for every month of the timing rules' reference calendar, the
content a lag-k value describes is timing.content_interval of the parent's period t-k (the parent's facts are
read from the store catalogs dataset.yaml includes, sha256-checked by treeroute.package.load.load_includes). The
output is declared stamp period_end, align backward, over the months that content and the row's own month span
(a superset: R8 reads only the forward edge, so the declaration can only raise a lag, never lower one), plus
reach_after_max only when the parent's content reaches past the row's month end. A parent with an unknown
window and no signed bound gives an output declared unknown too (R8 refuses both, G-LAG). Units, dtype, legal
range, scope, product family, lineage, absent groups, baseline period and fact_status are the parent's;
observed_through is the parent's moved k months later (the row of month m holds the parent's month m-k).

burn_lag1: burn_frac carries the MCD64A1 detection margin reach_after_max {1, month} (gfed_burn_schema_catalog.
yaml, ruling J1, the Q1 default, assumed), so its month t-1 content ends at month t's end: the composition gives
{2 months, backward} with no reach, and R8 gives burn_lag1 lag 0 (it holds month t-1). If that store reach
changes, burn_lag1's declared window follows it. burn_frac itself comes out at lag 1 on this target (the same
reach), so burn_lag1 holds the SAME value as the lagged burn_frac on every row: a duplicate column. OWNER
QUESTION (review/proposed/BAN_REVIEW_SUMMARY.md Q1, no default was written for it): keep the duplicate, move
burn_lag1 to month t-2, or drop it. Unchanged here until the owner rules.

ENGINE GAP (R4, ruling J5), recorded here because it touches these columns: R8 gives a lag-k output lag 0 (its
content already ends k months back), so R4 does not count the k months the column reads back from its parent. A
lag-12 value in Y0's first month reads the parent 12 months before Y0. With Y0 = 2004 (phenology_sos_doy's
2-year lag sets it; provisional, an owner decision) the lag-12 columns read 2003; with Y0 = 2003 (phenology held
out) they read 2002, the panel's first year. Either way nothing is read from a year the store lacks today, but only
by margin, not by rule: R4 counting derived_from + operation lags is an engine item.
The lag does not remove what a parent already holds from later years (SPEIbase's whole-record standardisation,
PSL AMO's whole-record detrend): disclosed in exceptions.yaml.
OWNER REVIEW (dataset science): the window wording and the context columns' facts are the agent's drafting.

THE LIVESTOCK HOLD (owner ruling L3, OWNER_RULINGS_2026-10-05.md section L, 2026-10-06). The store's 2022 and 2023
aglw_* layers are not observations: they are the 2021 layer times INDIA's FAOSTAT ratios, written for every region
(the panel store catalog's provenance; observed_through 2021). L3: "Each package builds an engineered column that
holds the real 2021 layer for 2022-2023 (backward-only, declared). The raw aglw_* are banned ... The fixed columns
are 'watch', lagged one year by R8, and the hold is disclosed." So for each of the six HOLD_PARENTS:
  <parent>_hold2021  the parent's value on rows of a year up to HOLD_THROUGH_YEAR (2021); on a row of a later year
             (2022, 2023) the SAME unit's value in HOLD_THROUGH_YEAR at the same calendar month (calendar
             predecessor 12 x (year - 2021) steps back; a missing predecessor gives NaN, R30 decides). Backward only:
             no row reads a later row. HOLD_THROUGH_YEAR must equal the parent's store fact observed_through, or the
             script refuses (fail loudly).
Its facts are the parent's (dtype, units, cadence {1, year}, scope, stamp, window, legal range, product family,
observed_through, lineage and fact_status), so R8 lags it one year on
this monthly target exactly as it lagged the parent: a row of 2023 reads the column's 2022 value, which is the real 2021
layer. The declared window is the parent's own year; a held row's content (2021) ends earlier, so the declaration can
only raise a lag, never lower one. operation 'hold_last_observed through_year=2021 unit=year' (not a lag k: R4 counts
only 'lag k=<k> unit=<unit>' operations, and a hold reads back only after 2021, far from Y0). On the rows of
2002-2021 the column equals its parent. The raw parents are banned 'incomplete' in ban.yaml (ruling L3 names
post_window_snapshot: see the ban.yaml header for why the reason word differs).
NOT SIGNED: the hold's facts drop the parent's reviewed_by and date. L1 (c) signs the parent aglw_* yearly facts;
the hold column and its operation are L3's, drafted by the agent, and L1 does not list them, so the column keeps
the parent's fact_status ('assumed') with no reviewer (defo's hold columns are written the same way). R8 reads
the window, cadence and stamp, not the reviewer, so the lag is the same either way.
"""
# Provenance: pm25_adaptation.py:195 (CTX = ["month", "lat"], the router context); pm25_architecture.py:81
# (BURN_COLS = burn_frac, burn_lag1), :178-181 (burn_lag1 = burn_frac one month earlier, per cell);
# engine/datasets/_stores/gfed_burn_schema_catalog.yaml (burn_frac's facts, the source of burn_lag1's);
# engine/datasets/_stores/monthly_panel_v170_schema_catalog.yaml (lat: static, degrees_north; the lag-12 parents);
# OWNER_RULINGS_2026-10-05.md J2 (a) (the lag-12 columns); engine/datasets/ndvi/features/build.py (the same
# composition rule for NDVI's driver lags, spelling 'lag k=<k> unit=month').

import re
from pathlib import Path

import numpy as np
import pandas as pd

from treeroute.io.steps import predecessor_index
from treeroute.package.load import load_dataset_file, load_includes
from treeroute.timing import TimingRefusal, content_interval
from treeroute.timing.calendar import REFERENCE_FIRST_YEAR, REFERENCE_YEARS, month_first_day, month_index

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
MONTHS = 12

# Owner ruling J2 (a): the columns missing in a test year, kept through a lag-12 child (the parents stay banned
# 'incomplete' in ban.yaml). V06_spei_12m is the panel's spei_12m.
LAG12_PARENTS = ("spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m", "amo")
LAG12_K = 12
BURN_PARENT, BURN_K = "burn_frac", 1
# Owner ruling L3: the yearly livestock columns whose 2022-2023 layers are not observations (store observed_through
# 2021); each is kept through <parent>_hold2021 (the raw parents are banned in ban.yaml).
# Owner ruling L1 (c) (OWNER_RULINGS_2026-10-05.md section L): the owner signs the windows of the engineered lag
# columns (here the six lag-12 columns of J2 a). Written in plan 1.3's spelling of a signed fact (the schema has no
# 'signed' fact_status): 'assumed' + reviewed_by + date. The signature covers the composed window.
# burn_lag1 is NOT signed: the list 'yes to all' answered (BAN_INSTALL_REPORT.md section 8 C) names the windows of
# the lag-12 columns on PM2.5, fire and NDVI and of defo's 18 lag-1 columns, not burn_lag1. Its window is composed
# from burn_frac's reach (signed, L1 a) and copies burn_frac's fact_status ('assumed') with no reviewer. OWNER
# QUESTION: does L1 (c) 'the windows of the engineered lag columns' cover burn_lag1 (itself open, Q1 duplicate)?
LAG12_SIGNATURE = {"fact_status": "assumed", "reviewed_by": "owner", "date": "2026-10-06"}
LAG12_SIGNATURE_NOTE = ("window signed by the owner 2026-10-06 (ruling L1 c: 'the windows of the engineered lag "
                        "columns'), written fact_status 'assumed' + reviewed_by owner + date")
HOLD_PARENTS = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD_THROUGH_YEAR = 2021


class FeatureBuildError(Exception):
    """The feature script refuses (fail loudly; nothing is guessed)."""


def lag_column(parent, k=LAG12_K):
    return "%s_lag%d" % (parent, k)


def hold_column(parent):
    return "%s_hold%d" % (parent, HOLD_THROUGH_YEAR)


# ---------------------------------------------------------------------------------------------------
# Composing a lag-k output's facts from its parent's (see the module docstring)
def _value(x):
    return getattr(x, "value", x)


class _Named(object):
    """A store-column fact object with a name, for the timing helpers' messages."""

    def __init__(self, name, facts):
        self.name = name
        self._facts = facts

    def __getattr__(self, item):
        return getattr(self._facts, item)


def _source_facts():
    dataset = load_dataset_file(PACKAGE_ROOT)
    stores, _ = load_includes(PACKAGE_ROOT, dataset)
    out = {}
    for _, catalog in sorted(stores.items()):
        for column, facts in catalog.columns.items():
            if column in out:
                raise FeatureBuildError("column %r is declared by two included store catalogs" % column)
            out[column] = facts
    return out


def _month_period(index):
    return month_first_day(index), month_first_day(index + 1) - 1


def _lag_window(name, facts, k):
    """(window dict, stamp) of the lag-k output of a monthly parent, composed over the reference calendar."""
    cad = facts.cadence
    if not (_value(cad.kind) == "regular" and cad.length == 1 and _value(cad.unit) == "month"):
        raise FeatureBuildError("lag parent %r has cadence %s; a lag in months needs a monthly parent" % (name, cad))
    view = _Named(name, facts)
    first_month = REFERENCE_FIRST_YEAR * MONTHS
    back, reach_months, month_ends, reach_days = 0, set(), True, []
    for m in range(first_month, first_month + REFERENCE_YEARS * MONTHS):
        first, last = content_interval(view, _month_period(m - k))
        back = max(back, m - month_index(first))
        reach_days.append(last - _month_period(m)[1])
        last_month = month_index(last)
        if last == _month_period(last_month)[1]:
            reach_months.add(last_month - m)
        else:
            month_ends = False
    window = {"length": back + 1, "unit": "month", "align": "backward"}
    if month_ends and len(reach_months) == 1:
        r = reach_months.pop()
        if r > 0:
            window["reach_after_max"] = {"value": r, "unit": "month"}
    elif max(reach_days) > 0:
        window["reach_after_max"] = {"value": max(reach_days), "unit": "day"}
    return window, "period_end"


def _shift_observed(name, value, k):
    """observed_through of a lag-k child: the parent's 'YYYY-MM' moved k months later (refuses any other form)."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", str(value))
    if m is None or not 1 <= int(m.group(2)) <= 12:
        raise FeatureBuildError("lag parent %r: observed_through %r is not a 'YYYY-MM' month; a monthly lag "
                                "cannot move it" % (name, value))
    index = int(m.group(1)) * MONTHS + int(m.group(2)) - 1 + k
    return "%04d-%02d" % (index // MONTHS, index % MONTHS + 1)


def _lag_facts(name, facts, k, provenance):
    out = {"dtype": facts.dtype, "units": facts.units,
           "cadence": {"kind": "regular", "length": 1, "unit": "month"},
           "scope": _value(facts.scope), "fact_status": _value(facts.fact_status),
           "reads_target": False, "derived_from": [name], "operation": "lag k=%d unit=month" % k}
    try:
        out["window"], out["stamp"] = _lag_window(name, facts, k)
    except TimingRefusal as err:
        if err.rule != "G-LAG":
            raise
        out["window"] = facts.window.model_dump(exclude_none=True)     # unknown stays unknown: R8 refuses both
        out["stamp"] = _value(facts.stamp)
    if facts.legal_range is not None:
        out["legal_range"] = [float(facts.legal_range[0]), float(facts.legal_range[1])]
    for field in ("product_family", "baseline_period"):
        v = getattr(facts, field, None)
        if v is not None:
            out[field] = list(v) if isinstance(v, tuple) else v
    if facts.observed_through is not None:
        out["observed_through"] = _shift_observed(name, facts.observed_through, k)
    if facts.lineage is not None:
        out["lineage"] = facts.lineage.model_dump()
    if facts.absent_groups:
        out["absent_groups"] = dict(facts.absent_groups)
    out["provenance"] = provenance
    return out


def _hold_facts(name, facts):
    """The facts of <parent>_hold2021: the parent's, with derived_from and the hold operation (ruling L3)."""
    cad = facts.cadence
    if not (_value(cad.kind) == "regular" and cad.length == 1 and _value(cad.unit) == "year"):
        raise FeatureBuildError("hold parent %r has cadence %s; the L3 hold is for yearly columns" % (name, cad))
    if str(facts.observed_through) != str(HOLD_THROUGH_YEAR):
        raise FeatureBuildError("hold parent %r: store observed_through %r is not HOLD_THROUGH_YEAR %d; the hold "
                                "must keep the last observed year" % (name, facts.observed_through, HOLD_THROUGH_YEAR))
    out = facts.model_dump(exclude_none=True, exclude_defaults=True)
    for field in ("fill_values", "near_sentinel_optout"):       # the frame arrives with sentinels masked
        out.pop(field, None)
    for field in ("reviewed_by", "date"):     # the owner signed the parent (L1 c), not this L3 column
        out.pop(field, None)
    out.update({"derived_from": [name], "reads_target": False,
                "operation": "hold_last_observed through_year=%d unit=year" % HOLD_THROUGH_YEAR})
    out["provenance"] = (
        "owner ruling L3 (OWNER_RULINGS_2026-10-05.md section L): %s on rows up to %d; on a row of a later year the "
        "same unit's %d value (calendar predecessor, backward only), so the 2022-2023 layers (the 2021 layer times "
        "India's FAOSTAT ratios) are never read; facts are the parent's without its owner signature (L1 c signs the parent; L1 does not list this column, so it is unsigned); "
        "features/build.py" % (name, HOLD_THROUGH_YEAR, HOLD_THROUGH_YEAR))
    return out


def _declare():
    facts = _source_facts()
    for parent in (BURN_PARENT,) + LAG12_PARENTS + HOLD_PARENTS:
        if parent not in facts:
            raise FeatureBuildError("lag parent %r is in no store catalog dataset.yaml includes" % parent)
    out = {
        "ctx:month": {
            "dtype": "float32", "units": "1",
            "cadence": {"kind": "regular", "length": 1, "unit": "month"},
            "scope": "global", "stamp": "period_end",
            "window": {"length": 1, "unit": "month", "align": "backward"},
            "legal_range": [1.0, 12.0],
            "derived_from": ["month"], "reads_target": False,
            "fact_status": "unverified",
            "provenance": "router context: the calendar month of the row, from the key_time column month "
                          "(pm25_adaptation.py:195, CTX = ['month', 'lat']); features/build.py",
        },
        "ctx:lat": {
            "dtype": "float32", "units": "degrees_north",
            "cadence": {"kind": "static"},
            "scope": "unit", "stamp": "period_end",
            "legal_range": [-90.0, 90.0],
            "derived_from": ["lat"], "reads_target": False,
            "product_family": "grid",
            "content_epoch": "timeless",    # ruling N2 (OWNER_RULINGS_2026-10-06.md N): a grid coordinate is a physical map
            "fact_status": "unverified",
            "provenance": "router context: the unit's latitude, the monthly panel's static lat "
                          "(pm25_adaptation.py:195, CTX = ['month', 'lat']); features/build.py",
        },
        "burn_lag1": _lag_facts(
            BURN_PARENT, facts[BURN_PARENT], BURN_K,
            "lag 1 (k = 1 month, same unit, dense-grid predecessor) of burn_frac (pm25_architecture.py:81, "
            "178-181; smoke is transported); facts composed from burn_frac's store facts (its one-month MCD64A1 "
            "reach, gfed_burn_schema_catalog.yaml, makes the window {2 months, backward}); features/build.py"),
    }
    for parent in LAG12_PARENTS:
        out[lag_column(parent)] = _lag_facts(
            parent, facts[parent], LAG12_K,
            "lag %d of %s (k = %d months, same unit, calendar predecessor; owner ruling J2 (a), "
            "OWNER_RULINGS_2026-10-05.md: kept through a lag-12 column, the parent stays banned 'incomplete'); "
            "facts composed from the parent's store facts, observed_through moved %d months; features/build.py; "
            "%s" % (LAG12_K, parent, LAG12_K, LAG12_K, LAG12_SIGNATURE_NOTE))
        out[lag_column(parent)].update(LAG12_SIGNATURE)
    for parent in HOLD_PARENTS:
        out[hold_column(parent)] = _hold_facts(parent, facts[parent])
    return out


OUTPUTS = _declare()


def build(frame, keys):
    """The outputs on the frame's rows (see the module docstring)."""
    unit_col, step_col = keys["unit"], keys["step"]
    month_col = [c for c, part in keys["time"].items() if part == "month"]
    if len(month_col) != 1:
        raise ValueError("the catalog must hold one key_time column with calendar part 'month', got %s"
                         % month_col)
    year_col = [c for c, part in keys["time"].items() if part == "year"]
    if len(year_col) != 1:
        raise ValueError("the catalog must hold one key_time column with calendar part 'year', got %s" % year_col)
    units = frame[unit_col].to_numpy()
    codes = pd.factorize(units, sort=True)[0].astype(np.int64)
    steps = frame[step_col].to_numpy().astype(np.int64)

    def lagged(source, k):
        prev = predecessor_index(codes, steps, k)
        values = frame[source].to_numpy(dtype=np.float64)
        out = np.full(len(frame), np.nan)
        ok = prev >= 0
        out[ok] = values[prev[ok]]
        return out.astype(np.float32)

    result = {
        "ctx:month": frame[month_col[0]].to_numpy().astype(np.float32),
        "ctx:lat": frame["lat"].to_numpy().astype(np.float32),
        "burn_lag1": lagged(BURN_PARENT, BURN_K),
    }
    for parent in LAG12_PARENTS:
        result[lag_column(parent)] = lagged(parent, LAG12_K)

    years = frame[year_col[0]].to_numpy().astype(np.int64)
    after = years > HOLD_THROUGH_YEAR
    gaps = np.unique(years[after] - HOLD_THROUGH_YEAR)

    def held(source):
        # rows up to 2021: the source itself; a later row: the same unit's 2021 row, same month (backward only)
        values = frame[source].to_numpy(dtype=np.float64)
        out = np.where(after, np.nan, values)
        for gap in gaps:
            rows = years - HOLD_THROUGH_YEAR == gap
            prev = predecessor_index(codes, steps, int(gap) * MONTHS)
            ok = rows & (prev >= 0)
            out[ok] = values[prev[ok]]
        return out

    for parent in HOLD_PARENTS:
        result[hold_column(parent)] = held(parent)
    return pd.DataFrame(result, index=frame.index)


# >>> SIGNOFF BLOCK (written by datasets/_tools/apply_signoff.py; do not edit by hand) >>>
# The owner signed the composed timing facts of these outputs (FREEZE_SIGNOFF_SHEET.md S5): fact_status 'assumed' + reviewed_by
# owner + date, plan 1.3's spelling of a signed fact. Each entry: column -> (ruling id, date, rulings file).
# The parents' facts were signed first (S1-S4 or earlier rulings); a renamed or removed output fails
# loudly here (KeyError). Written by datasets/_tools/apply_signoff.py; edit the answers, not this block.
SIGNOFF_COLUMNS = {
    'aglw_buffalo_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_cattle_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_goats_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_horse_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_sheep_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'aglw_total_lsu_hold2021': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:lat': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
    'ctx:month': ('N', '2026-10-06', 'OWNER_RULINGS_2026-10-06.md'),
}
for _signoff_column, (_signoff_ruling, _signoff_date, _signoff_file) in SIGNOFF_COLUMNS.items():
    _signoff_facts = OUTPUTS[_signoff_column]
    _signoff_facts.update({'fact_status': 'assumed', 'reviewed_by': 'owner', 'date': _signoff_date})
    _signoff_facts['provenance'] = '; '.join(x for x in (_signoff_facts.get('provenance'), 'signed by the owner %s (ruling %s, %s, FREEZE_SIGNOFF_SHEET.md S5)' % (_signoff_date, _signoff_ruling, _signoff_file)) if x)
del _signoff_column, _signoff_ruling, _signoff_date, _signoff_file, _signoff_facts
# <<< SIGNOFF BLOCK <<<
