"""The NDVI package's own code (tests may name problems): the target reader
(datasets/ndvi/ingest/target_reader.py: V11_mean_ndvi from the monthly panel, fills to NaN), the feature
script (datasets/ndvi/features/build.py: run89's driver lags for the 69 bases ban.yaml keeps (345; owner ruling J4
drops the 18 banned bases), the 6 engineered lag-12 columns of owner ruling J2 (a), 28 water-memory columns and
9 router-context columns, rebuilt date-safe) and the static-table builder (datasets/ndvi/ingest/build_static.py).
The J ban list itself (OWNER_RULINGS_2026-10-05.md section J) is checked in tests/test_ndvi_package_ban.py.

What is checked:
  - every output is a valid store-catalog column with derived_from, operation, a backward-only window and
    reads_target false, and has a catalog row in the NDVI catalog (the lag rows were added with the J ban list);
  - DATE SAFETY through R8: for every lag of a base column, R8's lag of the output plus the lag order k is
    at least R8's lag of the base, and exactly max(0, lag(base) - k) + k where the base's lag is known: the
    composed facts carry the base's content reach (a centred or filtered index keeps what is left of it),
    and a lag of an unknown-window column is refused like its base (G-LAG);
  - TRAILING ONLY: changing any source after a step never changes an output at or before it;
  - the values against a pandas re-implementation of run89's builder (bundle_lag_compare.build_feats_ext)
    on a synthetic dense panel, with the documented departures (NaN run lengths before the first event and
    after a missing month);
  - CALENDAR ONLY: a missing month is missing, never the neighbouring row; an unsorted or repeated
    (unit, step) frame is refused;
  - the saved run89 feature list (read-only; skipped where D:/run89full is absent) is the script's RUN89_LAG_BASES,
    and LAG_BASES is it minus DROPPED_LAG_BASES;
  - LINEAGE (a stand-in for G-LINEAGE on store columns, which is not built): a store column trained on the
    target (clf_dry, clf_wet) is never kept in either package's ban.yaml, and no feature output reads it;
  - the target reader refuses a key without a year, checks every unit id, counts infinite labels and masks
    MOD13C2's own fill (-0.3) in every float form; the static builder checks every year's cell set and every
    row's lat/lon.
Synthetic files live under the test's temp folder; read-only checks on real files are skipped where the
store is absent.

REVISED 2026-10-06 for ruling L (OWNER_RULINGS_2026-10-05.md section L): the 13 index windows are signed
{3, month, centred} (L1 b), so no base or lag is refused at R8 any more; the six J2 (a) lag-12 outputs carry the
owner's signature of their composed window (L1 c); six yearly outputs <aglw_*>_hold2021 hold the real 2021
livestock layer for 2022-2023 (L3; checked in tests/test_ndvi_package_ban.py and below).
"""

import functools
import math
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

NDVI = ENGINE_DIR / "datasets" / "ndvi"
DRAFT = ENGINE_DIR / "datasets" / "ndvi_draft"
PANEL = Path("D:/monthly_panel")
RUN89_FEATS = Path("D:/run89full/sandbox/sandbox_thar_desert.npz")
MONTH = NS(kind="regular", length=1, unit="month")
KEYS = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year", "month": "month"}}


@functools.lru_cache(maxsize=None)
def _hook(rel):
    from treeroute.pipeline.data import load_hook

    return load_hook(NDVI, rel)


@functools.lru_cache(maxsize=None)
def _outputs():
    from treeroute.pipeline.data import feature_outputs

    return feature_outputs(_hook("features/build.py"))


@functools.lru_cache(maxsize=None)
def _package():
    from treeroute.package.load import load_package

    return load_package(NDVI)


def _target():
    t = _package().catalog.columns["V11_mean_ndvi"]
    return NS(name="V11_mean_ndvi", cadence=MONTH, stamp=t.stamp, window=t.window, computed_from=())


def _lag(name, facts, co_measured=False):
    """R8's lag of a column (an int), or the refusing rule."""
    from treeroute.timing import TimingRefusal, compute_lag

    view = NS(name=name, cadence=facts.cadence, stamp=facts.stamp, window=facts.window,
              fact_status=facts.fact_status, co_measured_with_target=co_measured)
    try:
        return compute_lag(view, _target(), MONTH, "nowcast").steps
    except TimingRefusal as err:
        return err.rule


def _store_facts():
    out = {}
    for cat in _package().stores.values():
        out.update(cat.columns)
    return out


# ------------------------------------------------------------------------------------------------
# the target reader
def _panel_file(path, group, year, values, region=None, ids=None):
    n = len(values)
    pd.DataFrame({"cell_id": ids if ids is not None else ["%s_%d_%d" % (group, i, i + 1) for i in range(n)],
                  "region": [region or group] * n, "year": np.full(n, year, dtype=np.int64),
                  "month": (np.arange(n) % 12 + 1).astype(np.int64), "lat": np.zeros(n), "lon": np.zeros(n),
                  "V11_mean_ndvi": np.asarray(values, dtype=np.float32)}).to_parquet(path, index=False)


