"""Owner ruling L on the defo package, the parts review/PENDING_DEFO_L.md lists for the defo task and the K task
applies (tests may name problems):

  - L3 (items 5 a-d): the raw aglw_* are banned ('incomplete', the reason word disclosed as an OWNER item), the six
    aglw_<x>_hold2021 columns are features/build.py outputs, 'watch', co-measured as their parents, so R8 lags them
    one year; their facts are the parent's store facts; the script copies no signature: the owner's S5 signature
    (ruling N, OWNER_RULINGS_2026-10-06.md) is written by the SIGNOFF block of features/build.py.
  - L3 values, BACKWARD ONLY, on two real groups (costa_rica, pearl_river_delta): rows up to 2021 equal the parent;
    the 2022 and 2023 rows hold the same cell's 2021 value; a value planted in any later year never enters an earlier
    row, the rescaled 2022-2023 layers never enter any row, and a value planted in 2021 enters 2021-2023 (positive
    control). A cell without a 2021 row gets NaN after 2021, never a neighbour's value.
  - L4 (item 6): eddi_observed_mean/_min/_max banned structural, out of the tree features.
  (The test that nothing in the package is marked signed is gone: owner ruling N S18 a signs defo like the others.)
"""

from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

DEFO = ENGINE_DIR / "datasets" / "defo"
PANEL_CATALOG = "../_stores/monthly_panel_v170_schema_catalog.yaml"
K_CATALOG = "features/defo_features_k_store_catalog.yaml"
FEATURES_TEMPLATE = "D:/defo_features/{group}_{year}.parquet"
AGLW = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
HOLD = tuple(a + "_hold2021" for a in AGLW)
L4 = tuple("eddi_observed_%s" % s for s in ("mean", "min", "max"))
YEAR = NS(kind="regular", length=1, unit="year")
GROUPS = ("costa_rica", "pearl_river_delta")
KEYS = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year"}}
DATA = Path("D:/defo_features").is_dir()
needs_data = pytest.mark.skipif(not DATA, reason="the defo features store on D: is not reachable")


def _load():
    from treeroute.package.load import load_package
    return load_package(DEFO)


def _hook():
    from treeroute.pipeline import data as D
    return D.load_hook(DEFO, D.FEATURE_SCRIPT)


def _lag(pkg, column, facts, co_measured):
    from treeroute.timing import compute_lag
    t = pkg.catalog.columns["loss_frac"]
    target = NS(name="loss_frac", cadence=YEAR, stamp=t.stamp, window=t.window, computed_from=tuple(t.computed_from),
                fact_status=t.fact_status)
    view = NS(name=column, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)
    return compute_lag(view, target, YEAR, "nowcast").steps


def test_l3_l4_verdicts_and_the_closed_world():
    from treeroute.io.apply import apply_verdicts

    pkg = _load()
    v = pkg.ban.verdicts
    for a, h in zip(AGLW, HOLD):
        assert (v[a].verdict, v[a].reason) == ("ban", "incomplete") and "L3" in v[a].evidence, a
        assert "post_window_snapshot" in v[a].evidence and "OWNER" in v[a].evidence, a   # the reason word disclosed
        assert v[h].verdict == "watch" and "L3" in v[h].reason and "two years old" in v[h].reason, h
    for c in L4:
        assert (v[c].verdict, v[c].reason) == ("ban", "structural") and "L4" in v[c].evidence, c
    non_key = tuple(c for c, f in pkg.catalog.columns.items() if f.role not in ("key_unit", "key_group", "key_time"))
    sets = apply_verdicts(non_key, dict(v), {c: pkg.catalog.columns[c].role for c in non_key})
    assert set(HOLD) <= set(sets.tree_features)
    assert not (set(AGLW) | set(L4)) & set(sets.tree_features)
    flags = [e for e in pkg.exceptions.entries if e.check and e.check.startswith("AGLW 2022-23 extension")]
    assert len(flags) == 1 and all(c in flags[0].check for c in AGLW + HOLD) and "L3" in flags[0].decision
    assert "signed by the owner 2026-10-06 (ruling N" in flags[0].owner and "S8" in flags[0].owner   # S8: one of the 28


