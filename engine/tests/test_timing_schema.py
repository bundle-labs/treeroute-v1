"""The approved reach facts on the window fact (owner ruling of 2026-09-28, item 8 (a)), and the
timing rules reading the package schema's models directly."""

import pytest
from pydantic import ValidationError

from treeroute.package import schema as S
from treeroute.timing import content_interval, forward_reach_days, reference_day
from test_timing_facts import day, month_period
from test_timing_ruled import RULED

STORE_COLUMN = {"dtype": "float32", "units": "1",
                "cadence": {"kind": "regular", "length": 1, "unit": "month"},
                "scope": "unit", "stamp": "period_centre",
                "window": {"length": 1, "unit": "month", "align": "centred",
                           "reach_after_max": {"value": 15, "unit": "day"},
                           "reach_before_max": {"value": 15, "unit": "day"}}}


def test_window_takes_both_reach_facts():
    col = S.StoreColumn.model_validate(STORE_COLUMN)
    assert col.window.reach_after_max == S.Reach(value=15, unit="day")
    assert col.window.reach_before_max.value == 15.0
    S.Window.model_validate({"length": 1, "unit": "month", "align": "backward",
                             "reach_after_max": {"value": 2, "unit": "month"}})
    S.Window.model_validate({"align": "unknown", "max_length": 5, "unit": "month",
                             "reach_after_max": {"value": 1, "unit": "month"}})
    assert S.Window.model_validate({"length": 1, "unit": "month",
                                    "align": "centred"}).reach_after_max is None


@pytest.mark.parametrize("reach", [
    {"value": "15", "unit": "day"}, {"value": True, "unit": "day"}, {"value": 0, "unit": "day"},
    {"value": -3, "unit": "day"}, {"value": float("inf"), "unit": "day"},
    {"value": float("nan"), "unit": "day"}, {"value": 15, "unit": "week"}, {"value": 15},
    {"unit": "day"}, {"value": 15, "unit": "day", "note": "x"},
    {"value": "unknown", "unit": "day"},      # a margin nobody stated is not a number: sign a bound
])
def test_malformed_reach_is_refused(reach):
    with pytest.raises(ValidationError):
        S.Window.model_validate({"length": 1, "unit": "month", "align": "centred",
                                 "reach_after_max": reach})


def test_target_window_in_a_package_catalog_takes_reach():
    cat = S.PackageCatalog.model_validate({"columns": {"y": {
        "role": "target", "stamp": "period_end",
        "window": {"length": 1, "unit": "month", "align": "backward",
                   "reach_after_max": {"value": 1, "unit": "month"}}}}})
    assert cat.columns["y"].window.reach_after_max.unit == "month"


def test_json_schema_export_lists_the_reach_facts():
    text = str(S.json_schemas()["store_catalog"])
    assert "reach_after_max" in text and "reach_before_max" in text


def test_timing_reads_the_schema_models_directly():
    col = S.StoreColumn.model_validate(STORE_COLUMN)
    dec = month_period(2019, 12)
    assert content_interval(col, dec) == (day(2019, 11, 16), day(2020, 1, 15))
    assert forward_reach_days(col, dec) == 15
    tgt = S.PackageColumn.model_validate({"role": "target", "stamp": "period_centre",
                                          "window": STORE_COLUMN["window"]})
    assert reference_day(tgt, dec, "nowcast") == day(2020, 1, 15)


# ---- the timing rules on the four declared packages, as their facts stand (tests may name them) ----
PACKAGES = ("pm25", "fire", "defo", "ndvi")