def test_the_target_reader_masks_the_panel_fills_and_keeps_out_of_range_values(tmp_path, capsys):
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_monthly_2010.parquet"
    _panel_file(path, "g_one", 2010, [0.5, -32768.0, np.nan, 0.25, -2147483648.0, 1.2, -32767.0, np.inf, -np.inf])
    out = reader.read_target_file(str(path), {"group": "g_one", "year": 2010})
    assert list(out.columns) == ["cell_id", "region", "year", "month", "V11_mean_ndvi"]
    y = out["V11_mean_ndvi"].to_numpy()
    assert np.isnan(y[[1, 2, 4, 6, 7, 8]]).all() and np.allclose(y[[0, 3, 5]], [0.5, 0.25, 1.2])
    text = capsys.readouterr().out
    assert "2 infinite values masked to NaN" in text                       # counted, never silent
    assert "3 values at a panel fill code" in text
    assert "1 of 3 valid labels outside the legal range" in text          # counted, never masked
    assert out["year"].dtype == np.int64 and out["month"].dtype == np.int64
    assert (out["region"] == "g_one").all()


@pytest.mark.parametrize("dtype", [np.float32, np.float64])
def test_the_target_reader_masks_the_products_own_fill(tmp_path, capsys, dtype):
    """MOD13C2's NDVI fill (raw -3000, -0.3 after the 1e-4 scale) is masked and counted in every float form it can
    take (the ingest's float32 product, float32(-0.3), float64 -0.3); a raw value outside the valid range that
    is no fill code (-2999, -2001, 10001) is counted as out of range and left to D95, never masked."""
    reader = _hook("ingest/target_reader.py")
    assert reader.PRODUCT_FILL == -0.3 and reader.PRODUCT_FILL_TOL == 1e-6
    fills = [float(np.float32(-3000) * np.float32(1e-4)), float(np.float32(-0.3)), -0.3]
    others = [float(np.float32(r) * np.float32(1e-4)) for r in (-2999, -2001, 10001, -2000, 10000, 5000)]
    values = np.asarray(fills + others, dtype=dtype)
    path = tmp_path / "g_one_monthly_2010.parquet"
    n = len(values)
    pd.DataFrame({"cell_id": ["g_one_%d_0" % i for i in range(n)], "region": ["g_one"] * n,
                  "year": np.full(n, 2010, dtype=np.int64), "month": (np.arange(n) % 12 + 1).astype(np.int64),
                  "V11_mean_ndvi": values}).to_parquet(path, index=False)
    y = reader.read_target_file(str(path), {"group": "g_one", "year": 2010})["V11_mean_ndvi"].to_numpy()
    assert np.isnan(y[:3]).all()
    assert np.array_equal(y[3:], values[3:].astype(np.float64))                # nothing else is touched
    text = capsys.readouterr().out
    assert "3 values at MOD13C2's fill (raw -3000, -0.3) masked to NaN" in text
    assert "3 of 6 valid labels outside the legal range" in text            # -2999, -2001, 10001: D95 decides


@pytest.mark.parametrize("key,region,match", [({"year": 2010}, None, "no group"),
                                              ({"group": "g_one", "year": 2010}, "g_two", "regions"),
                                              ({"group": "g_one", "year": 2011}, None, "rows of years"),
                                              ({"group": "g_one"}, None, "no year"),
                                              ({"group": "g_one", "year": None}, None, "no year"),
                                              ({"group": "g_one", "year": "20x0"}, None, "not an integer")])
def test_the_target_reader_refuses_a_mismatched_file(tmp_path, key, region, match):
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_monthly_2010.parquet"
    _panel_file(path, "g_one", 2010, [0.1, 0.2], region=region)
    with pytest.raises(reader.TargetReadError, match=match):
        reader.read_target_file(str(path), key)


def test_the_target_reader_accepts_the_year_as_the_listing_reads_it(tmp_path):
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_monthly_2010.parquet"
    _panel_file(path, "g_one", 2010, [0.1, 0.2])
    out = reader.read_target_file(str(path), {"group": "g_one", "year": "2010"})
    assert (out["year"] == 2010).all()


def test_the_target_reader_checks_every_unit_id_not_a_sample(tmp_path):
    """A wrong id far past the first 50 distinct ids (and a missing id) is refused."""
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_monthly_2010.parquet"
    ids = ["g_one_%d_0" % i for i in range(300)]
    ids[250] = "g_two_250_0"
    _panel_file(path, "g_one", 2010, np.full(300, 0.3), ids=ids)
    with pytest.raises(reader.TargetReadError, match="1 unit ids do not carry the group"):
        reader.read_target_file(str(path), {"group": "g_one", "year": 2010})
    ids[250] = None
    _panel_file(path, "g_one", 2010, np.full(300, 0.3), ids=ids)
    with pytest.raises(reader.TargetReadError, match="1 unit ids do not carry the group"):
        reader.read_target_file(str(path), {"group": "g_one", "year": 2010})


def test_the_target_reader_fill_codes_are_the_store_catalogs():
    reader = _hook("ingest/target_reader.py")
    facts = _store_facts()["V11_mean_ndvi"]
    assert sorted(reader.PANEL_FILLS) == sorted(float(v) for v in facts.fill_values)
    assert reader.LEGAL_RANGE == tuple(_package().catalog.columns["V11_mean_ndvi"].legal_range)


