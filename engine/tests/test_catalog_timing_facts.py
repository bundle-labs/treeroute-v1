"""The merged catalogs: every schema store catalog and the four package catalogs load, and the ruled timing
facts come out of the REAL catalog files through the timing rules.

Rulings (OWNER_RULINGS_2026-09-28.md):
  B R-A (a)  the ERSSTv5 filter is content, +2 months: nino12/3/4/34 and the 8 sst_anom_* lag 2, oni lag 3,
             all 13 lag 1 year as calendar-year aggregates;
  B R-B      tni signed {7, month, centred}: lag 3;
  B R-C (a)  co2 {3, month, centred}, assumed: lag 1, and 1 year as an annual aggregate;
  B R-D (b)  fire's target gets a reach-after fact: R17 starts its history block at t-2, as for NDVI;
  B item 8   reach_after_max / reach_before_max on the window fact (V11/V12: the 16-day composites; December
             reaches about 3 days into January);
  C          defo's yearly columns are rebuilt from the monthly panel with aggregate_time (engineered columns);
  F4         the period-centre stamp merged with the ruled window (co2, the 8 sst_anom_*);
  F5         an aggregate's facts come from the timing helpers, so the ruled 1-year annual lags survive.

The catalogs are validated directly (treeroute.package.load.validate_file), not through load_package, so these
tests do not depend on the store-catalog sha256 each dataset.yaml declares. Every merged fact stays 'unverified'
or 'assumed' until the owner signs it (timing facts by Sat 10 Oct); the signing-state tests accept a signed fact
(a reviewer and a date), so signing does not break them.

compute_lag takes the LARGER of the nowcast and issue-step references (D24), so it returns one number for both.
On fire's reaching target the two references differ (the nowcast reference is the end of month t+1); a test pins
that, so the reliance on D24 is explicit.

Tests may name problems, columns and drives (G-NONAMES scans engine code only).
"""

import datetime as dt
from types import SimpleNamespace as NS

import pytest
import yaml

from conftest import ENGINE_DIR
from treeroute.errors import PackageError
from treeroute.package import schema as S
from treeroute.package.load import validate_file
from treeroute.timing import (TimingRefusal, aggregate_reach, aggregate_window, compute_lag,
                              forward_reach_days, lag_trace, periods_inside, target_content,
                              target_reach_offset_steps)

DATASETS = ENGINE_DIR / "datasets"
STORES = DATASETS / "_stores"
PANEL = STORES / "monthly_panel_v170_schema_catalog.yaml"
DEFO_FEATURES = STORES / "defo_annual_features_schema_catalog.yaml"
PROPOSAL = STORES / "index_facts.yaml"
PACKAGES = ("pm25", "fire", "defo", "ndvi")
MONTHLY_PACKAGES = ("pm25", "fire", "ndvi")

NINO = ("nino12", "nino3", "nino4", "nino34")
SST_BOXES = ("sst_anom_atl3", "sst_anom_iod_west", "sst_anom_iod_east",
             "sst_anom_subpolar_north_atlantic", "sst_anom_coral_sea", "sst_anom_mediterranean",
             "sst_anom_global_tropical_mean", "sst_anom_nino34")
ERSST = NINO + ("oni",) + SST_BOXES
RULED_MONTHLY_LAG = dict({name: 2 for name in NINO + SST_BOXES}, oni=3, tni=3, co2=1)
RULED = tuple(RULED_MONTHLY_LAG)
MOD13 = ("V11_mean_ndvi", "V12_mean_evi")
MERGED = RULED + MOD13
ASSUMED = ("tni", "co2")                      # R-B signed bound; R-C (a) 'assumed'
# the parents whose calendar-year aggregate reaches past the year end (lag 1 year): the ruled 15, the two MOD13
# composites, and the two columns seeded with a 47-day centred window (16-day composites averaged into a month)
ANNUAL_LAG_ONE = frozenset(RULED + MOD13 + ("V14_mean_albedo", "gpp_kgC_m2"))
STATS = ("mean", "min", "max")
PANEL_YEARS = range(2002, 2024)                # the panel's content years (every leap and common year pair)

