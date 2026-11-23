"""Owner ruling K (OWNER_RULINGS_2026-10-05.md, 2026-10-06: the author's answer, not quoted) on the defo package (tests may name
problems).

  - The K supplementary store D:/defo_features_k/{group}_{year}.parquet is dataset.yaml's SECOND driver store, its
    generated catalog (features/defo_features_k_store_catalog.yaml) is exactly what features/build_store_k.py writes
    and is pinned by sha256; no column is declared by two store catalogs.
  - Every K column declares derived_from, an operation, a backward window and reads_target false; nothing is marked
    verified; a signed entry carries the owner's S5 signature (ruling N, OWNER_RULINGS_2026-10-06.md), which the
    generator carries onto a regenerated entry whose facts are unchanged (never copied from the parent).
  - The lags: K2 one year (epo's window {3, month, centred}, ruling L1 b, merged into the shared panel store catalog
    2026-10-06; the aggregate reaches 31 days past its year); K3 one year from the J2 (b) reach; K4 one year
    from the co-measured fact (assumed) and 0 without it; K5 R8 0 and R4 2 (the declared 'lag k=2 unit=year'), as
    features/build.py's phenology_sos_doy_lag2 (ruling N S28 a), so the package's Y0 (owner ruling J5) is 2004 (S17 a).
  - The verdicts: K1 unchanged (J2 a), K2 / K3 / K5 keep, K4 banned by ruling N S3 (lookahead_unfixable), the raw
    parents banned, one verdict per sum group;
    the K2 December fill and the K3 lineage disclosed in exceptions.yaml.
  - K6 (2026-10-06, after ruling L1 b signed the 13 index windows {3, month, centred}): the 11 index families' yearly
    aggregates (soi, tna, tsa, iod, ao, nao, pna, wp, sam, noi, pdo; 33 columns) are K store columns with
    aggregate_time's facts, R8 one year, verdict keep; their values are the plain calendar-year aggregates (checked
    against a direct computation) and backward only.
  - The store schema: every record carries schema_sha256; a file of an older schema is moved aside into
    <store>/_moved_20261006/<schema>/ and rebuilt, never deleted (one-group test store).
  - BACKWARD ONLY, on two real groups (costa_rica, pearl_river_delta): a planted LATER value never enters a K value
    (K2, K3, K5 through the builder; K1 through features/build.py), and the lag-2 MOD44B column at year t holds year
    t-2 (a value planted at t-2 does enter: the positive control). The K2 fill reads a later month for its PRESENCE
    only: a value planted there leaves the year unchanged, a later month removed empties the December fill
    (disclosed in the store catalog and ban.yaml).
  - The builder end to end on a one-group test store, its resume rule, and the files already built in
    D:/defo_features_k (when present) against a rebuild and the features store's values.
"""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest
import yaml

from conftest import ENGINE_DIR

DEFO = ENGINE_DIR / "datasets" / "defo"
PANEL_CATALOG = "../_stores/monthly_panel_v170_schema_catalog.yaml"
FEATURES_CATALOG = "features/defo_features_store_catalog.yaml"
K_CATALOG = "features/defo_features_k_store_catalog.yaml"
FEATURES_TEMPLATE = "D:/defo_features/{group}_{year}.parquet"
K_TEMPLATE = "D:/defo_features_k/{group}_{year}.parquet"
PANEL_TEMPLATE = "D:/monthly_panel/{group}_monthly_{year}.parquet"
STATS = ("mean", "min", "max")
YEAR = NS(kind="regular", length=1, unit="year")
GROUPS = ("costa_rica", "pearl_river_delta")
K2 = tuple("epo_%s" % s for s in STATS)
K3 = tuple("deeprec_twsa_k3_%s" % s for s in STATS)
K3_RAW = tuple("deeprec_twsa_%s" % s for s in STATS)
K4 = ("modis_landcover_class", "modis_landcover_annual", "shrub_cover_pct_global", "cropland_fraction")
K5_RAW = ("V15_bare_ground_pct", "V17_herb_cover_pct", "tree_cover_pct")
K5 = tuple(p + "_lag2" for p in K5_RAW)
K6_PARENTS = ("soi", "tna", "tsa", "iod", "ao", "nao", "pna", "wp", "sam", "noi", "pdo")
K6 = tuple("%s_%s" % (p, s) for p in K6_PARENTS for s in STATS)
N1_PARENTS = ("pdo",)                   # ruling N1: the panel window carries the ERSSTv5 reach (+2 months)
LAG2_OUTPUTS = ("phenology_sos_doy_lag2",)      # features/build.py, ruling N S28 a
AGLW = ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats", "aglw_total_lsu")
K1_PARENTS = tuple("%s_%s" % (b, s) for b in ("V06_spei_12m", "spei_01m", "spei_03m", "spei_06m", "spei_24m", "amo")
                   for s in STATS)