@pytest.mark.skipif(not PANEL.is_dir(), reason="the monthly panel is not on this machine")
def test_the_target_reader_on_one_real_file_is_read_only_and_clean():
    import os

    reader = _hook("ingest/target_reader.py")
    path = PANEL / "thar_desert_monthly_2010.parquet"
    if not path.is_file():
        pytest.skip("no thar_desert 2010 file")
    before = os.stat(path).st_mtime_ns
    out = reader.read_target_file(str(path), {"group": "thar_desert", "year": 2010})
    assert os.stat(path).st_mtime_ns == before
    y = out["V11_mean_ndvi"].to_numpy()
    ok = np.isfinite(y)
    assert ok.mean() > 0.99 and ((y[ok] >= -0.2) & (y[ok] <= 1.0)).all()
    assert set(out["month"]) == set(range(1, 13)) and (out["region"] == "thar_desert").all()
    assert out["cell_id"].str.startswith("thar_desert_").all()


# ------------------------------------------------------------------------------------------------
# the store lineage of the target (stand-in for G-LINEAGE on store columns)
def _trained_on_target(pkg):
    """Catalog columns whose store-catalog lineage is trained_on (or assimilates) the package's target."""
    (target,) = [c for c, f in pkg.catalog.columns.items() if f.role == "target"]
    store = {}
    for cat in pkg.stores.values():
        store.update(cat.columns)
    return sorted(c for c in pkg.catalog.columns
                  if c in store and store[c].lineage is not None
                  and target in tuple(store[c].lineage.trained_on) + tuple(store[c].lineage.assimilates))


def _lineage_violations(trained, verdicts):
    """(column, verdict) of every trained-on-target column that has a verdict other than a target_derived ban."""
    out = []
    for c in trained:
        v = verdicts.get(c)
        if v is None:
            continue
        verdict = getattr(v.verdict, "value", v.verdict)
        if verdict != "ban" or v.reason != "target_derived":
            out.append((c, verdict, v.reason))
    return out


@pytest.mark.parametrize("root", [NDVI, DRAFT], ids=["ndvi", "ndvi_draft"])
def test_a_store_column_trained_on_the_target_is_never_kept(root):
    """G-LINEAGE is not built for store columns: treeroute.pipeline.data.check_feature_lineage checks only the
    feature script's sources, so a 'keep' on a store column whose lineage is trained_on (or assimilates) the
    target would pass the engine with no refusal. This package check stands in for it (keep it in the owner's
    Q34 checklist): every catalog column whose store-catalog lineage names the package's target must be BANNED
    (target_derived) in ban.yaml. A missing verdict is accepted only while ban.yaml does not close the catalog
    (a placeholder, which the engine refuses whole, G-CLOSED; both packages close it today); keep, conditional
    or any other verdict fails. No feature output may be derived from such a column either."""
    from treeroute.package.load import load_package
    from treeroute.pipeline.data import feature_outputs, load_hook, package_spec

    pkg = load_package(root)
    trained = _trained_on_target(pkg)
    assert trained == ["clf_dry", "clf_wet"]            # the store catalog's regime classifiers on NDVI
    assert _lineage_violations(trained, pkg.ban.verdicts) == []
    if any(c not in pkg.ban.verdicts for c in trained):  # only a placeholder ban.yaml may leave them out
        with pytest.raises(Exception) as err:
            package_spec(pkg)
        assert getattr(err.value, "rule", None) == "G-CLOSED", err.value
    outputs = feature_outputs(load_hook(root, "features/build.py"))
    assert not [(c, f.derived_from) for c, f in outputs.items() if set(f.derived_from) & set(trained)]
    # the check itself catches a keep and a conditional (negative control)
    keep = NS(verdict="keep", reason="DRAFT: shipped verdict 'keep'")
    cond = NS(verdict="conditional", reason="anything")
    assert _lineage_violations(trained, {"clf_dry": keep, "clf_wet": cond}) == [
        ("clf_dry", "keep", keep.reason), ("clf_wet", "conditional", "anything")]


# ------------------------------------------------------------------------------------------------
# the feature script: declarations
L3_HOLD = tuple("%s_hold2021" % c for c in ("aglw_cattle", "aglw_buffalo", "aglw_horse", "aglw_sheep", "aglw_goats",
                                             "aglw_total_lsu"))
L1_SIGNATURE = ("assumed", "owner", "2026-10-06")


def test_the_feature_script_declares_every_output_as_a_store_column():
    script = _hook("features/build.py")
    outputs = _outputs()
    lags = [script.lag_column(b, k) for k in script.LAG_ORDERS for b in script.LAG_BASES]
    lags += [script.lag_column(b, script.LAG12_ORDER) for b in script.LAG12_BASES]
    rolls = [script.roll_column(v, w) for v in script.WATER_VARS for w in script.ROLL_WINDOWS]
    others = ["precip_wytd", "api_precip", "api_soilmoist", "soil_water_tc_mm_wytd", "V30_soil_moisture_pct_wytd",
              "V07_total_ref_ET_mm_wytd", "aet_total_mm_wytd", "climate_water_deficit_mm_wytd",
              "consec_dry_months", "months_since_sig_rain"]
    ctx = ["ctx:sin1", "ctx:cos1", "ctx:sin2", "ctx:cos2", "ctx:top5:sph_kgkg_lag6", "ctx:top5:era5l_slhf_lag1",
           "ctx:top5:V07_total_ref_ET_mm_lag1", "ctx:top5:era5l_d2m", "ctx:top5:V01_mean_temp_C"]
    assert len(lags) == len(set(lags)) == 345 + 6 and len(rolls) == 18
    assert len(script.LAG_BASES) == 69 and len(script.RUN89_LAG_BASES) == 87
    assert sorted(outputs) == sorted(lags + rolls + others + ctx + list(L3_HOLD))
    for c, f in outputs.items():
        assert f.reads_target is False and len(f.derived_from) == 1 and f.operation, c
        assert f.window is not None and f.window.align in ("backward", "unknown"), c
        if f.window.align == "backward":
            assert f.stamp == "period_end" and f.window.reach_before_max is None, c
        unit = "year" if c in L3_HOLD else "month"       # L3: the hold keeps its yearly parent's cadence
        assert f.cadence.kind == "regular" and f.cadence.length == 1 and f.cadence.unit == unit, c
    assert "ctx:climatology" not in outputs                 # reads the target: replaced by the engine's normal