MONTH = NS(kind="regular", length=1, unit="month")
YEAR = NS(kind="regular", length=1, unit="year")


def day(y, m, d):
    return dt.date(y, m, d).toordinal()


def month_period(y, m):
    nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
    return day(y, m, 1), nxt.toordinal() - 1


def year_period(y):
    return day(y, 1, 1), day(y, 12, 31)


@pytest.fixture(scope="module")
def panel():
    return validate_file(PANEL, S.StoreCatalog)


@pytest.fixture(scope="module")
def features():
    return validate_file(DEFO_FEATURES, S.StoreCatalog)


@pytest.fixture(scope="module")
def catalogs():
    return {p: validate_file(DATASETS / p / "catalog.yaml", S.PackageCatalog) for p in PACKAGES}


def target_of(catalog, cadence):
    """The package's one target as the view the timing rules read (its package facts)."""
    (name, facts), = [(c, f) for c, f in catalog.columns.items() if f.role == "target"]
    return NS(name=name, cadence=cadence, stamp=facts.stamp, window=facts.window,
              computed_from=tuple(facts.computed_from), fact_status=facts.fact_status)


def column_view(name, facts, co_measured=False):
    return NS(name=name, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)


def aggregate_view(name, parent_facts, years=PANEL_YEARS, co_measured=False):
    """The calendar-year aggregate of a monthly column, its stamp and window computed by the timing
    aggregate path from the parent's facts (plan 1.5; ruling F5), never typed."""
    parent = column_view(name, parent_facts)
    spans = [(year_period(y), periods_inside(parent.cadence, year_period(y))) for y in years]
    fact = aggregate_window(aggregate_reach(parent, spans), YEAR)
    agg = S.StoreColumn.model_validate({
        "dtype": "float32", "units": "1", "scope": "unit", "stamp": fact["stamp"],
        "window": fact["window"], "cadence": {"kind": "regular", "length": 1, "unit": "year"}})
    return column_view(name, agg, co_measured)


# ---------------------------------------------------------------------------------------------------
# the catalogs load
SCHEMA_CATALOGS = sorted(p.name for p in STORES.glob("*_schema_catalog.yaml"))


def test_the_schema_store_catalogs_are_the_expected_set():
    assert SCHEMA_CATALOGS == sorted([
        "defo_annual_features_schema_catalog.yaml", "edgar_emis_schema_catalog.yaml",
        "fire_danger_schema_catalog.yaml", "fire_drivers_schema_catalog.yaml",
        "fire_history_schema_catalog.yaml", "fire_ndvi_lags_schema_catalog.yaml",
        "gfed_burn_schema_catalog.yaml", "monthly_panel_v170_schema_catalog.yaml"])


@pytest.mark.parametrize("name", SCHEMA_CATALOGS)
def test_every_schema_store_catalog_loads(name):
    catalog = validate_file(STORES / name, S.StoreCatalog)
    assert catalog.store and catalog.columns
    assert name == catalog.store + "_schema_catalog.yaml"


def test_the_audit_proposal_is_not_a_store_catalog():
    # index_facts.yaml shares the folder but must never be included: it does not load as a store catalog
    data = yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))
    assert data["meta"]["not_a_store_catalog"] is True
    with pytest.raises(PackageError):
        validate_file(PROPOSAL, S.StoreCatalog)


@pytest.mark.parametrize("name", PACKAGES)
def test_every_package_catalog_loads_with_one_target(catalogs, name):
    targets = [c for c, f in catalogs[name].columns.items() if f.role == "target"]
    assert len(targets) == 1, targets


# ---------------------------------------------------------------------------------------------------
# the merged store facts (R-A a, R-B, R-C a, F4, item 8 a)
def test_merged_store_facts_are_stamped_at_the_period_centre_with_centred_windows(panel):
    for name in MERGED:
        facts = panel.columns[name]
        assert facts.stamp == "period_centre", name                        # F4 (and the audit's spelling)
        assert facts.window.align == "centred" and facts.window.unit == "month", name
        assert facts.window.max_length is None, name