def test_l3_hold_facts_are_the_parents_unsigned_and_lag_one_year():
    from treeroute.derive import orchestrate as O
    from treeroute.pipeline import data as D

    pkg = _load()
    hook = _hook()
    outputs = D.feature_outputs(hook)
    panel = pkg.stores[PANEL_CATALOG].columns
    cols = pkg.catalog.columns
    for a, h in zip(AGLW, HOLD):
        f, p = outputs[h], panel[a]
        assert f.derived_from == [a] and f.reads_target is False, h
        assert f.operation == "hold_last_observed through_year=2021 unit=year", h
        assert (f.cadence, f.stamp, f.window, f.units, f.legal_range) == (p.cadence, p.stamp, p.window, p.units,
                                                                           p.legal_range), h
        assert f.observed_through == p.observed_through == "2021", h
        assert f.fill_values == [] and not f.near_sentinel_optout, h
        # the parent carries the owner's L1 c signature; the derived column the owner's S5 signature (ruling N), written
        # by the SIGNOFF block of features/build.py, never copied from the parent
        assert p.reviewed_by == "owner" and f.fact_status == "assumed", h
        assert f.reviewed_by == "owner" and f.date == "2026-10-06" and "ruling N" in f.provenance, h
        r = cols[h]
        assert r.role == "engineered" and r.co_measured_with_target is True and r.fact_status == "assumed", h
        assert getattr(r, "reviewed_by", None) is None, h
        assert _lag(pkg, h, f, True) == 1 and _lag(pkg, h, f, None) == 0, h     # R8: one year through the fact
    augmented = D.augment_package(pkg, outputs)
    notes = D.check_feature_lineage(outputs, augmented)          # G-LINEAGE does not refuse an 'incomplete' parent
    for a, h in zip(AGLW, HOLD):
        assert notes[h] == ["%s: ban (incomplete)" % a], h
    spec = D.package_spec(augmented)
    lags = {}
    for c in HOLD:
        s = spec.store_facts[c]
        from treeroute.timing import compute_lag
        t = pkg.catalog.columns["loss_frac"]
        lags[c] = compute_lag(NS(name=c, cadence=s.cadence, stamp=s.stamp, window=s.window, fact_status=s.fact_status,
                                 co_measured_with_target=cols[c].co_measured_with_target),
                              NS(name="loss_frac", cadence=YEAR, stamp=t.stamp, window=t.window,
                                 computed_from=tuple(t.computed_from), fact_status=t.fact_status), YEAR, "nowcast")
    r4, record = O._r04_lags(NS(store=spec.store_facts), lags)
    assert all(r4[c].steps == 1 for c in HOLD)                   # the hold is not a 'lag k' operation: R4 adds 0


def test_l3_hold_values_on_a_synthetic_frame_never_read_a_neighbour_or_a_later_row():
    hook = _hook()
    units = ["a"] * 4 + ["b"] * 3 + ["c"] * 2
    years = [2020, 2021, 2022, 2023, 2020, 2022, 2023, 2021, 2023]       # b has no 2021 row; c no 2022 row
    frame = pd.DataFrame({"cell_id": units, "year": years, "region": "g"})
    frame["_step"] = frame["year"]
    for p in hook.parents() + hook.LAG2_PARENTS:
        frame[p] = 0.0
    for i, a in enumerate(AGLW):
        frame[a] = np.arange(len(frame), dtype=np.float64) + 100.0 * i
    out = hook.build(frame.iloc[::-1].reset_index(drop=True), KEYS).iloc[::-1].reset_index(drop=True)
    for a, h in zip(AGLW, HOLD):
        src = frame[a].to_numpy()
        want = np.array([src[0], src[1], src[1], src[1], src[4], np.nan, np.nan, src[7], src[7]])
        assert np.array_equal(out[h].to_numpy(), want, equal_nan=True), h


@needs_data
@pytest.mark.parametrize("group", GROUPS)
def test_l3_hold_is_backward_only_on_real_groups_with_planted_values(group):
    hook = _hook()
    parts = [pd.read_parquet(FEATURES_TEMPLATE.format(group=group, year=y),
                             columns=["cell_id", "year"] + list(hook.parents() + hook.LAG2_PARENTS) + list(AGLW))
             for y in range(2002, 2024)]
    frame = pd.concat(parts, ignore_index=True)
    frame["cell_id"] = frame["cell_id"].astype(str)
    frame["region"] = group
    frame["_step"] = frame["year"].astype(np.int64)
    yr = frame["year"].to_numpy()
    base = hook.build(frame, KEYS)
    by_2021 = frame[yr == 2021].set_index("cell_id")
    for a, h in zip(AGLW, HOLD):
        early = yr <= 2021
        assert np.array_equal(base.loc[early, h].to_numpy(), frame.loc[early, a].to_numpy(dtype=np.float64),
                              equal_nan=True), h
        for y in (2022, 2023):
            rows = yr == y
            want = by_2021[a].reindex(frame.loc[rows, "cell_id"]).to_numpy(dtype=np.float64)
            assert np.array_equal(base.loc[rows, h].to_numpy(), want, equal_nan=True), (h, y)
            assert np.isfinite(want).mean() > 0.99, (h, y)        # the held layer is really there
    # a value planted in every year after t never enters a row of t or earlier
    for t in (2010, 2020, 2021, 2022):
        planted = frame.copy()
        later = yr > t
        for a in AGLW:
            planted.loc[later, a] = planted.loc[later, a] + 99.0
        got = hook.build(planted, KEYS)
        upto = yr <= t
        for h in HOLD:
            assert np.array_equal(got.loc[upto, h].to_numpy(), base.loc[upto, h].to_numpy(), equal_nan=True), (h, t)
    # the rescaled 2022-2023 layers enter no row at all
    planted = frame.copy()
    for a in AGLW:
        planted.loc[yr >= 2022, a] = -1.0e6
    pd.testing.assert_frame_equal(hook.build(planted, KEYS)[list(HOLD)], base[list(HOLD)])
    # positive control: a value planted in 2021 enters 2021, 2022 and 2023, nothing before
    planted = frame.copy()
    for a in AGLW:
        planted.loc[yr == 2021, a] = planted.loc[yr == 2021, a] + 5.0
    got = hook.build(planted, KEYS)
    for h in HOLD:
        d = got[h].to_numpy() - base[h].to_numpy()
        fin = np.isfinite(d)
        assert np.allclose(d[fin & (yr >= 2021)], 5.0) and np.allclose(d[fin & (yr < 2021)], 0.0), h
