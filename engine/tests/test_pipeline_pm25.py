"""The PM2.5 package's own code for the pipeline (tests may name problems): the target reader
(datasets/pm25/ingest/target_reader.py: the ACAG fill 9.96921e36 to NaN), the context feature script
(datasets/pm25/features/build.py: ctx:month, ctx:lat as shipped, and burn_lag1) and the static-table
builder (datasets/pm25/ingest/build_static.py). Synthetic files under the test's temp folder; one
read-only check on a real target file is skipped where the store is absent."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import ENGINE_DIR

PM25 = ENGINE_DIR / "datasets" / "pm25"
REAL_TARGET = Path("D:/pm25_acag")


def _hook(rel):
    from treeroute.pipeline.data import load_hook

    return load_hook(PM25, rel)


def _target_file(path, group, year, values):
    n = len(values)
    pd.DataFrame({"cell_id": ["%s_%d_%d" % (group, i, -i) for i in range(n)],
                  "year": np.full(n, year, dtype=np.int16), "month": np.arange(1, n + 1, dtype=np.int8),
                  "pm25_ugm3": np.asarray(values, dtype=np.float32)}).to_parquet(path, index=False)


def test_the_target_reader_masks_the_acag_fill(tmp_path, capsys):
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_pm25_2010.parquet"
    _target_file(path, "g_one", 2010, [5.0, 9.96921e36, np.nan, 12.5, 9.96921e36])
    out = reader.read_target_file(str(path), {"group": "g_one", "year": 2010})
    assert list(out.columns) == ["cell_id", "region", "year", "month", "pm25_ugm3"]
    assert (out["region"] == "g_one").all()
    y = out["pm25_ugm3"].to_numpy()
    assert np.isnan(y[[1, 2, 4]]).all() and np.allclose(y[[0, 3]], [5.0, 12.5])
    assert not (np.abs(np.nan_to_num(y)) >= 1e30).any()
    assert "2 values at the fill magnitude" in capsys.readouterr().out
    assert out["year"].dtype == np.int64 and out["month"].dtype == np.int64


@pytest.mark.parametrize("key,match", [({"year": 2010}, "no group"),
                                       ({"group": "g_other", "year": 2010}, "do not carry the group"),
                                       ({"group": "g_one", "year": 2011}, "rows of years")])
def test_the_target_reader_refuses_a_mismatched_file(tmp_path, key, match):
    reader = _hook("ingest/target_reader.py")
    path = tmp_path / "g_one_pm25_2010.parquet"
    _target_file(path, "g_one", 2010, [1.0, 2.0])
    with pytest.raises(reader.TargetReadError, match=match):
        reader.read_target_file(str(path), key)


def test_the_feature_script_makes_the_shipped_context_and_burn_lag1():
    from treeroute.pipeline.data import feature_outputs

    script = _hook("features/build.py")
    outputs = feature_outputs(script)                   # every output is a valid store-catalog column
    # + the six J2 (a) lag-12 columns (ruling J, 2026-10-05) and the six L3 livestock holds (ruling L, 2026-10-06);
    # their own checks are tests/test_packages_pm25_bans.py
    lag12 = ["%s_lag12" % p for p in ("spei_01m", "spei_03m", "spei_06m", "V06_spei_12m", "spei_24m", "amo")]
    hold = ["%s_hold2021" % p for p in script.HOLD_PARENTS]
    assert sorted(outputs) == sorted(["burn_lag1", "ctx:lat", "ctx:month"] + lag12 + hold) and len(hold) == 6
    assert outputs["ctx:lat"].cadence.kind == "static"
    assert outputs["burn_lag1"].derived_from == ["burn_frac"] and outputs["burn_lag1"].reads_target is False
    # two units; unit b misses step 24003 (a gap): its burn_lag1 after the gap is NaN, never a neighbour
    frame = pd.DataFrame({
        "cell_id": ["a_0_0"] * 3 + ["b_0_1"] * 2, "region": ["a"] * 3 + ["b"] * 2,
        "year": [2000] * 5, "month": [1, 2, 3, 1, 3], "_step": [24001, 24002, 24003, 24001, 24003],
        "lat": [10.0, 10.0, 10.0, -5.0, -5.0], "burn_frac": [0.1, 0.2, 0.3, 0.7, 0.9]})
    for c in script.LAG12_PARENTS + script.HOLD_PARENTS:     # the other outputs' sources
        frame[c] = 1.0
    keys = {"unit": "cell_id", "group": "region", "step": "_step", "time": {"year": "year", "month": "month"}}
    out = script.build(frame, keys)
    assert list(out["ctx:month"]) == [1, 2, 3, 1, 3]
    assert list(out["ctx:lat"]) == [10.0, 10.0, 10.0, -5.0, -5.0]
    lag = out["burn_lag1"].to_numpy(dtype=np.float64)
    assert np.isnan(lag[0]) and np.allclose(lag[1:3], [0.1, 0.2]) and np.isnan(lag[3]) and np.isnan(lag[4])


def test_the_catalog_declares_every_feature_output():
    from treeroute.package.load import load_package

    script = _hook("features/build.py")
    cols = load_package(PM25).catalog.columns
    for c in script.OUTPUTS:
        assert c in cols
    assert cols["ctx:month"].role == "router_context" and cols["ctx:lat"].role == "router_context"
    assert cols["burn_lag1"].role == "engineered"


def test_the_static_builder_writes_once_with_grid_indices(tmp_path):
    builder = _hook("ingest/build_static.py")
    store, panel, pkg = tmp_path / "acag", tmp_path / "panel", tmp_path / "pkg"
    for d in (store, panel, pkg):
        d.mkdir()
    for year in (2002, 2003):
        _target_file(store / ("g_x_pm25_%d.parquet" % year), "g_x", year, [1.0, 2.0, 3.0])
        pd.DataFrame({"cell_id": ["g_x_%d_%d" % (i, -i) for i in range(3)] * 2,
                      "lat": [1.0, 2.0, 3.0] * 2, "lon": [4.0, 5.0, 6.0] * 2}).to_parquet(
            panel / ("g_x_monthly_%d.parquet" % year), index=False)
    (pkg / "dataset.yaml").write_text(
        "stores:\n  target: '%s/{group}_pm25_{year}.parquet'\n  static: 'data/static/part-0.parquet'\n"
        "  drivers: ['%s/{group}_monthly_{year}.parquet']\n" % (store.as_posix(), panel.as_posix()),
        encoding="utf-8")
    out = builder.build(pkg)
    table = pd.read_parquet(out)
    assert list(table.columns) == ["cell_id", "region", "lat", "lon", "grid_ix", "grid_iy"]
    assert list(table["grid_ix"]) == [0, 1, 2] and list(table["grid_iy"]) == [0, -1, -2]
    with pytest.raises(SystemExit, match="written once"):
        builder.build(pkg)


@pytest.mark.skipif(not REAL_TARGET.is_dir(), reason="the ACAG target store is not on this machine")
def test_the_target_reader_on_one_real_file_is_read_only_and_clean():
    import os

    reader = _hook("ingest/target_reader.py")
    path = REAL_TARGET / "tasmania_western_pm25_2010.parquet"
    if not path.is_file():
        pytest.skip("no tasmania_western 2010 file")
    before = os.stat(path).st_mtime_ns
    out = reader.read_target_file(str(path), {"group": "tasmania_western", "year": 2010})
    assert os.stat(path).st_mtime_ns == before
    y = out["pm25_ugm3"].to_numpy()
    assert not (np.abs(np.nan_to_num(y)) >= 1e30).any()
    assert set(out["month"]) == set(range(1, 13)) and (out["region"] == "tasmania_western").all()
    assert out["cell_id"].str.startswith("tasmania_western_").all()