def test_merged_store_windows_are_the_ruled_ones(panel):
    def reach(r):
        return None if r is None else (r.value, r.unit)

    for name in ERSST:                                                     # R-A (a): +2 months of content
        w = panel.columns[name].window
        assert w.length == (3 if name == "oni" else 1), name
        assert reach(w.reach_after_max) == (2, "month") and w.reach_before_max is None, name
    for name, length in (("tni", 7), ("co2", 3)):                          # R-B; R-C (a)
        w = panel.columns[name].window
        assert (w.length, w.reach_after_max, w.reach_before_max) == (length, None, None), name
    for name in MOD13:                                                     # item 8 (a): 16-day composites
        w = panel.columns[name].window
        assert w.length == 1, name
        assert reach(w.reach_after_max) == reach(w.reach_before_max) == (15, "day"), name


SIGNED_STATUSES = ("verified", "assumed")      # G-FACTS: timing facts verified, or signed 'assumed' (plan 1.3)


def check_signing_state(where, facts, unsigned_status):
    """Until the owner signs a merged fact (no reviewer) it carries the status the merge wrote; once signed it
    carries a reviewer, a date and a status G-FACTS accepts."""
    if facts.reviewed_by is None:
        assert facts.fact_status == unsigned_status and facts.date is None, where
    else:
        assert facts.fact_status in SIGNED_STATUSES and facts.date is not None, where


def test_merged_facts_carry_the_merge_status_until_signed(panel, catalogs):
    for name in MERGED:
        check_signing_state(name, panel.columns[name], "assumed" if name in ASSUMED else "unverified")
    # R-D (b) ruled the reach fact, not its 1-month value: the proposed bound waits for the owner's signature
    check_signing_state("fire burned_frac", catalogs["fire"].columns["burned_frac"], "unverified")
    check_signing_state("ndvi V11_mean_ndvi", catalogs["ndvi"].columns["V11_mean_ndvi"], "unverified")


def is_aggregate(facts):
    return bool(facts.derived_from) and (facts.operation or "").startswith("aggregate_time ")


def test_no_fact_without_a_reviewer_is_verified(catalogs):
    """A fact nobody has signed is never 'verified' (plan 1.3: fact_status, reviewed_by, date). Scoped to facts
    with no reviewer, so the owner's signatures do not break it. The defo aggregates are left out on purpose:
    treeroute/io/aggregate.py resets reviewed_by and inherits fact_status from the parent, so their status is
    checked against the parent (test_defo_aggregate_store_facts_are_declared_and_inherited)."""
    checked = 0
    for name in SCHEMA_CATALOGS:
        for col, facts in validate_file(STORES / name, S.StoreCatalog).columns.items():
            if is_aggregate(facts):
                continue
            checked += 1
            if facts.reviewed_by is None:
                assert facts.fact_status != "verified", (name, col)
    for package, catalog in catalogs.items():
        for col, facts in catalog.columns.items():
            checked += 1
            if facts.reviewed_by is None:
                assert facts.fact_status != "verified", (package, col)
    assert checked > 1000


def test_merged_store_facts_reach_as_far_as_the_audit_proposal_with_the_rulings_applied(panel):
    """The merged spelling and the audit's ruled window agree on the forward edge in every month of the
    panel's era (R8 reads only that edge)."""
    proposal = {}
    for store in yaml.safe_load(PROPOSAL.read_text(encoding="utf-8"))["stores"].values():
        proposal.update(store.get("columns", {}))
    ruled_window = dict({n: proposal[n]["window_if_filter_is_content"] for n in ERSST},
                        tni={"length": 7, "unit": "month", "align": "centred"},
                        co2=proposal["co2"]["window"],
                        **{n: proposal[n]["window"] for n in MOD13})
    assert ruled_window["tni"] in [o["window"] for o in proposal["tni"]["owner_options"]]   # R-B option
    assert ruled_window["co2"] == {"length": 3, "unit": "month", "align": "centred"}          # R-C (a)
    months = [month_period(y, m) for y in PANEL_YEARS for m in range(1, 13)]
    for name in MERGED:
        audit = S.StoreColumn.model_validate({
            "dtype": "float32", "units": "1", "scope": "global", "stamp": proposal[name]["stamp"],
            "window": ruled_window[name], "cadence": {"kind": "regular", "length": 1, "unit": "month"},
            "fact_status": "assumed" if name in ASSUMED else "unverified"})
        merged = column_view(name, panel.columns[name])
        for period in months:
            assert forward_reach_days(merged, period) == \
                forward_reach_days(column_view(name, audit), period), (name, period)


