"""Fire package: the feature script (plan 1.5). It makes the router context as shipped and the lag-12 columns of
owner rule J2 (a), and nothing else.

Outputs (each declared below with its store facts, so the engine's R8 lags it from facts, never by hand):
  ctx:month  router context: the calendar month of the row (1..12).           shipped CTX = ['month', ...]
  ctx:lat    router context: the unit's latitude (the panel's static lat).   shipped CTX = [..., 'lat']
  <base>_lag12 for the six bases of LAG12_BASES (owner rule J2 a, OWNER_RULINGS_2026-10-05.md section J): the
             base's value of the SAME unit 12 calendar months earlier. J2 (a): "Columns missing in a test year
             (spei_01m/03m/06m/12m/24m, amo): keep them through a dataset-owned engineered lag-12 column
             (derived_from the parent, operation lag 12); the raw parent stays banned (incomplete)." The six
             parents stay banned 'incomplete' in ban.yaml (a non-leak reason, so the engine's lineage check
             records them and does not refuse the outputs: treeroute/pipeline/data.py LINEAGE_LEAK_REASONS).

HOW THE LAG-12 FACTS ARE MADE (derived, never typed; the NDVI package's method, datasets/ndvi/features/build.py).
Each output's facts are COMPOSED from its source's facts in the store catalogs dataset.yaml includes (read
through treeroute.package.load.load_includes, which checks their sha256): for every month M of the timing rules'
reference calendar, the output's content is timing.content_interval of the source period M-12. The output is
declared stamp period_end, align backward, over the months from the start of that content to the end of M (a
superset), plus reach_after_max when the source's content reaches past the end of month M (none of the six
does: their windows are trailing). So R8 gives each output lag 0 (its newest content ends 12 months before the
row), and a bound the owner signs on a source flows into its output here. dtype, units, scope, legal range,
product family and observed_through are the source's; the operation names the lag.

TRAILING ONLY AND CALENDAR ONLY (G-CALENDAR). The look-back reads the SAME unit's row 12 calendar steps earlier
(the frame's own step column: monthly steps year x 12 + month); a missing row or value is missing (NaN, R30
decides), never a neighbouring row. A repeated (unit, step) is refused.

The fire-history columns (tslf_*, last_burn_*, n_burns_*, burn_rate_120mo, nbr*) are NOT made here. They are
target-derived (store facts: derived_from burned_frac, reads_target true), declared with role engineered in
catalog.yaml and read from the fire-history store. Their recompute from the target, strictly before each row,
is features/target_history.py (the G-DERIVED reference, and the builder for the store: ingest/build_history.py).
It is not an output of this script because the engine's feature hook refuses any output declared
reads_target and hands the script no labels (treeroute/pipeline/data.py, feature_outputs: 'the engine builds
the own-history block'); plan 1.5 allows target-derived event counts, years since the last event and
neighbour aggregates read through the label vault's as-of door, which the hook does not offer yet (engine item).

Contract with the engine (treeroute/pipeline/data.py, 'feature script hook'):
    OUTPUTS: {column: its store facts, in the store-catalog schema (treeroute.package.schema.StoreColumn)}.
    build(frame, keys) -> pandas.DataFrame
        frame  one row per (unit, step) the engine asks for, sorted by unit then step, holding the catalog's
               key columns, the engine's integer step (column keys['step']) and every source column that
               OUTPUTS' derived_from lists, with sentinels already masked and NO lag applied.
        keys   {'unit': <key_unit column>, 'group': <key_group column>, 'step': <step column>,
                'time': {<key_time column>: <calendar part>}}
        Returns exactly the OUTPUTS columns, one row per frame row, in the frame's order.

No column reads the target, fits a model or draws a random number. OWNER REVIEW (dataset science): the
context columns' facts are the agent's drafting, as for PM2.5; the lag-12 columns follow J2 (a) as written.

THE LIVESTOCK HOLD (owner ruling L3, OWNER_RULINGS_2026-10-05.md section L, 2026-10-06). The store's 2022 and 2023
aglw_* layers are not observations: they are the 2021 layer times INDIA's FAOSTAT ratios, written for every region
(the panel store catalog's provenance; observed_through 2021). L3: "Each package builds an engineered column that
holds the real 2021 layer for 2022-2023 (backward-only, declared). The raw aglw_* are banned ... The fixed columns
are 'watch', lagged one year by R8, and the hold is disclosed." So for each of the six HOLD_PARENTS:
  <parent>_hold2021  the parent's value on rows of a year up to HOLD_THROUGH_YEAR (2021); on a row of a later year
             the SAME unit's value in HOLD_THROUGH_YEAR at the same calendar month (calendar predecessor
             12 x (year - 2021) steps back, treeroute.io.steps.predecessor_index; a missing predecessor gives NaN,
             R30 decides). Backward only. HOLD_THROUGH_YEAR must equal the parent's store fact observed_through,
             or the script refuses (fail loudly).
Its facts are the parent's (dtype, units, cadence {1, year}, scope, stamp, window, legal range, product family,
observed_through, lineage and fact_status), so R8 lags it one year
exactly as it lagged the parent. The declared window is the parent's own year; a held row's content (2021) ends
earlier, so the declaration can only raise a lag. operation 'hold_last_observed through_year=2021 unit=year' (not a
lag k: R4 counts only 'lag k=<k> unit=<unit>' operations). The raw parents are banned 'incomplete' in ban.yaml
(ruling L3 names post_window_snapshot: see the ban.yaml header for why the reason word differs).
NOT SIGNED: the hold's facts drop the parent's reviewed_by and date. L1 (c) signs the parent aglw_* yearly facts;
the hold column and its operation are L3's, drafted by the agent, and L1 does not list them, so the column keeps
the parent's fact_status ('assumed') with no reviewer (defo's hold columns are written the same way). R8 reads
the window, cadence and stamp, not the reviewer, so the lag is the same either way.
On fire the test years end in 2022, whose rows read the 2021 layer through the one-year lag anyway: the hold
changes no value fire reads; it is built for one rule on every package.
The J2 (a) lag-12 columns carry the owner's signature of their composed window (ruling L1 c: 'the windows of the
engineered lag columns'): fact_status 'assumed' + reviewed_by owner + date 2026-10-06 (plan 1.3's spelling).
"""
# Provenance: fire_evt_arch.py:78 (CTX = ["month", "lat"], the router context of the shipped fire run);
# engine/datasets/_stores/monthly_panel_v170_schema_catalog.yaml (lat: static, degrees_north; the six bases);
# engine/datasets/pm25/features/build.py (the same two context columns, the same facts);
# OWNER_RULINGS_2026-10-05.md J2 (a) (the lag-12 columns); engine/datasets/ndvi/features/build.py (the facts
# composition: _composed_window, _inherited).