DATA = Path("D:/monthly_panel").is_dir() and Path("D:/defo_target").is_dir() and Path("D:/defo_features").is_dir()
needs_data = pytest.mark.skipif(not DATA, reason="the defo stores on D: are not reachable")


def _k():
    path = DEFO / "features" / "build_store_k.py"
    spec = importlib.util.spec_from_file_location("defo_build_store_k_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load():
    from treeroute.package.load import load_package
    return load_package(DEFO)


def _target_view(pkg):
    f = pkg.catalog.columns["loss_frac"]
    return NS(name="loss_frac", cadence=YEAR, stamp=f.stamp, window=f.window, computed_from=tuple(f.computed_from),
              fact_status=f.fact_status)


def _lag(pkg, column, facts, co_measured=None):
    from treeroute.timing import compute_lag
    view = NS(name=column, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)
    return compute_lag(view, _target_view(pkg), YEAR, "nowcast").steps


# ------------------------------------------------------------------------------------------------ package
def test_k_store_is_the_second_driver_store_and_its_catalog_is_what_the_builder_writes():
    K = _k()
    pkg = _load()
    assert list(pkg.dataset.stores.drivers) == [FEATURES_TEMPLATE, K_TEMPLATE, PANEL_TEMPLATE]
    assert K.K_TEMPLATE == K_TEMPLATE and K.CATALOG_FILE == K_CATALOG
    assert set(pkg.stores) == {PANEL_CATALOG, FEATURES_CATALOG, K_CATALOG}
    files = K.load_package_files(DEFO)
    sha, entries = K.check_signed_catalog(files)              # the committed file is the generated one, pinned
    assert sha == {i.path: i.sha256 for i in pkg.dataset.includes}[K_CATALOG]
    cat = pkg.stores[K_CATALOG].columns
    assert list(cat) == list(K.columns()) == list(K2 + K3 + K5 + K6) and set(entries) == set(cat)
    for c in cat:
        assert pkg.catalog.columns[c].role == "engineered", c
    seen = {}
    for path, catalog in pkg.stores.items():
        for c in catalog.columns:
            assert c not in seen, "%s declared by %s and %s" % (c, seen[c], path)
            seen[c] = path
    # K1 stays features/build.py's (no second copy), K4 is facts alone (no store column)
    from treeroute.pipeline import data as D
    outputs = D.feature_outputs(D.load_hook(DEFO, D.FEATURE_SCRIPT))
    holds = {a + "_hold2021" for a in AGLW}                     # ruling L3 (tests/test_defo_k_l3_l4.py)
    assert set(outputs) == {p + "_lag1" for p in K1_PARENTS} | holds | set(LAG2_OUTPUTS)
    assert not set(outputs) & set(cat)
    assert not set(K4) & set(cat)


def test_every_k_column_declares_derived_from_operation_and_a_backward_window():
    pkg = _load()
    cat = pkg.stores[K_CATALOG].columns
    panel = pkg.stores[PANEL_CATALOG].columns
    for c, f in cat.items():
        assert f.reads_target is False and f.dtype == "float64" and f.fact_status != "verified", c
        assert (f.cadence.kind, f.cadence.length, f.cadence.unit) == ("regular", 1, "year"), c
        if f.reviewed_by is not None:                          # the owner's S5 signature (ruling N), nothing else
            assert f.reviewed_by == "owner" and f.date == "2026-10-06" and f.fact_status == "assumed", c
            assert "(ruling N, " in f.provenance and "S5)" in f.provenance, c
        assert f.window is not None and f.window.align == "backward", c
    for s, c in zip(STATS, K2):
        f = cat[c]
        assert f.derived_from == ["epo"] and f.operation.startswith("last_value {rule: J2 d") and f.operation.endswith(
            "aggregate_time {window: 1 year, stat: %s}" % s), c
        # the panel's epo window (ruling L1 b, signed there by the owner) carried through aggregate_time; the
        # generated entry is 'assumed' (signed only by the owner's S5 signature, ruling N)
        w = panel["epo"].window
        assert (w.length, w.unit, w.align, panel["epo"].stamp) == (3, "month", "centred", "period_centre")
        assert (f.window.length, f.window.unit, f.window.align, f.stamp) == (1, "year", "backward", "period_end"), c
        assert f.window.reach_after_max.model_dump() == {"value": 31, "unit": "day"}, c
        assert f.fact_status == "assumed" and "December 2023" in f.provenance, c
    for s, c in zip(STATS, K3):
        f = cat[c]
        assert f.derived_from == ["deeprec_twsa"] and f.operation == "aggregate_time {window: 1 year, stat: %s}" % s, c
        assert (f.window.length, f.window.unit, f.window.align, f.stamp) == (1, "year", "backward", "period_end"), c
        assert f.window.reach_after_max is not None and f.window.reach_after_max.model_dump() == {"value": 91, "unit": "day"}
        assert f.fact_status == panel["deeprec_twsa"].fact_status == "assumed", c      # J2 (b), not signed
        assert f.lineage == panel["deeprec_twsa"].lineage, c
    for p, c in zip(K5_RAW, K5):
        f = cat[c]
        assert f.derived_from == [p] and f.operation == "lag k=2 unit=year", c
        assert (f.window.length, f.window.unit, f.window.align, f.stamp) == (2, "year", "backward", "period_start"), c
        # K5 'same sum group, one verdict': the three lag columns form ONE group of their own (the raw trio, banned,
        # keeps the parents' group), so no sum-group name holds two verdicts (APP_PLAN.md 1.4)
        assert panel[p].sum_group == "MOD44B_V15_V17_tree_cover", c
        assert f.sum_group == panel[p].sum_group + "_lag2" == "MOD44B_V15_V17_tree_cover_lag2", c
        assert f.legal_range == panel[p].legal_range and f.fact_status == panel[p].fact_status == "assumed", c
    for c in K6:
        p, s = c.rsplit("_", 1)
        f = cat[c]
        w = panel[p].window                                    # ruling L1 (b), signed in the shared panel catalog
        assert (w.unit, w.align, panel[p].stamp, panel[p].reviewed_by) == ("month", "centred", "period_centre",
                                                                           "owner"), p
        assert f.derived_from == [p] and f.operation == "aggregate_time {window: 1 year, stat: %s}" % s, c
        assert (f.window.length, f.window.unit, f.window.align, f.stamp) == (1, "year", "backward", "period_end"), c
        if p in N1_PARENTS:                                    # ruling N1: the ERSSTv5 reach, carried by aggregate_time
            assert w.reach_after_max.model_dump() == {"value": 2, "unit": "month"} and "ruling N1" in f.provenance, c
            assert f.window.reach_after_max.unit == "day" and f.window.reach_after_max.value > 31, c
        else:
            assert w.length == 3 and w.reach_after_max is None, p
            assert f.window.reach_after_max.model_dump() == {"value": 31, "unit": "day"}, c
        assert f.fact_status == panel[p].fact_status == "assumed" and "K6" in f.provenance, c   # nothing signed here
        assert f.legal_range == panel[p].legal_range and f.lineage == panel[p].lineage, c


def test_k5_declared_window_holds_the_year_t_minus_2_composite_and_ends_before_the_predicted_year():
    """The parent (stamp period_start, {430 day forward}) of year t-2 lies inside the declared content of year t,
    which ends on 31 December t-1, for every store year; a one-year lag would not end before the year (why K5)."""
    from treeroute.timing import content_interval
    K = _k()
    files = K.load_package_files(DEFO)
    _, entries = K.check_signed_catalog(files)
    years = K.B.store_years(files, K.B.target_groups(files))
    assert K.check_k5_windows(files, entries, years) == 3 * len(years)
    p = files.panel.columns["tree_cover_pct"]
    view = NS(name="tree_cover_pct", cadence=p.cadence, stamp=p.stamp, window=p.window, fact_status=p.fact_status)
    for t in years:
        first_t = K._year_period(t)[0]
        assert content_interval(view, K._year_period(t - 1))[1] >= first_t       # lag 1 overlaps the year t
        assert content_interval(view, K._year_period(t - 2))[1] < first_t        # lag 2 ends before it


def test_k_lags_r8_and_r4_and_the_y0_they_give():
    from treeroute.derive import orchestrate as O
    from treeroute.derive import rules as R
    from treeroute.pipeline import data as D
    from treeroute.timing import TimingRefusal, compute_lag

    pkg = _load()
    cols = pkg.catalog.columns
    cat = pkg.stores[K_CATALOG].columns
    panel = pkg.stores[PANEL_CATALOG].columns
    for c in K2:
        assert _lag(pkg, c, cat[c], cols[c].co_measured_with_target) == 1, c    # the 31-day reach past the year
        bare = NS(**dict(vars(cat[c]), window=NS(unit="month", align="unknown", length=None, max_length=None,
                                                 reach_after_max=None, reach_before_max=None)))
        with pytest.raises(TimingRefusal) as err:                    # without a window it would be refused
            _lag(pkg, c, bare)
        assert err.value.rule == "G-LAG"
    for c in K3:
        assert _lag(pkg, c, cat[c], cols[c].co_measured_with_target) == 1, c
    for c in K4:
        f = cols[c]
        assert f.co_measured_with_target is True and f.fact_status == "assumed", c
        assert f.co_measured_evidence.startswith("owner ruling K4"), c
        assert _lag(pkg, c, panel[c], True) == 1 and _lag(pkg, c, panel[c], None) == 0, c
    for c in K5:
        assert _lag(pkg, c, cat[c], cols[c].co_measured_with_target) == 0, c
    for c in K6:
        assert _lag(pkg, c, cat[c], cols[c].co_measured_with_target) == 1, c    # the December value reaches January
    # the whole package as derive_all lags it (feature outputs added), and R4's J5 count
    outputs = D.feature_outputs(D.load_hook(DEFO, D.FEATURE_SCRIPT))
    spec = D.package_spec(D.augment_package(pkg, outputs))
    lags = {}
    for c in spec.tree_features + spec.context:
        f = spec.store_facts[c]
        if f.cadence.kind == "static":
            continue
        lags[c] = compute_lag(NS(name=c, cadence=f.cadence, stamp=f.stamp, window=f.window,
                                 fact_status=f.fact_status, co_measured_with_target=cols[c].co_measured_with_target),
                              _target_view(pkg), YEAR, "nowcast")
    assert sorted({lag.steps for lag in lags.values()}) == [0, 1]
    r4, record = O._r04_lags(NS(store=spec.store_facts), lags)
    assert {c for c, lag in r4.items() if lag.steps == 2} == set(K5) | set(LAG2_OUTPUTS)
    assert all(record["counted"][c]["operation_steps"] == 2 for c in K5 + LAG2_OUTPUTS)
    assert R.derive_r04_first_year(2002, r4).value == 2004        # J5: 2002 (driver stores) + 2 (K5, S28 a)
    two = set(K5) | set(LAG2_OUTPUTS)
    assert R.derive_r04_first_year(2002, {c: lag for c, lag in r4.items() if c not in two}).value == 2003


def test_k_verdicts_as_ruled():
    from treeroute.io.apply import apply_verdicts

    pkg = _load()
    v = pkg.ban.verdicts
    for p in K1_PARENTS:                                         # K1: J2 (a) unchanged
        assert (v[p].verdict, v[p].reason) == ("ban", "incomplete") and v[p + "_lag1"].verdict == "keep", p
    for c in K2:
        assert v[c].verdict == "keep" and "K2" in v[c].reason and "December 2023" in v[c].reason, c
        assert "K2" in v[c].evidence and "L1 b" in v[c].evidence, c
    for c in K3:
        assert v[c].verdict == "keep" and "K3" in v[c].reason, c
    for c in K3_RAW:
        assert (v[c].verdict, v[c].reason) == ("ban", "lookahead_unfixable") and "K3" in v[c].evidence, c
    for c in K4:                                                 # ruling N S3 re-rules K4: banned
        assert (v[c].verdict, v[c].reason) == ("ban", "lookahead_unfixable") and "S3" in v[c].evidence, c
    for c in K5_RAW:
        assert (v[c].verdict, v[c].reason) == ("ban", "coproduct"), c
    for c in K6:                                                 # K6 after L1 (b): conditional -> keep
        assert v[c].verdict == "keep" and "ruling K6" in v[c].reason and "L1 b" in v[c].reason, c
        assert v[c].evidence.startswith("CHANGE 2026-10-06") and "K6" in v[c].evidence, c
    assert len({(v[c].verdict, v[c].reason, v[c].evidence) for c in K5}) == 1 and v[K5[0]].verdict == "keep"
    # one verdict per sum-group NAME across every store catalog the package includes
    groups = {}
    for catalog in pkg.stores.values():
        for c, f in catalog.columns.items():
            if f.sum_group and c in v:
                groups.setdefault(f.sum_group, set()).add((v[c].verdict, v[c].reason))
    assert groups["MOD44B_V15_V17_tree_cover_lag2"] == {("keep", v[K5[0]].reason)}
    assert groups["MOD44B_V15_V17_tree_cover"] == {("ban", "coproduct")}
    # the G-LINEAGE stand-in runs on feature-script outputs only: disclosed for the K store columns (OWNER item)
    lin = [e for e in pkg.exceptions.entries if e.check and e.check.startswith("G-LINEAGE stand-in")]
    assert len(lin) == 1 and lin[0].kind == "disclosed_defect" and lin[0].owner.startswith("UNSIGNED")
    assert all(c in lin[0].check for c in K3 + K5) and all("G-LINEAGE" in v[c].evidence for c in K3 + K5)
    non_key = tuple(c for c, f in pkg.catalog.columns.items() if f.role not in ("key_unit", "key_group", "key_time"))
    sets = apply_verdicts(non_key, dict(v), {c: pkg.catalog.columns[c].role for c in non_key})
    assert set(K2) | set(K3) | set(K5) | set(K6) <= set(sets.tree_features)
    assert not (set(K3_RAW) | set(K5_RAW) | set(K4)) & set(sets.tree_features)
    for prefix, cols_ in (("DeepRec lineage", K3), ("EPO December fill", K2)):
        flags = [e for e in pkg.exceptions.entries if e.check and e.check.startswith(prefix)]
        assert len(flags) == 1 and all(c in flags[0].check for c in cols_), prefix
        assert "signed by the owner 2026-10-06 (ruling N" in flags[0].owner and "S8" in flags[0].owner, prefix


# ------------------------------------------------------------------------------------------------ real data
def _group_data(K, files, group):
    reader = K.B.load_target_reader(files.root)
    tpath = K.B.template_files(files.target_template)[(group,)]
    cells = np.unique(reader.read_target_file(tpath, {"group": group})["cell_id"].astype(str).to_numpy())
    years = K.B.store_years(files, K.B.target_groups(files))
    return cells, years


def _planting_reader(K, real, plant):
    def reader(pkg, group, year, cells):
        frame, codes, steps, masked = real(pkg, group, year, cells)
        return plant(frame.copy(), year, codes), codes, steps, masked
    return reader


@needs_data
@pytest.mark.parametrize("group", GROUPS)
def test_k_values_are_backward_only_with_planted_later_values(group, monkeypatch):
    K = _k()
    files = K.load_package_files(DEFO)
    _, entries = K.check_signed_catalog(files)
    k3_cat = {c: entries[c] for c in K3 + K6}
    cells, years = _group_data(K, files, group)
    real = K.read_panel_year

    def build(t, plant=None):
        monkeypatch.setattr(K, "read_panel_year", real if plant is None else _planting_reader(K, real, plant))
        data = K.GroupData(files, group, cells, years)
        table, record = K.build_group_year(files, data, t, k3_cat)
        return table, record

    for t in (2010, 2022):
        base, rec = build(t)
        assert rec["epo_months_filled_in_year"] == len(cells) and rec["epo_months_missing_after_fill"] == 0

        def later(frame, year, codes, t=t):                    # every value of a LATER year replaced, presence kept
            if year > t:
                for c in ("epo", "deeprec_twsa") + K5_RAW + K6_PARENTS:
                    v = frame[c].to_numpy(dtype=np.float64)
                    frame[c] = np.where(np.isfinite(v), v + 77.0, v)
            return frame
        planted, _ = build(t, later)
        pd.testing.assert_frame_equal(base, planted)

        # K5 positive control: a value planted at t-2 enters year t's lag-2 column, one planted at t-1 or t does not
        def at(offset):
            def plant(frame, year, codes, t=t):
                if year == t - offset:
                    for c in K5_RAW:
                        frame[c] = frame[c].to_numpy(dtype=np.float64) + 5.0
                return frame
            return plant
        for offset in (1, 0):
            pd.testing.assert_frame_equal(base, build(t, at(offset))[0])
        moved, _ = build(t, at(2))
        for c in K5:
            assert np.allclose(moved[c].to_numpy() - base[c].to_numpy(), 5.0), c
        # the lag-2 column at t holds year t-2: equal to the features store's annual value of t-2
        old = pd.read_parquet(FEATURES_TEMPLATE.format(group=group, year=t - 2), columns=["cell_id"] + list(K5_RAW))
        assert old.cell_id.astype(str).tolist() == base.cell_id.tolist()
        for p, c in zip(K5_RAW, K5):
            assert np.array_equal(base[c].to_numpy(), old[p].to_numpy(dtype=np.float64), equal_nan=True), c
        # K3 equals the features store's aggregate of the same year (same values, new facts)
        same = pd.read_parquet(FEATURES_TEMPLATE.format(group=group, year=t), columns=list(K3_RAW))
        for r, c in zip(K3_RAW, K3):
            assert np.array_equal(base[c].to_numpy(), same[r].to_numpy(dtype=np.float64), equal_nan=True), c
        # K6: the plain calendar-year mean / min / max of the 12 monthly values of year t (D34 strict), every cell
        idx = pd.read_parquet(PANEL_TEMPLATE.format(group=group, year=t), columns=["cell_id", "month"] + list(K6_PARENTS))
        for p in K6_PARENTS:
            m = idx.pivot(index="cell_id", columns="month", values=p).reindex(base.cell_id).to_numpy(np.float64)
            assert m.shape[1] == 12 and np.isfinite(m).all(), p
            for s in STATS:
                assert np.allclose(base["%s_%s" % (p, s)].to_numpy(), getattr(m, s)(axis=1), rtol=0, atol=1e-12), (p, s)
        # K2: December takes November (D34 strict over the 12 filled months), checked against a direct computation
        panel = pd.read_parquet(PANEL_TEMPLATE.format(group=group, year=t), columns=["cell_id", "month", "epo"])
        m = panel.pivot(index="cell_id", columns="month", values="epo").reindex(base.cell_id).to_numpy(np.float64)
        assert np.isnan(m[:, 11]).all() and np.isfinite(m[:, :11]).all()
        m[:, 11] = m[:, 10]
        for s, c in zip(STATS, K2):
            assert np.allclose(base[c].to_numpy(), getattr(m, s)(axis=1), rtol=0, atol=1e-12), c

        def november(frame, year, codes, t=t):                 # positive control: November of t feeds December
            if year == t:
                e = frame["epo"].to_numpy(dtype=np.float64).copy()
                e[frame["month"].to_numpy() == 11] += 1.0
                frame["epo"] = e
            return frame
        nov, _ = build(t, november)
        assert (nov["epo_max"].to_numpy() >= base["epo_max"].to_numpy()).all()
        assert np.allclose(nov["epo_mean"].to_numpy() - base["epo_mean"].to_numpy(), 2.0 / 12.0, atol=1e-9)

        def later_months_gone(frame, year, codes, t=t, months=(1, 2)):   # PRESENCE of a later month decides the fill
            if year == t + 1:
                e = frame["epo"].to_numpy(dtype=np.float64).copy()
                e[np.isin(frame["month"].to_numpy(), months)] = np.nan
                frame["epo"] = e
            return frame
        # January t+1 missing too: December and January form a 2-month gap closed by February, still filled
        pd.testing.assert_frame_equal(base, build(t, lambda f, y, c: later_months_gone(f, y, c, months=(1,)))[0])
        # January and February t+1 missing: a 3-month gap, longer than the 2-month maximum, left to R30 whole
        gone, rec_gone = build(t, later_months_gone)
        assert np.isnan(gone[list(K2)].to_numpy()).all() and rec_gone["epo_months_filled_in_year"] == 0
        pd.testing.assert_frame_equal(base.drop(columns=list(K2)), gone.drop(columns=list(K2)))
    # 2023: December is the record's tail, never filled: the 2023 aggregates are empty in every cell
    last, rec = build(2023)
    assert np.isnan(last[list(K2)].to_numpy()).all() and rec["epo_months_filled_in_year"] == 0
    first, _ = build(2002)
    assert np.isnan(first[list(K5)].to_numpy()).all() and np.isfinite(first[list(K2)].to_numpy()).all()


@needs_data
def test_k1_lag1_columns_are_backward_only_on_two_real_groups():
    """features/build.py (K1 = J2 a) on the real features-store rows of two groups: year t holds the same cell's
    year t-1 aggregate, and values planted in every later year change nothing at t."""
    from treeroute.pipeline import data as D

    hook = D.load_hook(DEFO, D.FEATURE_SCRIPT)
    keys = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year"}}
    for group in GROUPS:
        parts = [pd.read_parquet(FEATURES_TEMPLATE.format(group=group, year=y), columns=["cell_id", "year"] + list(
            K1_PARENTS) + list(AGLW) + ["phenology_sos_doy"]) for y in range(2002, 2024)]
        frame = pd.concat(parts, ignore_index=True)
        frame["cell_id"] = frame["cell_id"].astype(str)
        frame["region"] = group
        frame["_step"] = frame["year"].astype(np.int64)
        base = hook.build(frame, keys)
        for t in (2010, 2020, 2023):
            planted = frame.copy()
            later = planted["year"].to_numpy() > t
            for p in K1_PARENTS:
                planted.loc[later, p] = planted.loc[later, p] + 99.0
            got = hook.build(planted, keys)
            rows = frame["year"].to_numpy() == t
            prev = frame[frame["year"] == t - 1].set_index("cell_id")
            for p in K1_PARENTS:
                c = p + "_lag1"
                assert np.array_equal(got.loc[rows, c].to_numpy(), base.loc[rows, c].to_numpy(), equal_nan=True), c
                want = prev[p].reindex(frame.loc[rows, "cell_id"]).to_numpy(dtype=np.float64)
                assert np.array_equal(base.loc[rows, c].to_numpy(), want, equal_nan=True), (group, t, c)
        assert np.isfinite(base.loc[frame["year"].to_numpy() == 2023, "amo_mean_lag1"].to_numpy()).all()


@needs_data
def test_build_writes_resumes_and_refuses_a_changed_input_on_a_one_group_test_store(tmp_path):
    K = _k()
    out = tmp_path / "k_store"
    lines = []
    K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lines.append)
    assert "22 files written,  0 kept" in lines[-1]
    files = sorted(out.glob("costa_rica_*.parquet"))
    assert len(files) == 22
    table = pd.read_parquet(files[0])
    assert list(table.columns) == ["cell_id", "year"] + list(K.columns())
    lines.clear()
    K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lines.append)
    assert " 0 files written, 22 kept" in lines[-1]
    rec_path = out / "_build" / "costa_rica_2010.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["content_sha256"] == K.content_sha256() and rec["build_store_content_sha256"] == K.B.content_sha256()
    vf = K.value_facts(K.load_package_files(DEFO))
    assert rec["value_facts"] == vf and set(vf) == {"epo", "deeprec_twsa"} | set(K5_RAW) | set(K6_PARENTS)
    assert rec["schema_sha256"] == K.schema_sha256() == K.file_schema_sha256(str(files[0]))
    assert all(set(f) == {"cadence", "fill_values", "near_sentinel_optout"} for f in vf.values())
    assert sorted(rec["panel_files"]) == sorted(PANEL_TEMPLATE.format(group="costa_rica", year=y)
                                                for y in (2008, 2009, 2010, 2011))
    # a parent's fill facts enter the values (mask_sentinels): a record built under other facts is refused
    other = json.loads(json.dumps(rec["value_facts"]))
    other["epo"]["fill_values"] = other["epo"]["fill_values"] + [-1.0e9]
    for key, value in (("content_sha256", "0" * 64), ("target_sha256", "0" * 64), ("value_facts", other),
                       ("panel_files", {"x": [1, 2]}), ("file_size", 1)):
        changed = dict(rec, **{key: value})
        rec_path.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(K.BuildError, match=key):
            K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lambda s: None)
    rec_path.write_text(json.dumps({k: x for k, x in rec.items() if k != "value_facts"}), encoding="utf-8")
    with pytest.raises(K.BuildError, match="value_facts None"):      # a record from before the key: refused
        K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lambda s: None)
    rec_path.write_text(json.dumps(rec), encoding="utf-8")
    K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lambda s: None)
    with pytest.raises(K.BuildError, match="groups without a target file"):
        K.build(DEFO, groups=["no_such_group"], out_root=str(out), echo=lambda s: None)
    # a file of an OLDER store schema (here: the pre-K6 column list) is moved aside with its record and rebuilt
    old = out / "costa_rica_2011.parquet"
    old_rec = out / "_build" / "costa_rica_2011.json"
    stale = pd.read_parquet(old)[["cell_id", "year"] + list(K2 + K3 + K5)]
    old.unlink()                                              # the test's own temporary store
    stale.to_parquet(old, index=False)
    old_schema = K.file_schema_sha256(str(old))
    assert old_schema != K.schema_sha256()
    lines.clear()
    K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lines.append)
    assert " 1 files written, 21 kept |  1 stale moved aside" in lines[-1]
    aside = out / "_moved_20261006" / old_schema[:12]
    assert list(pd.read_parquet(aside / "costa_rica_2011.parquet").columns) == list(stale.columns)
    assert (aside / "_build" / "costa_rica_2011.json").is_file() and old_rec.is_file()
    assert K.file_schema_sha256(str(old)) == K.schema_sha256()
    # a second stale file of the same name is refused, never overwritten
    old.unlink()
    stale.to_parquet(old, index=False)
    with pytest.raises(K.BuildError, match="already exist"):
        K.build(DEFO, groups=["costa_rica"], out_root=str(out), echo=lambda s: None)