# ---------------------------------------------------------------------------------------------------
# compute_lag gives the ruled lags on the real package targets
@pytest.mark.parametrize("package", MONTHLY_PACKAGES)
@pytest.mark.parametrize("name", RULED)
def test_ruled_monthly_lag_on_each_monthly_package(panel, catalogs, package, name):
    catalog = catalogs[package]
    assert catalog.columns[name].role == "driver"
    tgt = target_of(catalog, MONTH)
    col = column_view(name, panel.columns[name], catalog.columns[name].co_measured_with_target)
    # R8 takes the larger of the two references (D24), so both calls return the same number by construction;
    # whether the references themselves agree is pinned per target below
    for reference in ("nowcast", "issue_step"):
        assert compute_lag(col, tgt, MONTH, reference).steps == RULED_MONTHLY_LAG[name], reference
    trace = lag_trace(col, tgt, MONTH)
    assert trace.content_steps == trace.steps and trace.floor_reason is None   # from content, not a floor
    assert trace.issue_steps == RULED_MONTHLY_LAG[name]


@pytest.mark.parametrize("name", RULED + MOD13)
def test_fire_ruled_lags_rest_on_the_issue_step_reference(panel, catalogs, name):
    """Fire's target reaches 1 month past its month (R-D b; the bound is PROPOSED), so the nowcast reference
    (the end of the target's content, reach included) is the end of month t+1. On its own it would admit
    month t+1 content: one step less than the ruled lag for every ruled column and both MOD13 composites.
    The ruled lag holds only because R8 takes the larger reference (D24). A caller that reads the nowcast
    reference alone (an as-of join, a direct G-LAG check) must not; a larger bound moves it later still."""
    catalog = catalogs["fire"]
    col = column_view(name, panel.columns[name], catalog.columns[name].co_measured_with_target)
    trace = lag_trace(col, target_of(catalog, MONTH), MONTH)
    assert trace.nowcast_steps == trace.issue_steps - 1 < trace.issue_steps, name
    assert trace.steps == trace.issue_steps == RULED_MONTHLY_LAG.get(name, 1), name


@pytest.mark.parametrize("package, names", [("pm25", RULED + MOD13), ("ndvi", RULED)])
def test_the_two_references_agree_on_the_other_monthly_targets(panel, catalogs, package, names):
    # PM2.5's target is a plain month; NDVI's 15-day reach does not move a ruled index by a whole step
    catalog = catalogs[package]
    tgt = target_of(catalog, MONTH)
    for name in names:
        col = column_view(name, panel.columns[name], catalog.columns[name].co_measured_with_target)
        trace = lag_trace(col, tgt, MONTH)
        assert trace.nowcast_steps == trace.issue_steps == trace.steps, (package, name)


@pytest.mark.parametrize("package", ("pm25", "fire"))
@pytest.mark.parametrize("name", MOD13)
def test_mod13_composites_as_drivers_lag_one_month(panel, catalogs, package, name):
    # V11/V12 reach up to 15 days into the next month (item 8 a); where they are drivers they lag 1
    catalog = catalogs[package]
    assert catalog.columns[name].role == "driver"
    col = column_view(name, panel.columns[name], catalog.columns[name].co_measured_with_target)
    assert compute_lag(col, target_of(catalog, MONTH), MONTH, "nowcast").steps == 1