from pathlib import Path

import numpy as np
import pandas as pd

from treeroute.io.steps import predecessor_index
from treeroute.package.load import load_dataset_file, load_includes
from treeroute.timing import content_interval
from treeroute.timing.calendar import REFERENCE_FIRST_YEAR, REFERENCE_YEARS, month_first_day, month_index

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# origin: OWNER_RULINGS_2026-10-05.md J2 (a): spei_01m/03m/06m/12m/24m and amo (the panel's 12-month SPEI is
# V06_spei_12m). Order: the catalog's.
LAG12_BASES = ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
LAG12_STEPS = 12                 # J2 (a): "operation lag 12" (months; the target is monthly)
MONTHS = 12
_SHOW = 5


class FeatureBuildError(Exception):
    """The feature script refuses (fail loudly; nothing is guessed)."""


def lag_column(base, k):
    return "%s_lag%d" % (base, k)


LAG12_COLUMNS = tuple(lag_column(b, LAG12_STEPS) for b in LAG12_BASES)

# Owner ruling L3: the yearly livestock columns whose 2022-2023 layers are not observations (store observed_through
# 2021); each is kept through <parent>_hold2021 (the raw parents are banned in ban.yaml).
HOLD_PARENTS = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD_THROUGH_YEAR = 2021
# Owner ruling L1 (c): the owner signs the windows of the engineered lag columns (the six J2 a lag-12 columns),
# written in plan 1.3's spelling of a signed fact (the schema has no 'signed' fact_status).
LAG12_SIGNATURE = {"fact_status": "assumed", "reviewed_by": "owner", "date": "2026-10-06"}
LAG12_SIGNATURE_NOTE = ("window signed by the owner 2026-10-06 (ruling L1 c: 'the windows of the engineered lag "
                        "columns'), written fact_status 'assumed' + reviewed_by owner + date")


