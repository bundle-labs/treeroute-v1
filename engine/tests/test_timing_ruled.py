"""The ruled index lags on REAL catalog facts, not only on synthetic ones.

Rulings (OWNER_RULINGS_2026-09-28.md part B): R-A (a) the ERSSTv5 filter is content, +2 months: the
4 nino* and the 8 sst_anom_* lag 2, oni 3, all 13 lag 1 year as annual aggregates; R-B tni signed
{7, month, centred}: lag 3; R-C (a) co2 {3, month, centred} assumed: lag 1, and 1 year as an annual
aggregate.

Two sources are checked:
  1. the audit's proposal (datasets/_stores/index_facts.yaml) with each ruling applied as the ruling
     reads. This is what the store catalog must say once merged; it passes today.
  2. the store catalog every package includes (monthly_panel_v170_schema_catalog.yaml). A column
     that still carries its seeded pre-ruling facts is PENDING: the merge is outside the timing
     module's write scope, so the test is marked xfail naming them, and derive v1 must not be
     trusted on those columns until they are merged. A column whose facts changed must give the
     ruled lag, whatever spelling was merged.
"""

import pytest
import yaml
from types import SimpleNamespace as NS

from conftest import ENGINE_DIR
from test_timing_facts import ANNUAL_TARGET, MONTHLY_TARGET, YEAR, year_period
from treeroute.package import schema as SC
from treeroute.package.load import validate_file
from treeroute.timing import (TimingRefusal, aggregate_reach, aggregate_window, compute_lag,
                              periods_inside)

STORES = ENGINE_DIR / "datasets" / "_stores"
STORE_CATALOG = STORES / "monthly_panel_v170_schema_catalog.yaml"
PROPOSAL = STORES / "index_facts.yaml"

NINO = ("nino12", "nino3", "nino4", "nino34")
SST_BOXES = ("sst_anom_atl3", "sst_anom_iod_west", "sst_anom_iod_east",
             "sst_anom_subpolar_north_atlantic", "sst_anom_coral_sea", "sst_anom_mediterranean",
             "sst_anom_global_tropical_mean", "sst_anom_nino34")
ERSST = NINO + ("oni",) + SST_BOXES
RULED_MONTHLY_LAG = dict({name: 2 for name in NINO + SST_BOXES}, oni=3, tni=3, co2=1)
RULED_ANNUAL_LAG = {name: 1 for name in RULED_MONTHLY_LAG}
RULED = tuple(RULED_MONTHLY_LAG)
R_B_WINDOW = {"length": 7, "unit": "month", "align": "centred"}      # tni, ruling R-B
R_C_WINDOW = {"length": 3, "unit": "month", "align": "centred"}      # co2, ruling R-C (a)

# The seeded store facts of 2026-09-28 (stamp, window): while a column still carries them, its
# ruling is not merged.
SEEDED = dict(
    {name: ("period_centre", {"unit": "month", "align": "unknown"}) for name in NINO + ("tni",)},
    oni=("period_centre", {"length": 3.0, "unit": "month", "align": "centred"}),
    co2=("period_end", {"length": 1.0, "unit": "month", "align": "backward"}),
    **{name: ("period_end", {"length": 1.0, "unit": "month", "align": "backward"})
       for name in SST_BOXES})

AGGREGATE_YEARS = range(2001, 2024)          # every data year of the panel's era, leap years included


def view(name, facts, co_measured=False):
    """A column view from a package-schema StoreColumn (timing reads facts by attribute name)."""
    return NS(name=name, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)


def store_column(stamp, window, fact_status="unverified"):
    return SC.StoreColumn.model_validate({
        "dtype": "float32", "units": "1", "scope": "global", "stamp": stamp, "window": window,
        "cadence": {"kind": "regular", "length": 1, "unit": "month"}, "fact_status": fact_status})


def annual_aggregate_lag(name, facts):
    """The column's calendar-year aggregate, its window computed by timing's aggregate path, lagged
    on an annual target."""
    col = view(name, facts)
    spans = [(year_period(y), periods_inside(col.cadence, year_period(y))) for y in AGGREGATE_YEARS]
    fact = aggregate_window(aggregate_reach(col, spans), YEAR)
    agg = SC.StoreColumn.model_validate({
        "dtype": "float32", "units": "1", "scope": "global", "stamp": fact["stamp"],
        "window": fact["window"], "cadence": {"kind": "regular", "length": 1, "unit": "year"}})
    return compute_lag(view(name + "_annual", agg), ANNUAL_TARGET, YEAR, "nowcast").steps


# ---- 1. the audit's proposal with the rulings applied ----
def _proposal():
    data = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    columns = {}
    for store in data["stores"].values():
        columns.update(store.get("columns", {}))
    return columns