@pytest.mark.parametrize("package", MONTHLY_PACKAGES)
def test_a_plain_month_still_lags_zero_on_every_monthly_target(panel, catalogs, package):
    # the reaching targets (fire, NDVI) do not move a whole-month driver: D24 takes the issue-step reference
    facts = panel.columns["V01_mean_temp_C"]
    assert (facts.stamp, facts.window.align, facts.window.length) == ("period_end", "backward", 1)
    col = column_view("V01_mean_temp_C", facts)
    assert compute_lag(col, target_of(catalogs[package], MONTH), MONTH, "nowcast").steps == 0


@pytest.mark.parametrize("name", RULED + MOD13)
def test_ruled_annual_aggregate_lag_on_the_defo_target(panel, catalogs, name):
    tgt = target_of(catalogs["defo"], YEAR)
    agg = aggregate_view(name + "_mean", panel.columns[name])
    assert agg.stamp == "period_end" and agg.window.reach_after_max is not None
    assert compute_lag(agg, tgt, YEAR, "nowcast").steps == 1


# ---------------------------------------------------------------------------------------------------
# target windows: R17 offsets and the December reach
def test_r17_offsets_from_the_target_windows(catalogs):
    assert target_reach_offset_steps(target_of(catalogs["pm25"], MONTH), MONTH) == 0
    assert target_reach_offset_steps(target_of(catalogs["fire"], MONTH), MONTH) == 1   # R-D (b): t-2
    assert target_reach_offset_steps(target_of(catalogs["ndvi"], MONTH), MONTH) == 1   # composites: t-2
    assert target_reach_offset_steps(target_of(catalogs["defo"], YEAR), YEAR) == 0


def test_fire_target_reach_is_the_proposed_one_month_bound(catalogs):
    # R-D (b) ruled the fact; the 1-month value is a PROPOSED bound (the guide states no margin), unsigned
    facts = catalogs["fire"].columns["burned_frac"]
    assert (facts.stamp, facts.window.length, facts.window.unit, facts.window.align) == \
        ("period_end", 1, "month", "backward")
    assert (facts.window.reach_after_max.value, facts.window.reach_after_max.unit) == (1, "month")
    assert facts.window.reach_before_max is None
    tgt = target_of(catalogs["fire"], MONTH)
    for y in PANEL_YEARS:                                   # the burn month plus at most the next month
        for m in range(1, 13):
            first, last = target_content(tgt, month_period(y, m))
            nxt = month_period(y + (m == 12), m % 12 + 1)
            assert (first, last) == (month_period(y, m)[0], nxt[1]), (y, m)


def test_ndvi_target_facts_equal_the_v11_store_facts_and_reach_into_january(panel, catalogs):
    target = catalogs["ndvi"].columns["V11_mean_ndvi"]
    store = panel.columns["V11_mean_ndvi"]
    assert (target.stamp, target.window) == (store.stamp, store.window)
    tgt = target_of(catalogs["ndvi"], MONTH)
    for y in PANEL_YEARS:
        dec = month_period(y, 12)
        first, last = target_content(tgt, dec)
        # December's day-353 composite ends on 2-3 January (audit T9, [S42]); the 15-day bound covers it
        assert last - dec[1] == 15 >= 3
        assert dec[0] - first == 15


# ---------------------------------------------------------------------------------------------------
# defo's annual aggregates (ruling C): declared as engineered, facts inherited, window computed.
# Owner ruling J4 (OWNER_RULINGS_2026-10-05.md section J, 2026-10-05) removed the 101 monthly parents from defo's
# catalog ("an annual target never reads a monthly row"): the parents are now read off the declared aggregates, as
# features/build_store.py column_plan does (UPDATED 2026-10-06, agent C1: the test listed role 'driver' rows).
def monthly_parents_of_aggregates(catalog, panel):
    """The one-month panel columns whose three aggregates <parent>_mean/_min/_max the catalog declares (engineered),
    in the order of their first aggregate (features/build_store.py column_plan)."""
    out = []
    for c, f in catalog.columns.items():
        head, _, stat = c.rpartition("_")
        if (f.role == "engineered" and stat in STATS and head not in out and head in panel.columns
                and (panel.columns[head].cadence.kind, panel.columns[head].cadence.length,
                     panel.columns[head].cadence.unit) == ("regular", 1, "month")):
            out.append(head)
    return out


