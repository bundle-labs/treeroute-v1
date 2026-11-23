"""Read-only smoke of the io science on real monthly-panel files (skipped when the store is absent).

Facts come from the NDVI package (roles) and its included panel store catalog (fill values), loaded
through treeroute.package.load; data are read with treeroute.io.readers. Nothing is written.

Known from the full-dataset audit (memory: reference_panel_nodata_sentinel): the TerraClimate
precipitation and snow columns carry the int32 NoData -2^31, and nine more TerraClimate columns carry
the int16 NoData -32768, in the ocean-edge cells of 47 coastal regions (greenland_west_coast and
greece_mainland among them); inland deserts (thar_desert) carry none.
"""

from pathlib import Path

import numpy as np
import pytest

from conftest import ENGINE_DIR

PANEL = Path("D:/monthly_panel")
FILES = {name: PANEL / ("%s_monthly_2010.parquet" % name)
         for name in ("greece_mainland", "greenland_west_coast", "thar_desert")}
INT32_NODATA = ("V02_total_precip_mm", "swe_mean_mm")
INT16_NODATA = ("V01_mean_temp_C", "V05_mean_vpd_kPa", "V07_total_ref_ET_mm", "V09_mean_wind_ms",
                "aet_total_mm", "climate_water_deficit_mm", "soil_water_tc_mm", "solar_radiation_Wm2",
                "tc_vapor_pressure")
KEYS = ("cell_id", "region", "year", "month")

pytestmark = pytest.mark.skipif(not all(p.is_file() for p in FILES.values()),
                                reason="the monthly panel store is not on this machine")


class Facts:
    def __init__(self, role, fills, optout):
        self.role, self.fill_values, self.near_sentinel_optout = role, tuple(fills), optout


@pytest.fixture(scope="module")
def package_facts():
    from treeroute.package.load import load_package

    pkg = load_package(ENGINE_DIR / "datasets" / "ndvi")
    store = [s for path, s in pkg.stores.items() if "monthly_panel" in path][0]
    facts = {}
    for name, col in pkg.catalog.columns.items():
        stored = store.columns.get(name)
        facts[name] = Facts(col.role, stored.fill_values if stored else (),
                            stored.near_sentinel_optout if stored else False)
    catalog_columns = tuple(store.columns) + KEYS
    return facts, catalog_columns


def _raw_counts(table, column, code):
    values = table.column(column).to_numpy(zero_copy_only=False).astype(np.float64)
    return int((values == code).sum())


def test_every_column_of_a_real_file_is_masked_by_its_declared_fills(package_facts):
    import pyarrow.parquet as pq

    from treeroute.io.checks import check_column_set
    from treeroute.io.readers import read_columns
    from treeroute.io.sentinel import mask_sentinels

    facts, catalog_columns = package_facts
    path = FILES["greece_mainland"]
    names = tuple(pq.ParquetFile(str(path)).schema_arrow.names)
    check_column_set(names, catalog_columns, "monthly panel")  # all 170 columns declared, none extra
    table = read_columns(path, names)
    raw = {c: (_raw_counts(table, c, -2.0 ** 31), _raw_counts(table, c, -32768.0))
           for c in INT32_NODATA + INT16_NODATA}
    assert all(raw[c][0] > 0 for c in INT32_NODATA), raw
    assert all(raw[c][1] > 0 for c in INT16_NODATA), raw
    frame = table.to_pandas()
    out, report = mask_sentinels(frame, facts)
    for c in INT32_NODATA:
        assert report.masked[c] == raw[c][0], (c, report.masked[c], raw[c])
    for c in INT16_NODATA:
        assert report.masked[c] == raw[c][1], (c, report.masked[c], raw[c])
    codes = (-32768.0, -32767.0, -2.0 ** 31, -2.0 ** 31 + 1)
    for c in out.columns:
        if facts[c].role in ("key_unit", "key_group", "key_time") or out[c].dtype.kind not in "fiu":
            continue
        v = out[c].to_numpy().astype(np.float64)
        assert not np.isin(v, codes).any(), c
        assert not (np.abs(v[np.isfinite(v)]) >= 1e30).any(), c
        if facts[c].near_sentinel_optout is False:
            with np.errstate(invalid="ignore"):
                assert report.flagged_near_sentinel[c] == int((np.abs(v) >= 2.0 ** 30).sum()), c
    assert out["cell_id"].equals(frame["cell_id"]) and out["year"].equals(frame["year"])
    assert "V11_mean_ndvi" not in report.masked  # the target is checked, never masked


@pytest.mark.parametrize("region,expect_any", [("greenland_west_coast", True), ("thar_desert", False)])
def test_known_sentinel_regions(package_facts, region, expect_any):
    from treeroute.io.readers import read_columns
    from treeroute.io.sentinel import mask_sentinels

    facts, _ = package_facts
    cols = KEYS + INT32_NODATA + INT16_NODATA[:2]
    frame = read_columns(FILES[region], cols).to_pandas()
    out, report = mask_sentinels(frame, facts)
    total = sum(report.masked.values())
    assert (total > 0) == expect_any, report.masked
    if expect_any:
        assert report.masked["V02_total_precip_mm"] == report.masked["swe_mean_mm"] > 0
    assert np.isfinite(out["V02_total_precip_mm"].to_numpy()).sum() == len(out) - report.masked["V02_total_precip_mm"]


def test_real_keys_give_a_complete_monthly_grid_and_exact_predecessors():
    from treeroute.io.readers import read_columns
    from treeroute.io.steps import build_dense_grid, predecessor_index, step_bounds, step_index

    class Cad:
        kind, length, unit = "regular", 1, "month"

    frame = read_columns(FILES["greece_mainland"], KEYS).to_pandas()
    steps = step_index({"year": frame["year"].to_numpy(), "month": frame["month"].to_numpy()},
                       {"year": "year", "month": "month"}, Cad)
    assert steps.min() == 2010 * 12 + 1 and steps.max() == 2010 * 12 + 12
    grid = build_dense_grid(frame["cell_id"].to_numpy(dtype=object), frame["region"].to_numpy(dtype=object),
                            steps, (2010 * 12 + 1, 2010 * 12 + 12))
    assert grid.n_steps == 12 and len(grid.unit_ids) * 12 == len(frame)
    assert set(grid.group_of_unit) == {"greece_mainland"}
    codes = {u: i for i, u in enumerate(grid.unit_ids)}
    unit_codes = np.array([codes[u] for u in frame["cell_id"]])
    prev = predecessor_index(unit_codes, steps, 1)
    january = frame["month"].to_numpy() == 1
    assert (prev[january] == -1).all() and (prev[~january] >= 0).all()
    assert (frame["cell_id"].to_numpy()[prev[~january]] == frame["cell_id"].to_numpy()[~january]).all()
    first, last = step_bounds(np.array([2010 * 12 + 2]), Cad)
    assert int(last[0] - first[0]) == 27  # February 2010 has 28 days