def ruled_facts(name, proposal):
    entry = proposal[name]
    status = "unverified"
    if name in ERSST:                                   # R-A (a): the filter reach is content
        window = entry["window_if_filter_is_content"]
    elif name == "tni":                                 # R-B: one of the audit's owner options
        assert R_B_WINDOW in [o["window"] for o in entry["owner_options"]]
        window = R_B_WINDOW
    elif name == "co2":                                 # R-C (a): the proposed bound, assumed
        assert entry["window"] == R_C_WINDOW
        window, status = R_C_WINDOW, "assumed"
    else:
        window = entry["window"]
    return store_column(entry["stamp"], window, status)


@pytest.mark.parametrize("name", RULED)
def test_ruled_monthly_lag_from_the_proposal_with_the_ruling_applied(name):
    proposal = _proposal()
    assert proposal[name]["stamp"] == "period_centre"   # the rulings are in the audit's spelling
    facts = ruled_facts(name, proposal)
    assert compute_lag(view(name, facts), MONTHLY_TARGET, MONTHLY_TARGET.cadence,
                       "nowcast").steps == RULED_MONTHLY_LAG[name]


@pytest.mark.parametrize("name", RULED)
def test_ruled_annual_aggregate_lag_through_the_aggregate_path(name):
    assert annual_aggregate_lag(name, ruled_facts(name, _proposal())) == RULED_ANNUAL_LAG[name]


@pytest.mark.parametrize("name", ["V11_mean_ndvi", "V12_mean_evi"])
def test_reaching_composite_drivers_from_the_proposal(name):
    # the 16-day composites averaged into a month (audit T9; reach facts, ruling item 8 (a)):
    # 1 month as a driver, and 1 year as a calendar-year aggregate (defo's pending V11/V12 list)
    facts = ruled_facts(name, _proposal())
    assert compute_lag(view(name, facts), MONTHLY_TARGET, MONTHLY_TARGET.cadence,
                       "nowcast").steps == 1
    assert annual_aggregate_lag(name, facts) == 1


def test_the_stamp_must_be_merged_with_the_window():
    # the rulings are written with the stamp at the month CENTRE; the seeded store stamps co2 and the
    # 8 boxes at the month END, where the same windows reach half a month further and lag one more
    assert compute_lag(view("sst", store_column("period_end", {"length": 5, "unit": "month",
                                                               "align": "centred"})),
                       MONTHLY_TARGET, MONTHLY_TARGET.cadence, "nowcast").steps == 3
    assert compute_lag(view("co2", store_column("period_end", R_C_WINDOW, "assumed")),
                       MONTHLY_TARGET, MONTHLY_TARGET.cadence, "nowcast").steps == 2
    # merged together (centre stamp + ruled window), or the reach spelling at the month end: ruled
    reach_spelling = {"length": 1, "unit": "month", "align": "backward",
                      "reach_after_max": {"value": 2, "unit": "month"}}
    assert compute_lag(view("sst", store_column("period_end", reach_spelling)), MONTHLY_TARGET,
                       MONTHLY_TARGET.cadence, "nowcast").steps == 2
    assert compute_lag(view("sst", store_column("period_centre", {"length": 5, "unit": "month",
                                                                  "align": "centred"})),
                       MONTHLY_TARGET, MONTHLY_TARGET.cadence, "nowcast").steps == 2


# ---- 2. the store catalog the packages include ----
def _pre_ruling_value(name, facts):
    try:
        return compute_lag(view(name, facts), MONTHLY_TARGET, MONTHLY_TARGET.cadence,
                           "nowcast").steps
    except TimingRefusal as err:
        return "refused (%s)" % err.rule


def test_ruled_lags_on_the_merged_store_catalog():
    catalog = validate_file(STORE_CATALOG, SC.StoreCatalog)
    pending = {}
    for name in RULED:
        facts = catalog.columns[name]
        window = facts.window.model_dump(exclude_none=True) if facts.window else None
        if (facts.stamp, window) == SEEDED[name]:
            pending[name] = _pre_ruling_value(name, facts)
            continue
        # merged, in whatever spelling: the ruled values must come out
        got = compute_lag(view(name, facts), MONTHLY_TARGET, MONTHLY_TARGET.cadence, "nowcast")
        assert got.steps == RULED_MONTHLY_LAG[name], (name, got)
        assert annual_aggregate_lag(name, facts) == RULED_ANNUAL_LAG[name], name
    if pending:
        pytest.xfail("rulings R-A (a), R-B, R-C (a) are not merged into %s for %d columns; until "
                     "they are (stamp AND window), derive v1 must not be trusted on them. Pre-ruling "
                     "values today: %s" % (STORE_CATALOG.name, len(pending), pending))


def test_seeded_facts_give_the_pre_ruling_values():
    # what derive v1 would compute from the seeded store facts today (the hazard the xfail names)
    catalog = validate_file(STORE_CATALOG, SC.StoreCatalog)
    values = {name: _pre_ruling_value(name, catalog.columns[name]) for name in RULED
              if (catalog.columns[name].stamp,
                  catalog.columns[name].window.model_dump(exclude_none=True)) == SEEDED[name]}
    for name, value in values.items():
        assert value != RULED_MONTHLY_LAG[name], (name, value)