def hold_column(parent):
    return "%s_hold%d" % (parent, HOLD_THROUGH_YEAR)


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


def _held(frame, year_col, codes, steps, source):
    """<source>_hold2021 on the frame's rows: rows up to 2021 the source itself; a later row the same unit's 2021
    row at the same calendar month (backward only; a missing predecessor gives NaN)."""
    years = frame[year_col].to_numpy().astype(np.int64)
    after = years > HOLD_THROUGH_YEAR
    values = np.asarray(frame[source].to_numpy(), dtype=np.float64)
    out = np.where(after, np.nan, values)
    for gap in np.unique(years[after] - HOLD_THROUGH_YEAR):
        rows = years - HOLD_THROUGH_YEAR == gap
        prev = predecessor_index(codes, steps, int(gap) * MONTHS)
        ok = rows & (prev >= 0)
        out[ok] = values[prev[ok]]
    return out


# ---------------------------------------------------------------------------------------------------
# The source facts (store catalogs included by dataset.yaml, sha256-checked by load_includes)
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


class _Named(object):
    """A store-column fact object with a name, for the timing helpers' messages."""

    def __init__(self, name, facts):
        self.name = name
        self._facts = facts

    def __getattr__(self, item):
        return getattr(self._facts, item)


def _value(x):
    return getattr(x, "value", x)


def _month_period(index):
    return month_first_day(index), month_first_day(index + 1) - 1


def _reference_months():
    first = REFERENCE_FIRST_YEAR * MONTHS
    return range(first, first + REFERENCE_YEARS * MONTHS)


def _lag_window(name, facts, k):
    """(window dict, stamp) of the lag-k output of a monthly source (see the module docstring)."""
    cad = facts.cadence
    if not (_value(cad.kind) == "regular" and cad.length == 1 and _value(cad.unit) == "month"):
        raise FeatureBuildError("source %r has cadence %s; a lag of calendar months needs a monthly column"
                                % (name, cad))
    view = _Named(name, facts)
    reach_months, month_ends, reach_days = set(), True, []
    back = 0
    for m in _reference_months():
        first, last = content_interval(view, _month_period(m - k))     # refuses an unknown window (G-LAG)
        reach_days.append(last - _month_period(m)[1])
        last_month = month_index(last)
        if last == _month_period(last_month)[1]:
            reach_months.add(last_month - m)
        else:
            month_ends = False
        back = max(back, m - month_index(first))
    window = {"length": back + 1, "unit": "month", "align": "backward"}
    if month_ends and len(reach_months) == 1:
        r = reach_months.pop()
        if r > 0:
            window["reach_after_max"] = {"value": r, "unit": "month"}
    else:
        d = max(reach_days)
        if d > 0:
            window["reach_after_max"] = {"value": d, "unit": "day"}
    return window, "period_end"


def _lag_facts(name, facts, k):
    out = {"dtype": facts.dtype, "units": facts.units,
           "cadence": {"kind": "regular", "length": 1, "unit": "month"},
           "scope": _value(facts.scope), "fact_status": _value(facts.fact_status),
           "reads_target": False, "derived_from": [name]}
    for field in ("product_family", "observed_through", "baseline_period"):
        v = getattr(facts, field, None)
        if v is not None:
            out[field] = list(v) if isinstance(v, tuple) else v
    if facts.lineage is not None:
        out["lineage"] = facts.lineage.model_dump()
    if facts.absent_groups:
        out["absent_groups"] = dict(facts.absent_groups)
    if facts.legal_range is not None:
        out["legal_range"] = [float(facts.legal_range[0]), float(facts.legal_range[1])]
    out["window"], out["stamp"] = _lag_window(name, facts, k)
    out["operation"] = "lag k=%d unit=month" % k
    out["provenance"] = ("owner rule J2 (a) (OWNER_RULINGS_2026-10-05.md section J): the value of %s of the same "
                         "unit %d calendar months earlier (calendar predecessor; missing stays missing); the raw "
                         "parent stays banned (incomplete); features/build.py; %s" % (name, k, LAG12_SIGNATURE_NOTE))
    out.update(LAG12_SIGNATURE)
    return out


