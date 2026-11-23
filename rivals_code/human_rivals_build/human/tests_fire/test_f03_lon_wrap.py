"""T-F03 the longitude wrap (SPEC_HUMAN_PARTB.txt 3.1, 3.3; PEND Part 620 :998, the fire_cems.py bug where every
western cell snapped to one column).

- wrap_lon: ((lon + 180) mod 360) - 180, float64, in [-180, 180); haversine_km casts float32 inputs to float64 first;
  product_cell_id writes the wrapped longitude.
- With the great_plains and cerrado SEAS5 subsets (0-360 longitudes 256.25.. / 304.5..), every real western bank unit
  maps to the brute-force haversine nearest point; the units use >= 2 distinct grid columns and NOT the single column
  a raw (unwrapped) -103 vs 256..258 comparison gives.
- The ERA5 western copy (same values, longitudes 256.00..257.25) gives the shifted units the same values as the
  eastern original; the prime-meridian copy (358.75 .. 0.5, non-monotonic) maps units at -0.2 / -0.1 / +0.1 / +0.2 to
  the right side of 0 deg; a unit outside its box area refuses.
"""

import json

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def test_f03_wrap_lon_and_haversine(geff):
    got = geff.wrap_lon(np.array([358.75, 0.0, 180.0, -180.0, 359.999, 256.25, -102.5, 540.0]))
    assert got.dtype == np.float64
    np.testing.assert_allclose(got, [-1.25, 0.0, -180.0, -180.0, -0.001, -103.75, -102.5, -180.0], atol=1e-9)
    assert (got >= -180.0).all() and (got < 180.0).all()
    d = geff.haversine_km(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([1.0]))
    assert float(np.ravel(d)[0]) == pytest.approx(6371.0 * np.pi / 180.0, rel=1e-12)
    # periodic: 256.25 east == -103.75
    a = geff.haversine_km(np.array([39.0]), np.array([-102.9]), np.array([39.5]), np.array([256.25]))
    b = geff.haversine_km(np.array([39.0]), np.array([-102.9]), np.array([39.5]), np.array([-103.75]))
    assert float(np.ravel(a)[0]) == pytest.approx(float(np.ravel(b)[0]), rel=1e-12)
    # float32 inputs are cast to float64 FIRST (RF:26): the same as the float64 of the float32 values
    la32, lo32 = np.float32([39.0581169128418]), np.float32([-102.96489715576172])
    c32 = geff.haversine_km(la32, lo32, np.array([39.5]), np.array([-102.75]))
    c64 = FF.haversine(la32.astype(np.float64), lo32.astype(np.float64), 39.5, -102.75)
    assert np.asarray(c32).dtype == np.float64
    assert float(np.ravel(c32)[0]) == pytest.approx(float(np.ravel(c64)[0]), rel=1e-12)


def test_f03_product_cell_id_wraps(geff):
    assert geff.product_cell_id("great_plains", 39.5, 257.25) == "great_plains|39.500|-102.750"
    assert geff.product_cell_id("box10", 37.25, 359.75) == "box10|37.250|-0.250"
    assert geff.product_cell_id("cerrado", -14.75, 305.5) == "cerrado|-14.750|-54.500"


def _map(geff, grid_lat, grid_lon, valid, units, window=2):
    la = np.array([FF.unit_coords(u)[0] for u in units], np.float64)
    lo = np.array([FF.unit_coords(u)[1] for u in units], np.float64)
    m = geff.map_units(grid_lat, grid_lon, valid, la, lo, window)
    return {k: np.asarray(v) for k, v in m.items()}, la, lo


@pytest.mark.parametrize("key,group", [("seas_gp_2019", "great_plains"), ("seas_ce_2019", "cerrado")])
def test_f03_western_units_map_to_the_haversine_nearest_point(geff, raw_subsets, key, group):
    lat, lon, valid = FF.grid_of(raw_subsets[key])
    assert (lon > 180).all(), "the subset keeps the RAW 0-360 western longitudes"
    units = [r[0] for r in FF.REAL_UNITS if r[1] == group]
    m, la, lo = _map(geff, lat, lon, valid, units)
    for k, u in enumerate(units):
        e = FF.expected_point(lat, lon, valid, la[k], lo[k], 2)
        assert (int(m["i"][k]), int(m["j"][k])) == (e["i"], e["j"]), u
        assert not bool(m["uncovered"][k]) and not bool(m["substituted"][k])
        assert float(m["dist_km"][k]) == pytest.approx(e["dist_km"], rel=1e-9)
        assert e["dist_km"] < 80.0                                     # a 1-deg cell: always < ~79 km away
    raw_cols = [int(np.argmin(np.abs(lon - v))) for v in lo]         # the fire_cems.py comparison: -103 vs 256..
    assert len(set(raw_cols)) == 1                                   # every unit snaps to one column there
    cols = set(int(j) for j in m["j"])
    assert len(cols) >= 2, cols                                      # units at different longitudes: >= 2 columns
    assert cols != set(raw_cols), (cols, raw_cols)