def test_every_output_has_a_catalog_row_with_its_role():
    """Every output has its own row in the NDVI catalog (the lag rows were added with the J ban list, so the
    engine's G-CLOSED check finds a row and a verdict for each), and the catalog declares no engineered or
    router-context column the script does not build, except the copy of the normal (banned, replaced_by_engine)."""
    script = _hook("features/build.py")
    ndvi = _package().catalog.columns
    for c in _outputs():
        assert c in ndvi, c
        assert ndvi[c].role == ("router_context" if c.startswith("ctx:") else "engineered"), c
    built = {c for c, f in ndvi.items() if f.role in ("engineered", "router_context")}
    assert built - set(_outputs()) == set()                 # ruling N S11: the ctx:climatology row is removed
    dropped = {script.lag_column(b, k) for k in script.LAG_ORDERS for b in script.DROPPED_LAG_BASES}
    dropped -= {script.lag_column(b, script.LAG12_ORDER) for b in script.LAG12_BASES}
    assert len(dropped) == 18 * 5 - 6 and not dropped & set(ndvi)   # no row for a lag the script no longer builds
    top5 = {c for c, f in ndvi.items() if f.data_selected is not None}
    assert top5 == {c for c, _, _ in script.TOP5}


def test_the_sources_are_the_panels_monthly_columns():
    script = _hook("features/build.py")
    store = _package().stores["../_stores/monthly_panel_v170_schema_catalog.yaml"].columns
    for c, f in _outputs().items():
        (src,) = f.derived_from
        if c.startswith("ctx:") and src == "month":
            continue
        assert src in store and src in _package().catalog.columns, (c, src)
        unit = "year" if c in L3_HOLD else "month"
        assert store[src].cadence.kind == "regular" and store[src].cadence.unit == unit, (c, src)
    assert set(script.WATER_VARS) <= set(store)


def test_facts_are_inherited_from_the_source():
    script = _hook("features/build.py")
    store = _store_facts()
    signed_lag12 = {script.lag_column(b, script.LAG12_ORDER) for b in script.LAG12_BASES}
    for c, f in _outputs().items():
        (src,) = f.derived_from
        if src == "month":
            continue
        s = store[src]
        assert f.scope == s.scope, c
        if c in signed_lag12:                       # L1 c: the owner signed the composed window of the lag-12 columns
            assert (f.fact_status, f.reviewed_by, f.date) == L1_SIGNATURE, c
        else:                                       # ruling N S5 (OWNER_RULINGS_2026-10-06.md N) signed every other
            assert (f.fact_status, f.reviewed_by, f.date) == L1_SIGNATURE, c         # output's facts
            assert "ruling N" in f.provenance, c
            if c in L3_HOLD:
                assert s.reviewed_by == "owner", c # the parent aglw_* fact is signed (L1 c)
        if f.operation.startswith(("lag", "trailing_mean", "cumulative stat=ewm")):
            assert f.legal_range == s.legal_range and f.units == s.units, c
    wytd = _outputs()["precip_wytd"]
    assert wytd.legal_range == (0.0, 12 * store["V02_total_precip_mm"].legal_range[1])
    assert _outputs()["consec_dry_months"].legal_range == (0.0, math.inf)


# ------------------------------------------------------------------------------------------------
# DATE SAFETY through R8
def test_every_lag_ends_at_or_before_the_issue_step():
    """lag(output) + k >= lag(base) for every lag output (so its content never reaches past what the base
    itself may show), with equality to max(0, lag(base) - k) + k: nothing the base may show is lost."""
    script = _hook("features/build.py")
    store = _store_facts()
    outputs = _outputs()
    pairs = [(script.lag_column(b, k), b, k) for k in script.LAG_ORDERS for b in script.LAG_BASES]
    pairs += [(script.lag_column(b, script.LAG12_ORDER), b, script.LAG12_ORDER) for b in script.LAG12_BASES]
    pairs += list(script.TOP5)
    refused = []
    for column, base, k in pairs:
        base_lag = _lag(base, store[base])
        out_lag = _lag(column, outputs[column])
        if base_lag == "G-LAG":
            assert out_lag == "G-LAG", column
            refused.append(base)
            continue
        assert isinstance(out_lag, int), (column, out_lag)
        assert out_lag == max(0, base_lag - k), (column, base_lag, k, out_lag)
    assert refused == []          # ruling L1 (b): the 13 index windows that R8 refused are signed