def _declare():
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
                          "(fire_evt_arch.py:78, CTX = ['month', 'lat']); features/build.py",
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
                          "(fire_evt_arch.py:78, CTX = ['month', 'lat']); features/build.py",
        },
    }
    facts = _source_facts()
    for base in LAG12_BASES:
        if base not in facts:
            raise FeatureBuildError("source %r is in no store catalog dataset.yaml includes" % base)
        out[lag_column(base, LAG12_STEPS)] = _lag_facts(base, facts[base], LAG12_STEPS)
    for parent in HOLD_PARENTS:
        if parent not in facts:
            raise FeatureBuildError("hold parent %r is in no store catalog dataset.yaml includes" % parent)
        out[hold_column(parent)] = _hold_facts(parent, facts[parent])
    return out


OUTPUTS = _declare()


# ---------------------------------------------------------------------------------------------------
# The build
def _month_of_step(steps):
    """Calendar month (1..12) of monthly steps year x 12 + month (io.steps.step_index, D28)."""
    steps = np.asarray(steps, dtype=np.int64)
    return steps - MONTHS * ((steps - 1) // MONTHS)


def _predecessor_rows(codes, steps, k):
    """Row index of the same unit's row k steps earlier, or -1 where the frame holds no such row."""
    index = pd.Index(pd.MultiIndex.from_arrays([codes, steps]))
    if index.has_duplicates:
        raise FeatureBuildError("the frame repeats a (unit, step)")
    return np.asarray(index.get_indexer(pd.MultiIndex.from_arrays([codes, steps - k])), dtype=np.int64)


def build(frame, keys):
    """Every OUTPUTS column on the frame's rows (see the module docstring)."""
    unit_col, step_col = keys["unit"], keys["step"]
    month_col = [c for c, part in keys["time"].items() if part == "month"]
    if len(month_col) != 1:
        raise FeatureBuildError("the catalog must hold one key_time column with calendar part 'month', got %s"
                                % month_col)
    year_col = [c for c, part in keys["time"].items() if part == "year"]
    if len(year_col) != 1:
        raise FeatureBuildError("the catalog must hold one key_time column with calendar part 'year', got %s"
                                % year_col)
    missing = [s for s in ("lat",) + LAG12_BASES + HOLD_PARENTS if s not in frame.columns]
    if missing:
        raise FeatureBuildError("the frame lacks the sources %s" % missing[:_SHOW])
    n = len(frame)
    steps = frame[step_col].to_numpy().astype(np.int64)
    months = frame[month_col[0]].to_numpy().astype(np.int64)
    if n and not np.array_equal(_month_of_step(steps), months):
        raise FeatureBuildError("the step column does not hold the rows' calendar months (monthly steps "
                                "year x 12 + month expected)")
    codes = pd.factorize(frame[unit_col].to_numpy(), sort=False)[0].astype(np.int64)
    if n and ((np.diff(codes) < 0).any() or ((np.diff(codes) == 0) & (np.diff(steps) <= 0)).any()):
        # sorted by unit (in order of first appearance) then strictly increasing step: no repeated (unit, step)
        raise FeatureBuildError("the frame is not sorted by unit then step, or repeats a (unit, step)")
    out = {
        "ctx:month": months.astype(np.float32),
        "ctx:lat": frame["lat"].to_numpy().astype(np.float32),
    }
    src = _predecessor_rows(codes, steps, LAG12_STEPS) if n else np.zeros(0, dtype=np.int64)
    ok = src >= 0
    for base in LAG12_BASES:
        column = lag_column(base, LAG12_STEPS)
        dtype = np.float32 if OUTPUTS[column]["dtype"] == "float32" else np.float64
        values = np.asarray(frame[base].to_numpy(), dtype=np.float64)
        moved = np.full(n, np.nan)
        moved[ok] = values[src[ok]]
        out[column] = moved.astype(dtype)
    for parent in HOLD_PARENTS:
        out[hold_column(parent)] = (_held(frame, year_col[0], codes, steps, parent) if n
                                    else np.zeros(0, dtype=np.float64))
    return pd.DataFrame({c: out[c] for c in OUTPUTS}, index=frame.index)


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
