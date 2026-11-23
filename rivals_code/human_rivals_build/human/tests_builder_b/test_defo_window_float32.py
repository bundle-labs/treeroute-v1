"""Regression (2026-10-24, PARITY japan_central_honshu / new_guinea_papua): the region window edges must be computed in
the target builder's float32 arithmetic (defo_ingest.py reads float32 panel centres); float64 put the first 30 m pixel
column of two real region west edges one column off the target."""
import math

import numpy as np

from adapters import defo_prep as DP


def _two_columns(west):
    lon = np.array([west, west, np.float32(west + np.float32(0.035934448))], dtype=np.float32)
    lat = np.array([35.0, 35.035934448, 35.0], dtype=np.float32)
    return ["a", "b", "c"], lon.astype(np.float64), lat.astype(np.float64)


def test_west_edge_is_the_float32_value_and_lands_on_the_builders_pixel_column():
    # the two real failing west columns and their tile origins (Hansen 10-degree tiles)
    for west, tile_lon, builder_c0 in ((np.float32(135.98697), 130.0, 23875), (np.float32(141.98772), 140.0, 7879)):
        ids, lon, lat = _two_columns(west)
        g = DP.region_grid(ids, lon, lat)
        u = np.sort(np.unique(lon.astype(np.float32)))
        hx = float(np.median(np.diff(u))) / 2
        assert g["lon0"] == float(np.float32(u.min()) - np.float32(hx))
        assert int(np.floor((g["lon0"] - tile_lon) / 0.00025)) == builder_c0


def test_non_float32_centres_refuse():
    ids, lon, lat = _two_columns(np.float32(135.98697))
    lon = lon.copy(); lon[0] += 1e-9                           # not a float32 value any more
    try:
        DP.region_grid(ids, lon, lat)
    except Exception as exc:                                   # the adapter's refusal
        assert "float32" in str(exc)
    else:
        raise AssertionError("expected a refusal")