def test_f03_build_on_the_western_subsets_matches_the_hand_point(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)
    frame = geff.build(toy.ctx(), toy.rival, 6, "all")
    for key, group in (("seas_gp_2019", "great_plains"), ("seas_ce_2019", "cerrado")):
        lat, lon, valid = FF.grid_of(raw_subsets[key])
        for u in [r[0] for r in FF.REAL_UNITS if r[1] == group]:
            la, lo = FF.unit_coords(u)
            e = FF.expected_point(lat, lon, valid, la, lo, 2)
            for start in ("2019-01-01", "2019-02-01"):
                t, want = FF.seas5_target_hand(raw_subsets[key], start, e["i"], e["j"])
                got = frame[(frame["unit"] == u) & (frame["time"] == t)]
                assert len(got) == 1
                assert float(got["x__fwi_mean"].iloc[0]) == pytest.approx(want, rel=1e-6), (u, start)
                assert got["product_cell"].iloc[0] == geff.product_cell_id(group, lat[e["i"]], lon[e["j"]])


def test_f03_era5_western_copy_gives_the_same_values(geff, raw_subsets, tmp_path):
    east = geff.build(*_toy_args(FF.era5_toy(tmp_path / "east", raw_subsets)))
    west_toy = FF.era5_toy(tmp_path / "west", raw_subsets, key="era5_west", group="greece_west")
    assert (west_toy.units["unit"].str.startswith("west_")).all()
    west = geff.build(*_toy_args(west_toy))
    w = west.assign(unit=west["unit"].str.replace("west_", "", regex=False)).set_index(["unit", "time"])
    e = east.set_index(["unit", "time"])
    assert len(w) == len(e) and set(w.index) == set(e.index)
    np.testing.assert_array_equal(w.loc[e.index, "x__fwi_mean"].to_numpy(), e["x__fwi_mean"].to_numpy())
    assert np.isfinite(e["x__fwi_mean"]).sum() > 0
    lat, lon, valid = FF.grid_of(raw_subsets["era5_west"])
    assert (lon >= 256.0).all() and (lon <= 257.25).all()


def _toy_args(toy):
    return toy.ctx(), toy.rival, toy.lead, "all"


def test_f03_prime_meridian_grid(geff, raw_subsets, tmp_path):
    lat, lon, valid = FF.grid_of(raw_subsets["era5_prime"])
    np.testing.assert_array_equal(lon, FF.PRIME_LONS)                  # non-monotonic in 0-360
    units = ["prime_m020", "prime_m010", "prime_p010", "prime_p020"]
    m, la, lo = _map(geff, lat, lon, valid, units)
    for k, u in enumerate(units):
        e = FF.expected_point(lat, lon, valid, la[k], lo[k], 2)
        assert (int(m["i"][k]), int(m["j"][k])) == (e["i"], e["j"]), u
    col = {u: float(FF.wrap(lon[int(m["j"][k])])) for k, u in enumerate(units)}
    assert col["prime_m020"] == -0.25 and col["prime_p020"] == 0.25        # each on its own side of 0 deg
    assert col["prime_m010"] in (-0.25, 0.0) and col["prime_p010"] in (0.0, 0.25)
    assert col["prime_m010"] == 0.0 and col["prime_p010"] == 0.0           # 0.1 from 0.0, 0.15 from +-0.25
    toy = FF.era5_toy(tmp_path, raw_subsets, key="era5_prime", group="prime_meridian")
    assert toy.products[FF.ERA5_PID]
    area = json.loads(open(toy.products[FF.ERA5_PID]["manifest"], encoding="utf-8").read())
    req = list(area["requests"].values())[0]["request"]["area"]
    assert req[1] == -1.25 and req[3] == 0.5                                 # W <= E in -180..180: no wrap box
    frame = geff.build(toy.ctx(), toy.rival, 0, "all")
    assert np.isfinite(frame["x__fwi_mean"]).any()
    for u in units:
        f = frame[(frame["unit"] == u) & np.isfinite(frame["x__fwi_mean"])]
        assert len(f) == 23
        assert set(f["product_cell"]) == {geff.product_cell_id("prime_meridian", lat[int(m["i"][units.index(u)])],
                                                                lon[int(m["j"][units.index(u)])])}


def test_f03_unit_outside_its_box_refuses(geff, raw_subsets, tmp_path):
    """A great_plains unit west of the box's W edge (-103.75) is refused, never silently dropped."""
    toy = FF.seas5_toy(tmp_path, raw_subsets)
    ctx = toy.ctx()
    st = FF.static_table()
    folder = toy.products[FF.STATIC_PID]["path"]
    out = pd.concat([st, pd.DataFrame({"cell_id": ["great_plains_far_west"], "region": ["great_plains"],
                                       "lat": [39.0], "lon": [-110.0], "grid_ix": [0], "grid_iy": [0]})],
                    ignore_index=True)
    out.to_parquet(str(FF.Path(folder) / "part-0.parquet"), index=False)
    FF.write_tool_manifest(folder, FF.Path(ctx.cfg["out_root"]) / "_products" / FF.STATIC_PID /
                           "product_manifest.json", FF.STATIC_PID)
    units = pd.concat([toy.units, pd.DataFrame({"unit": ["great_plains_far_west"], "group": ["great_plains"],
                                                "is_scored": [True], "seen_during_design": [False]})],
                      ignore_index=True)
    table = FF.key_table(units, FF.RAW_SEAS_TIMES, 6, FF.RAW_SEAS_CUTS, offset=0)
    exc = FF.refuses(geff.build, toy.ctx(units=units, key_table=table), toy.rival, 6, "all", kinds=_refusals(geff))
    assert "great_plains_far_west" in str(exc) or "box" in str(exc).lower() or "outside" in str(exc).lower()