def _built_k_files():
    folder = Path(K_TEMPLATE).parent
    out = []
    for g in GROUPS:
        for y in (2002, 2010, 2022, 2023):
            f = folder / ("%s_%d.parquet" % (g, y))
            r = folder / "_build" / ("%s_%d.json" % (g, y))
            if f.is_file() and r.is_file():
                out.append((g, y, f, r))
    return out


@needs_data
@pytest.mark.skipif(not _built_k_files(), reason="D:/defo_features_k holds no built file of the two groups")
def test_built_k_files_are_kept_by_the_resume_rule_and_equal_a_rebuild():
    K = _k()
    files = K.load_package_files(DEFO)
    _, entries = K.check_signed_catalog(files)
    targets = K.B.template_files(files.target_template)
    stale = 0
    for group, year, path, rec_path in _built_k_files():
        cells, years = _group_data(K, files, group)
        tpath = targets[(group,)]
        if K.file_schema_sha256(str(path)) != K.schema_sha256():
            # built before the store's current schema (K6 added 33 columns on 2026-10-06): the builder detects it by
            # its schema hash, moves it aside and rebuilds it (tests never write to the real store)
            assert K.schema_sha256(["cell_id", "year"] + list(K2 + K3 + K5)) == K.file_schema_sha256(str(path)), path
            stale += 1
            continue
        now = {"schema_sha256": K.schema_sha256(), "content_sha256": K.content_sha256(),
               "build_store_content_sha256": K.B.content_sha256(),
               "engine_code_sha256": K.engine_code_sha256(), "value_facts": K.value_facts(files), "target_file": tpath,
               "target_sha256": K.B.sha256_file(tpath), "panel_files": K.panel_dependencies(group, year, years)}
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        assert K.resume_check(rec, K_TEMPLATE.format(group=group, year=year), group, year, now) is None, path
        table = pd.read_parquet(path)
        rebuilt, _ = K.build_group_year(files, K.GroupData(files, group, cells, years), year,
                                        {c: entries[c] for c in K3 + K6})
        pd.testing.assert_frame_equal(table.reset_index(drop=True), rebuilt.reset_index(drop=True), check_dtype=False)
        if year == 2023:
            assert np.isnan(table[list(K2)].to_numpy()).all()
        else:
            assert np.isfinite(table[list(K2)].to_numpy()).all()