def test_defo_aggregates_cover_every_monthly_driver_and_are_engineered(panel, features, catalogs):
    defo = catalogs["defo"]
    parents = monthly_parents_of_aggregates(defo, panel)
    assert len(parents) == 101
    assert not set(parents) & set(defo.columns)                         # J4: no monthly parent is a catalog row
    expected = {"%s_%s" % (p, s) for p in parents for s in STATS}
    assert set(features.columns) == expected
    assert {c for c in expected if defo.columns.get(c) is not None
            and defo.columns[c].role == "engineered"} == expected
    assert not set(features.columns) & set(panel.columns)               # new names, never a panel column


# The seed (datasets/_stores/defo_annual_features_schema_catalog.yaml, NOT included by the package: the generated
# store catalogs supersede it) predates two later rulings on its parents' facts. The drift is pinned exactly, so any
# other drift still fails: J4 (V30_soil_moisture_pct legal minimum -1e-12, rounding negatives) and L1 (the owner's
# signature: fact_status unverified -> assumed with reviewed_by owner on V30, deeprec_twsa and the 13 index windows).
SEED_PRE_RULING_DRIFT = {("V30_soil_moisture_pct", "legal_range"): ((0.0, 100.0), (-1e-12, 100.0))}
SEED_PRE_RULING_DRIFT.update({(p, "fact_status"): ("unverified", "assumed") for p in (
    "V30_soil_moisture_pct", "deeprec_twsa", "soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi", "pdo",
    "epo", "grace_lwe")})


def test_defo_aggregate_store_facts_are_declared_and_inherited(panel, features):
    drift = {}
    for name, facts in features.columns.items():
        parent_name, stat = name.rsplit("_", 1)
        parent = panel.columns[parent_name]
        for field in ("legal_range", "fact_status"):
            if (parent_name, field) in SEED_PRE_RULING_DRIFT and getattr(facts, field) != getattr(parent, field):
                drift[(parent_name, field)] = (getattr(facts, field), getattr(parent, field))
                parent = parent.model_copy(update={field: getattr(facts, field)})
        if (parent_name, "fact_status") in SEED_PRE_RULING_DRIFT:
            assert panel.columns[parent_name].reviewed_by == "owner", parent_name      # the L1 signature
        assert facts.derived_from == [parent_name], name
        assert facts.operation == "aggregate_time {window: 1 year, stat: %s}" % stat, name
        assert facts.reads_target is False, name
        assert facts.window is None, name                                # computed at build, never typed
        assert facts.stamp == "period_end", name                         # the aggregate path's stamp
        assert (facts.cadence.kind, facts.cadence.length, facts.cadence.unit) == ("regular", 1, "year")
        # as treeroute/io/aggregate.py builds an aggregate's facts: dtype float64, no fill codes; plan 1.5 units,
        # legal range (mean/min/max), lineage and product family inherited, and every other fact too
        assert facts.dtype == "float64" and facts.fill_values == [], name
        assert facts.units == parent.units and facts.legal_range == parent.legal_range, name
        assert facts.product_family == parent.product_family and facts.lineage == parent.lineage, name
        assert (facts.scope, facts.baseline_period, facts.observed_through, facts.fact_status) == \
            (parent.scope, parent.baseline_period, parent.observed_through, parent.fact_status), name
        assert facts.reviewed_by is None, name              # aggregate.py resets it: nobody reviewed the aggregate
    assert drift == SEED_PRE_RULING_DRIFT