def test_the_ruled_index_lags_and_their_lag_columns():
    store, outputs = _store_facts(), _outputs()
    assert {c: _lag(c, store[c]) for c in ("sst_anom_nino34", "nino34", "oni", "tni", "co2", "soi")} == {
        "sst_anom_nino34": 2, "nino34": 2, "oni": 3, "tni": 3, "co2": 1, "soi": 1}       # soi: L1 b
    got = {c: _lag(c, outputs[c]) for c in ("sst_anom_nino34_lag1", "sst_anom_nino34_lag2", "nino34_lag1",
                                            "oni_lag1", "oni_lag2", "oni_lag3", "tni_lag1", "tni_lag2",
                                            "V01_mean_temp_C_lag1", "soi_lag12", "spei_03m_lag12", "amo_lag12")}
    assert got == {"sst_anom_nino34_lag1": 1, "sst_anom_nino34_lag2": 0, "nino34_lag1": 1, "oni_lag1": 2,
                   "oni_lag2": 1, "oni_lag3": 0, "tni_lag1": 2, "tni_lag2": 1,
                   "V01_mean_temp_C_lag1": 0, "soi_lag12": 0, "spei_03m_lag12": 0, "amo_lag12": 0}
    assert "co2_lag1" not in outputs                   # co2 is banned (trend_proxy): J4 drops its lags


def test_the_water_memory_and_context_columns_are_at_lag_zero():
    outputs = _outputs()
    for c, f in outputs.items():
        if f.operation.startswith(("trailing_mean", "cumulative", "years_since", "calendar_harmonic")):
            assert _lag(c, f) == 0, c
    for c in ("ctx:top5:sph_kgkg_lag6", "ctx:top5:era5l_d2m", "ctx:top5:V01_mean_temp_C"):
        assert _lag(c, outputs[c]) == 0, c


def test_a_bound_signed_on_a_source_flows_into_its_lags():
    """The composition is generic: a source with a signed bound (align unknown, max_length 5 months,
    assumed: content forward from the stamp, D20) gives lag outputs whose R8 lag is never below
    max(0, lag(base) - k). The bound ends mid-month, so the output's reach is written in days (the largest
    over the reference months), which may cost at most one step more; never one less."""
    from treeroute.package.schema import StoreColumn

    script = _hook("features/build.py")
    src = StoreColumn.model_validate({
        "dtype": "float32", "units": "1", "cadence": {"kind": "regular", "length": 1, "unit": "month"},
        "scope": "global", "stamp": "period_centre", "window": {"align": "unknown", "max_length": 5, "unit": "month"},
        "fact_status": "assumed"})
    base_lag = _lag("toy", src)
    content = script._Content("toy", src)
    for k in (1, 2, 3, 6):
        facts = script._composed("toy", src, content, lambda m, k=k: (k,), False, "lag k=%d unit=month" % k,
                                 "float32", None, None, "test")
        out = StoreColumn.model_validate(facts)
        assert max(0, base_lag - k) <= _lag("toy_lag%d" % k, out) <= max(0, base_lag - k) + 1, k
    assert base_lag in (4, 5)
    # the same bound NOT signed (fact_status unverified): the output keeps the source's window, R8 refuses both
    unsigned = StoreColumn.model_validate(dict(src.model_dump(exclude_none=True), fact_status="unverified"))
    facts = script._composed("toy", unsigned, script._Content("toy", unsigned), lambda m: (1,), False,
                             "lag k=1 unit=month", "float32", None, None, "test")
    assert facts["window"] == {"align": "unknown", "max_length": 5.0, "unit": "month"}
    assert _lag("toy", unsigned) == _lag("toy_lag1", StoreColumn.model_validate(facts)) == "G-LAG"