@pytest.mark.parametrize("name", PACKAGES)
def test_timing_on_the_declared_packages(name):
    import json
    from types import SimpleNamespace as NS

    from conftest import ENGINE_DIR
    from treeroute.package.load import load_package
    from treeroute.timing import TimingRefusal, compute_lag

    root = ENGINE_DIR / "datasets" / name
    pkg = load_package(root)
    unit = json.loads((root / "expected_derived.json").read_text("utf-8"))["R1_cadence"]["unit"]
    cadence = NS(kind="regular", length=1, unit=unit)
    (tname, tfacts), = [(c, f) for c, f in pkg.catalog.columns.items() if f.role == "target"]
    tgt = NS(name=tname, cadence=cadence, stamp=tfacts.stamp, window=tfacts.window,
             computed_from=tuple(tfacts.computed_from))
    period = (day(2019, 12, 1), day(2019, 12, 31)) if unit == "month" else (day(2019, 1, 1),
                                                                           day(2019, 12, 31))
    if tfacts.window.align == "unknown":
        # the seeded target window is unknown until the owner's signed facts are merged: refused
        with pytest.raises(TimingRefusal):
            reference_day(tgt, period, "nowcast")
        return
    # The nowcast reference is the end of the target's own CONTENT, reach facts included (R8; owner
    # rulings B item 8 (a), R-D (b)): the month end only when the target window declares no reach past
    # its step; fire's detection window and NDVI's 16-day composites reach past the month end, so their
    # reference is the content end the reach facts imply (target_content), later than the month end.
    from treeroute.timing import target_content

    content_end = target_content(tgt, period)[1]
    assert reference_day(tgt, period, "nowcast") == content_end
    if tfacts.window.reach_after_max is None:
        assert content_end == period[1]
    else:
        reach = tfacts.window.reach_after_max
        assert content_end > period[1]
        if reach.unit == "day":
            assert content_end - period[1] <= reach.value
        elif reach.unit == "month":
            assert content_end - period[1] <= 31 * reach.value

    stores = {}
    for store in pkg.stores.values():
        stores.update(store.columns)
    lags, refused = {}, {}
    for col, facts in pkg.catalog.columns.items():
        sc = stores.get(col)
        if facts.role not in ("driver", "router_context") or sc is None \
                or sc.cadence.kind in ("static", "epoch"):
            continue
        view = NS(name=col, cadence=sc.cadence, stamp=sc.stamp, window=sc.window,
                  fact_status=sc.fact_status, co_measured_with_target=facts.co_measured_with_target)
        try:
            lags[col] = compute_lag(view, tgt, cadence, "nowcast")
        except TimingRefusal as err:
            refused[col] = err
    assert lags
    for col, err in refused.items():
        window, col_unit = stores[col].window, stores[col].cadence.unit
        unknown = window is not None and window.align == "unknown" and window.max_length is None
        finer = unit == "year" and col_unit == "month"
        assert (err.rule == "G-LAG" and unknown) or (finer and "aggregate" in str(err)), (col, err)
    for col, got in lags.items():
        if col in RULED:
            # the ruled index lags (R-A a, R-B, R-C a) are checked on the store catalog by
            # test_timing_ruled.py (xfail while the seeded pre-ruling facts are unmerged); the
            # generic 'one plain step: lag 0' reading below would assert the pre-ruling value
            continue
        sc = stores[col]
        if sc.cadence.unit == "year" and unit == "month" and sc.stamp == "period_end":
            assert got.steps >= 1, col                       # annual columns: year -1 or more
        if sc.cadence.unit == unit and sc.stamp == "period_end" and sc.window.align == "backward" \
                and sc.window.length == 1 and sc.window.unit == unit and sc.window.reach_after_max is None:
            assert got.steps == (1 if got.floor_reason else 0), col    # one plain step: lag 0
        if sc.cadence.unit == unit == "month" and sc.window.reach_after_max is not None \
                and sc.window.reach_after_max.unit == "month":
            # a whole-month reach past the step (deeprec_twsa's signed 3 months, ruling J2 b / L1 a): lag >= reach
            assert got.steps >= sc.window.reach_after_max.value, col
        if pkg.catalog.columns[col].co_measured_with_target:
            assert got.steps >= 1 and got.floor_reason in (None, "co_measured"), col
    if unit == "month":
        # ruling L1 (b), signed 2026-10-06: the 13 index windows are {3, month, centred}: no KEPT column (keep, watch)
        # is refused at R8 on a monthly package any more, and each declared index column lags exactly one month
        kept = {c for c, v in pkg.ban.verdicts.items() if v.verdict in ("keep", "watch", "keep_unreviewed", "freeze")}
        assert not sorted(set(refused) & kept), sorted(set(refused) & kept)
        for col in L1_INDEX_WINDOWS:
            if col in lags:
                assert lags[col].steps == 1, (col, lags[col])


# ruling L1 (b) (OWNER_RULINGS_2026-10-05.md section L): the 13 index windows the owner signed {3, month, centred}
L1_INDEX_WINDOWS = ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi", "pdo", "epo", "grace_lwe")