def test_defo_aggregate_lags_computed_from_the_parent_facts(panel, features, catalogs):
    """F5: the aggregate's window comes from the timing helpers. Every parent whose content reaches past
    the year end gives lag 1 year; a whole-period backward parent lag 0; an unknown window is refused.
    UPDATED 2026-10-06 (agent C1): since ruling J2 (b) (deeprec_twsa reach 3 months) and ruling L1 (b) (the 13 index
    windows signed {3, month, centred}) those 14 parents reach past the year end too, and no parent is refused."""
    tgt = target_of(catalogs["defo"], YEAR)
    lag_one, lag_zero, refused = set(), set(), set()
    for parent_name in sorted({f.derived_from[0] for f in features.columns.values()}):
        parent = panel.columns[parent_name]
        try:
            steps = compute_lag(aggregate_view(parent_name, parent), tgt, YEAR, "nowcast").steps
        except TimingRefusal as err:
            assert err.rule == "G-LAG", (parent_name, err)
            assert parent.window.align == "unknown" and parent.window.max_length is None
            refused.add(parent_name)
            continue
        assert steps in (0, 1), (parent_name, steps)
        (lag_one if steps else lag_zero).add(parent_name)
        if parent.stamp == "period_end" and parent.window.align == "backward" and parent.window.reach_after_max is None:
            assert steps == 0, parent_name          # (deeprec_twsa's J2 b reach_after_max carries it into January)
    assert lag_one == ANNUAL_LAG_ONE | set(L1_INDEX_WINDOWS) | {"deeprec_twsa"}
    assert refused == set()
    assert len(lag_zero) + len(lag_one) + len(refused) == 101


# the monthly parents the shipped defo run read ONLY lagged (defo_ban.py LAG, 'measures the clearing concurrently';
# the lag1_* entries of defo/catalog.yaml; the review sheet marks each 'co-measured -> at least 1 step')
LAG_PARENTS_AT_LAG_ZERO = ("V13_mean_lst_C", "nighttime_lst_C", "cloud_frequency_pct", "snow_cover_fraction",
                           "esacci_sm", "V20_burned_binary")
LAG_PARENTS_AT_LAG_ONE = ("V11_mean_ndvi", "V12_mean_evi", "V14_mean_albedo", "gpp_kgC_m2")


# owner ruling J4: the aggregates of these four lag parents carry co_measured_with_target: true in defo's catalog
J4_CO_MEASURED_PARENTS = ("V13_mean_lst_C", "nighttime_lst_C", "cloud_frequency_pct", "V20_burned_binary")


def test_co_measured_answer_decides_the_lag_parents_aggregates(panel, features, catalogs):
    """Plan 1.4 family expansion carries verdicts only, so the aggregates of the monthly LAG parents need their own
    co_measured_with_target answer. From the facts alone six of them come out at lag 0 year; a 'true' answer floors
    every one at 1 year. UPDATED 2026-10-06 (agent C1) for owner ruling J4: the 33 pre-lagged lag1_* rows are gone
    from defo's catalog (no row reads them), and J4 wrote the 'true' answer on the aggregates of the four parents
    J4_CO_MEASURED_PARENTS (catalog co_measured_with_target), so R8 floors those at one year."""
    defo = catalogs["defo"]
    tgt = target_of(defo, YEAR)
    parents = {f.derived_from[0] for f in features.columns.values()}
    assert not [c for c in defo.columns if c.startswith("lag1_")]                  # J4 removed them
    for parent_name in LAG_PARENTS_AT_LAG_ZERO + LAG_PARENTS_AT_LAG_ONE:
        assert parent_name in parents, parent_name
        for stat in STATS:
            assert defo.columns["%s_%s" % (parent_name, stat)].role == "engineered"
            answer = defo.columns["%s_%s" % (parent_name, stat)].co_measured_with_target
            assert answer is (True if parent_name in J4_CO_MEASURED_PARENTS else None), (parent_name, stat)
        facts = panel.columns[parent_name]
        from_facts = compute_lag(aggregate_view(parent_name, facts), tgt, YEAR, "nowcast").steps
        co_measured = compute_lag(aggregate_view(parent_name, facts, co_measured=True), tgt, YEAR, "nowcast")
        assert from_facts == (0 if parent_name in LAG_PARENTS_AT_LAG_ZERO else 1), parent_name
        assert co_measured.steps == 1, parent_name
    assert not set(LAG_PARENTS_AT_LAG_ZERO) & ANNUAL_LAG_ONE
    assert set(LAG_PARENTS_AT_LAG_ONE) <= ANNUAL_LAG_ONE