# ------------------------------------------------------------------------------------------------
# the feature script: values
def _frame(n_units=3, first_year=2001, n_months=40, gaps=(), nan_precip=(), seed=0):
    """A synthetic dense panel frame with every source the script reads (fixed generator: deterministic)."""
    script = _hook("features/build.py")
    rng = np.random.default_rng(seed)
    sources = sorted({f.derived_from[0] for f in _outputs().values()} - {"month"})
    rows = []
    for u in range(n_units):
        for i in range(n_months):
            if (u, i) in gaps:
                continue
            year, month = first_year + (i // 12), i % 12 + 1
            rows.append(("g_%d_%d" % (u, u), "g", year, month, year * 12 + month))
    frame = pd.DataFrame(rows, columns=["cell_id", "region", "year", "month", "_step"])
    for s in sources:
        frame[s] = rng.gamma(2.0, 20.0, len(frame))
    for (u, i) in nan_precip:
        sel = (frame.cell_id == "g_%d_%d" % (u, u)) & (frame._step == (first_year + i // 12) * 12 + i % 12 + 1)
        frame.loc[sel, script.PRECIP] = np.nan
    return frame


def _run89_reference(frame):
    """bundle_lag_compare.build_feats_ext's arithmetic (pandas), on a DENSE frame, float64."""
    script = _hook("features/build.py")
    df = frame.copy()
    df["t"] = (df.year - 2002) * 12 + (df.month - 1)
    out = {}
    # run89's lags of every run89 base the frame holds (the kept LAG_BASES and the J2 (a) lag-12 parents)
    bases = [b for b in script.RUN89_LAG_BASES if b in df.columns]
    assert set(bases) == set(script.LAG_BASES) | set(script.LAG12_BASES)
    for k in script.LAG_ORDERS:
        ren = {v: "%s_lag%d" % (v, k) for v in bases}
        df = df.merge(df[["cell_id", "t"] + bases].rename(columns=ren).assign(t=lambda x: x.t + k),
                      on=["cell_id", "t"], how="left")
    df = df.sort_values(["cell_id", "t"]).reset_index(drop=True)
    for v in script.WATER_VARS:
        gv = df.groupby("cell_id", sort=False)[v]
        for w in script.ROLL_WINDOWS:
            df["%s_roll%d" % (v, w)] = gv.rolling(w, min_periods=1).mean().to_numpy()
    df["wy"] = df.year - (df.month < 6).astype(int)
    for column, v in script.WYTD:
        df[column] = df.groupby(["cell_id", "wy"], sort=False)[v].cumsum()
    for column, v in script.API:
        df[column] = df.groupby("cell_id")[v].ewm(alpha=0.1, adjust=False).mean().reset_index(level=0, drop=True)
    for column, v, thr in script.RUN_LENGTHS:
        ev = (df[v] >= thr).astype(int)
        g = ev.groupby(df.cell_id).cumsum()
        df[column] = (1 - ev).groupby([df.cell_id, g]).cumsum()
        out[column + ":first_event"] = df.cell_id.map(
            df[df[v] >= thr].groupby("cell_id")["t"].min()).to_numpy()
    th = 2 * np.pi * (df.month - 0.5) / 12.0
    df["ctx:sin1"], df["ctx:cos1"], df["ctx:sin2"], df["ctx:cos2"] = (np.sin(th), np.cos(th), np.sin(2 * th),
                                                                      np.cos(2 * th))
    return df, out


def test_the_values_are_run89s_builder_on_a_dense_panel():
    script = _hook("features/build.py")
    frame = _frame()
    got = script.build(frame, KEYS)
    assert list(got.columns) == list(script.OUTPUTS) and len(got) == len(frame)
    ref, extra = _run89_reference(frame)
    ref = ref.set_index(["cell_id", "t"]).reindex(pd.MultiIndex.from_arrays(
        [frame.cell_id, (frame.year - 2002) * 12 + frame.month - 1]))
    for c in got.columns:
        g = got[c].to_numpy(dtype=np.float64)
        if c.startswith("ctx:top5:"):
            (src,) = script.OUTPUTS[c]["derived_from"]
            k = dict((cc, kk) for cc, _, kk in script.TOP5)[c]
            r = ref[src if k == 0 else "%s_lag%d" % (src, k)].to_numpy(dtype=np.float64)
        elif c in L3_HOLD:
            # L3: on rows up to 2021 (every row of this frame) the hold is its parent itself
            assert (frame.year <= 2021).all()
            r = frame[script.OUTPUTS[c]["derived_from"][0]].to_numpy(dtype=np.float64)
        elif c in ("consec_dry_months", "months_since_sig_rain"):
            r = ref[c].to_numpy(dtype=np.float64)
            t = ((frame.year - 2002) * 12 + frame.month - 1).to_numpy()
            before = ~(t >= extra[c + ":first_event"])          # before the unit's first event (or none)
            assert np.isnan(g[before]).all(), c                    # departure 2: NaN, not a clock
            r = np.where(before, np.nan, r)
        else:
            r = ref[c].to_numpy(dtype=np.float64)
        if script.OUTPUTS[c]["dtype"] == "float32":
            r = r.astype(np.float32).astype(np.float64)
        assert np.array_equal(np.isnan(g), np.isnan(r)), c
        ok = ~np.isnan(g)
        assert np.allclose(g[ok], r[ok], rtol=1e-12, atol=1e-9), c


def test_a_missing_month_breaks_the_run_lengths_until_the_next_event():
    script = _hook("features/build.py")
    frame = _frame(n_units=1, n_months=30, nan_precip=((0, 10),))
    frame[script.PRECIP] = np.where(frame[script.PRECIP].isna(), np.nan, 1.0)      # dry everywhere...
    frame.loc[frame.index[[3, 20]], script.PRECIP] = 50.0                             # ...but months 3 and 20
    got = script.build(frame, KEYS)["consec_dry_months"].to_numpy()
    assert np.isnan(got[:3]).all()                        # before the first event
    assert list(got[3:10]) == [0, 1, 2, 3, 4, 5, 6]
    assert np.isnan(got[10:20]).all()                     # a missing month: unknown until the next event
    assert list(got[20:23]) == [0, 1, 2]


def test_a_gap_is_a_missing_month_never_the_neighbouring_row():
    script = _hook("features/build.py")
    frame = _frame(n_units=2, n_months=20, gaps=((1, 5),))
    got = script.build(frame, KEYS)
    unit1 = frame.cell_id == "g_1_1"
    steps = frame._step[unit1].to_numpy()
    lag1 = got["V01_mean_temp_C_lag1"][unit1].to_numpy(dtype=np.float64)
    after_gap = np.flatnonzero(steps == steps[4] + 2)[0]       # the month after the missing one
    assert np.isnan(lag1[after_gap])
    src = frame["V01_mean_temp_C"][unit1].to_numpy()
    assert lag1[4] == np.float32(src[3])
    assert got["V01_mean_temp_C_lag1"].isna().sum() == 2 + 1   # each unit's first month, and after the gap
    r3 = got["V02_total_precip_mm_roll3"][unit1].to_numpy()
    p = frame["V02_total_precip_mm"][unit1].to_numpy()
    assert np.isclose(r3[after_gap], (p[after_gap] + p[after_gap - 1]) / 2)   # the two months present of three


def test_outputs_are_trailing_only():
    """Changing every source after a step never changes an output at or before that step."""
    script = _hook("features/build.py")
    frame = _frame(n_units=2, n_months=36)
    base = script.build(frame, KEYS)
    cut = 2002 * 12 + 7
    later = frame._step > cut
    changed = frame.copy()
    for c in frame.columns[5:]:
        changed.loc[later, c] = changed.loc[later, c] * 3.0 + 7.0
    moved = script.build(changed, KEYS)
    early = (frame._step <= cut).to_numpy()
    pd.testing.assert_frame_equal(base[early], moved[early])
    assert not base[~early].equals(moved[~early])


def test_an_unsorted_or_repeated_frame_is_refused():
    script = _hook("features/build.py")
    frame = _frame(n_units=2, n_months=6)
    with pytest.raises(script.FeatureBuildError, match="sorted"):
        script.build(frame.iloc[::-1].reset_index(drop=True), KEYS)
    with pytest.raises(script.FeatureBuildError, match="sorted"):
        script.build(pd.concat([frame.iloc[:3], frame.iloc[2:]], ignore_index=True), KEYS)
    bad = frame.copy()
    bad["month"] = 1
    with pytest.raises(script.FeatureBuildError, match="calendar months"):
        script.build(bad, KEYS)


def test_the_block_size_does_not_change_a_value():
    script = _hook("features/build.py")
    frame = _frame(n_units=7, n_months=30)
    whole = script.build(frame, KEYS)
    saved = script.UNIT_BLOCK
    try:
        script.UNIT_BLOCK = 2
        blocks = script.build(frame, KEYS)
    finally:
        script.UNIT_BLOCK = saved
    pd.testing.assert_frame_equal(whole, blocks)


@pytest.mark.skipif(not RUN89_FEATS.is_file(), reason="run89's saved feature list is not on this machine")
def test_the_lag_bases_and_water_columns_are_run89s_saved_feature_list():
    script = _hook("features/build.py")
    feats = [str(f) for f in np.load(str(RUN89_FEATS), allow_pickle=True)["feats"]]
    lags = [f for f in feats if f.rsplit("_lag", 1)[-1].isdigit() and "_lag" in f]
    assert lags == [script.lag_column(b, k) for k in script.LAG_ORDERS for b in script.RUN89_LAG_BASES]
    assert script.LAG_BASES == tuple(b for b in script.RUN89_LAG_BASES if b not in script.DROPPED_LAG_BASES)
    assert set(script.LAG12_BASES) <= set(script.DROPPED_LAG_BASES)
    built = [c for c in _outputs() if not c.startswith("ctx:") and "_lag" in c]
    assert set(built) <= set(lags) and len(built) == 345 + 6        # every built lag is a run89 saved feature
    water = [c for c in _outputs() if not c.startswith("ctx:") and c not in built and c not in L3_HOLD]
    assert set(water) <= set(feats) and len(water) == 28
    assert feats[-28:] == [c for c in feats if c in water]


@pytest.mark.skipif(not (RUN89_FEATS.is_file() and PANEL.is_dir()),
                    reason="run89's saved features or the monthly panel are not on this machine")
def test_the_rebuild_is_run89s_saved_feature_values_on_real_data():
    """On the 64 thar_desert cells x 264 months run89 saved (sandbox_thar_desert.npz 'X', read-only), every
    lag (345 + the 6 J2 (a) lag-12 columns) and water-memory column the script builds equals run89's value
    wherever both are finite, up to
    run89's power-of-two column divisor (cross_region_full.get_colscale: the float16 storage scale; 1024 or
    512 for the ERA5 flux lags, 16 for four water-year sums). run89's X holds median-imputed values where
    the build gave NaN (leak_audit.impute_masked); the rebuild leaves them NaN (and the run lengths NaN
    before a cell's first event, departure 2), so those rows are not compared."""
    import pyarrow.parquet as pq

    script = _hook("features/build.py")
    z = np.load(str(RUN89_FEATS), allow_pickle=True)
    feats = [str(f) for f in z["feats"]]
    cid = z["cell_id"].astype(str)
    cells = sorted(set(cid))
    sources = sorted({f["derived_from"][0] for f in script.OUTPUTS.values()} - {"month"})
    parts = [pq.read_table(str(PANEL / ("thar_desert_monthly_%d.parquet" % y)),
                           columns=["cell_id", "region", "year", "month"] + sources,
                           filters=[("cell_id", "in", cells)]).to_pandas() for y in range(2002, 2024)]
    frame = pd.concat(parts, ignore_index=True)
    frame["_step"] = frame.year * 12 + frame.month
    frame = frame.sort_values(["cell_id", "_step"]).reset_index(drop=True)
    for s in sources:          # the panel fills, as the engine's reader masks them (thar holds none)
        v = frame[s].to_numpy(dtype=np.float64)
        frame[s] = np.where(np.isin(v, [-32768.0, -32767.0, -2147483648.0, -2147483647.0]), np.nan, v)
    got = script.build(frame, KEYS)
    ref = pd.DataFrame(z["X"], columns=feats, index=pd.MultiIndex.from_arrays(
        [cid, z["year"] * 12 + z["month"]])).reindex(pd.MultiIndex.from_arrays([frame.cell_id, frame._step]))
    assert ref.notna().all(axis=1).all()               # every rebuilt row is a saved row
    compared, scaled = 0, {}
    for c in got.columns:
        if c not in feats:
            continue
        g, r = got[c].to_numpy(dtype=np.float64), ref[c].to_numpy(dtype=np.float64)
        ok = np.isfinite(g) & (r != 0)
        scale = 2.0 ** np.round(np.log2(np.median(g[ok] / r[ok])))
        assert np.allclose(g[ok], r[ok] * scale, rtol=1e-5, atol=1e-6), c
        assert np.allclose(g[np.isfinite(g) & (r == 0)], 0.0, atol=1e-6), c
        compared += 1
        if scale != 1:
            scaled[c] = scale
    assert compared == 345 + 6 + 28
    assert set(scaled.values()) <= {16.0, 512.0, 1024.0} and len(scaled) == 24


# ------------------------------------------------------------------------------------------------
# the static-table builder
def test_the_static_builder_writes_once_with_grid_indices(tmp_path):
    builder = _hook("ingest/build_static.py")
    panel, pkg = tmp_path / "panel", tmp_path / "pkg"
    panel.mkdir()
    pkg.mkdir()
    for year in (2002, 2003, 2004):
        pd.DataFrame({"cell_id": ["g_x_%d_%d" % (i, 10 - i) for i in (2, 0, 1)] * 2,
                      "lat": [3.0, 1.0, 2.0] * 2, "lon": [6.0, 4.0, 5.0] * 2}).to_parquet(
            panel / ("g_x_monthly_%d.parquet" % year), index=False)
    (pkg / "dataset.yaml").write_text(
        "stores:\n  target: '%s/{group}_monthly_{year}.parquet'\n  static: 'data/static/part-0.parquet'\n"
        "  drivers: ['%s/{group}_monthly_{year}.parquet']\n" % (panel.as_posix(), panel.as_posix()),
        encoding="utf-8")
    dry = builder.static_table(pkg)                                   # the checked table, nothing written
    assert not (pkg / "data").exists()
    out = builder.build(pkg)
    table = pd.read_parquet(out)
    pd.testing.assert_frame_equal(table, dry.reset_index(drop=True))
    assert list(table.columns) == ["cell_id", "region", "lat", "lon", "grid_ix", "grid_iy"]
    assert list(table["cell_id"]) == ["g_x_0_10", "g_x_1_9", "g_x_2_8"]
    assert list(table["grid_ix"]) == [0, 1, 2] and list(table["grid_iy"]) == [10, 9, 8]
    assert list(table["lat"]) == [1.0, 2.0, 3.0]
    with pytest.raises(SystemExit, match="written once"):
        builder.build(pkg)


def test_the_static_builder_refuses_a_broken_census(tmp_path):
    builder = _hook("ingest/build_static.py")
    first, last = tmp_path / "a.parquet", tmp_path / "b.parquet"
    pd.DataFrame({"cell_id": ["g_0_0", "g_1_0"], "lat": [1.0, 2.0], "lon": [1.0, 2.0]}).to_parquet(first, index=False)
    pd.DataFrame({"cell_id": ["g_0_0"], "lat": [1.0], "lon": [1.0]}).to_parquet(last, index=False)
    with pytest.raises(SystemExit, match="not one census"):
        builder.group_rows([str(first), str(last)], "g")
    # a MIDDLE year with another cell set is refused too (every year is checked, not only the two ends)
    middle = tmp_path / "m.parquet"
    pd.DataFrame({"cell_id": ["g_0_0", "g_1_0", "g_2_0"], "lat": [1.0, 2.0, 3.0],
                  "lon": [1.0, 2.0, 3.0]}).to_parquet(middle, index=False)
    with pytest.raises(SystemExit, match="m.parquet holds 3"):
        builder.group_rows([str(first), str(middle), str(first)], "g")
    assert len(builder.group_rows([str(first), str(first), str(first)], "g")) == 2
    pd.DataFrame({"cell_id": ["g_0_0", None], "lat": [1.0, 2.0], "lon": [1.0, 2.0]}).to_parquet(middle, index=False)
    with pytest.raises(SystemExit, match="no cell id"):
        builder.group_rows([str(middle)], "g")
    pd.DataFrame({"cell_id": ["g_0_0", "g_0_0"], "lat": [1.0, 1.5], "lon": [1.0, 1.0]}).to_parquet(first, index=False)
    with pytest.raises(SystemExit, match="change lat/lon"):
        builder.group_rows([str(first), str(first)], "g")
    # a lat/lon missing on SOME rows of a cell is refused row by row (the per-cell nunique and first skip NaN),
    # and so is a finite fill code or any value outside [-90, 90] / [-180, 180]
    for lat, lon in (([1.0, np.nan], [1.0, 1.0]), ([1.0, 1.0], [np.nan, 1.0]), ([1.0, 1.0], [1.0, np.inf]),
                     ([-32768.0, -32768.0], [1.0, 1.0]), ([1.0, 1.0], [180.5, 180.5]), ([90.5, 90.5], [1.0, 1.0])):
        pd.DataFrame({"cell_id": ["g_0_0", "g_0_0"], "lat": lat, "lon": lon}).to_parquet(first, index=False)
        with pytest.raises(SystemExit, match=r"missing, non-finite or out-of-range lat/lon, e.g. cells \['g_0_0'\]"):
            builder.group_rows([str(first)], "g")
    pd.DataFrame({"cell_id": ["g_0_0", "g_0_0"], "lat": [-90.0, -90.0], "lon": [180.0, 180.0]}).to_parquet(
        first, index=False)
    assert builder.group_rows([str(first)], "g")[["lat", "lon"]].values.tolist() == [[-90.0, 180.0]]