# ---------------------------------------------------------------------------------------------------
# ruling L1 (OWNER_RULINGS_2026-10-05.md section L, owner 2026-10-06): the timing facts signed by the owner, written
# fact_status 'assumed' + reviewed_by owner + date 2026-10-06 (plan 1.3's spelling of a signed fact; the schema's
# FactStatus has no 'signed' value)
L1_INDEX_WINDOWS = ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi", "pdo", "epo", "grace_lwe")
L1_SIGNED_AS_WRITTEN = ("deeprec_twsa", "phenology_sos_doy", "nitrogen_gkg", "V30_soil_moisture_pct", "tni")
L1_AGLW = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
L1_SIGNATURE = ("assumed", "owner", "2026-10-06")


def test_l1_the_13_index_windows_are_signed_three_months_centred_and_lag_one_month(panel, catalogs):
    """UPDATED 2026-10-06 for owner ruling N1 (OWNER_RULINGS_2026-10-06.md N): pdo takes nino34's form, window
    {1, month, centred} plus the ERSSTv5 filter reach of +2 months, so it enters at lag 2 on a monthly target (L1 b's
    3-month width plus the reach would give 3); the other 12 stay at lag 1."""
    for name in L1_INDEX_WINDOWS:
        facts = panel.columns[name]
        w = facts.window
        n1 = name == "pdo"
        assert (w.length, w.unit, w.align, w.max_length) == (1 if n1 else 3, "month", "centred", None), name
        reach = None if w.reach_after_max is None else (w.reach_after_max.value, w.reach_after_max.unit)
        assert reach == ((2, "month") if n1 else None) and w.reach_before_max is None, name
        assert facts.stamp == "period_centre", name
        assert (facts.fact_status, facts.reviewed_by, facts.date) == L1_SIGNATURE, name
        if n1:
            assert "N1 (OWNER_RULINGS_2026-10-06.md" in facts.provenance
        for package in MONTHLY_PACKAGES:
            tgt = target_of(catalogs[package], MONTH)
            assert compute_lag(column_view(name, facts), tgt, MONTH, "nowcast").steps == (2 if n1 else 1),                 (package, name)
    # as a calendar-year aggregate the December value reaches into January: one year on an annual target
    tgt = target_of(catalogs["defo"], YEAR)
    assert compute_lag(aggregate_view("ao", panel.columns["ao"]), tgt, YEAR, "nowcast").steps == 1


def test_l1_the_other_signed_store_facts_and_co2_stays_unsigned(panel):
    from treeroute.package.load import validate_file as vf

    for name in L1_SIGNED_AS_WRITTEN + L1_AGLW:
        facts = panel.columns[name]
        assert (facts.fact_status, facts.reviewed_by, facts.date) == L1_SIGNATURE, name
        assert "SIGNED by the owner 2026-10-06 (ruling L1" in facts.provenance, name
    for name in L1_AGLW:
        f = panel.columns[name]
        assert (f.cadence.kind, f.cadence.length, f.cadence.unit, f.observed_through) == ("regular", 1, "year", "2021")
        assert (f.window.length, f.window.unit, f.window.align) == (1, "year", "backward"), name
    burn = vf(STORES / "gfed_burn_schema_catalog.yaml", S.StoreCatalog).columns["burn_frac"]
    assert (burn.fact_status, burn.reviewed_by, burn.date) == L1_SIGNATURE
    assert (panel.columns["co2"].fact_status, panel.columns["co2"].reviewed_by) == ("assumed", None)
    # nothing in the shared panel was 'verified' by the signature, and every reviewer is the owner with a date
    for name, facts in panel.columns.items():
        assert facts.fact_status != "verified", name
        assert (facts.reviewed_by is None) == (facts.date is None), name
        assert facts.reviewed_by in (None, "owner"), name
