"""T-H16 the coral rule on synthetic SST (SPEC_HUMAN.txt section 2; adapters/coral_crw.py, coral_outlook.py):
DHW and the 5-level BAA equal a hand computation; the window ends at d*; a missing day gives NaN; a masked MMM pixel
takes the nearest valid pixel within 3 cells (none -> NaN); the SST npz is memory-mapped by its stored members (a
compressed member refuses); the store reader never reads the label column; the Outlook reader checks the Week_20
window attributes and takes the maximum alert of the nearest ocean ring within 3 rings."""

import datetime as dt
import math

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O
from rivals_human.tests import toy_products as TP


def _cc():
    return HK.tool("coral_crw")


def _series(n_days=200, d_end=20000, mmm=28.0, seed=1):
    rng = np.random.default_rng(seed)
    days = np.arange(d_end - n_days + 1, d_end + 1, dtype=np.int64)
    sst = np.round(mmm + 1.6 * np.sin(np.arange(n_days) / 9.0) + rng.normal(0, 0.4, n_days), 2).astype(np.float32)   # CoralTemp: 0.01
    return days, sst


def _oracle(days, sst, mmm, d_star):
    return O.dhw_baa({int(d): float(v) for d, v in zip(days.tolist(), sst.astype(np.float64).tolist())}, mmm, d_star)


@pytest.mark.parametrize("d_back", [0, 3, 40])
def test_h16_dhw_and_baa_equal_the_hand_computation(d_back):
    CC = _cc()
    days, sst = _series()
    mmm = 28.0
    d_star = int(days[-1]) - d_back
    dhw, baa, missing = HK.need(CC, "heat_stats", "B1")(days, sst, mmm, d_star)
    want_dhw, want_baa = _oracle(days, sst, mmm, d_star)
    assert missing == 0
    assert dhw == pytest.approx(want_dhw, rel=1e-12, abs=1e-12)
    assert baa == want_baa


def test_h16_the_window_ends_at_d_star():
    CC = _cc()
    days, sst = _series()
    mmm = 28.0
    d_star = int(days[-1]) - 10
    base = CC.heat_stats(days, sst, mmm, d_star)
    later = sst.copy()
    later[days > d_star] = mmm + 9.0                        # heat after d*: never read
    assert CC.heat_stats(days, later, mmm, d_star)[:2] == base[:2]
    before = sst.copy()
    before[days == d_star - 84] = mmm + 9.0                 # one day before the DHW window
    assert CC.heat_stats(days, before, mmm, d_star)[0] == base[0]
    inside = sst.copy()
    inside[days == d_star - 83] = mmm + 9.0                 # the window's first day counts
    assert CC.heat_stats(days, inside, mmm, d_star)[0] > base[0]


def test_h16_a_missing_day_gives_nan():
    CC = _cc()
    days, sst = _series()
    d_star = int(days[-1])
    keep = days != d_star - 30
    dhw, baa, missing = CC.heat_stats(days[keep], sst[keep], 28.0, d_star)
    assert math.isnan(dhw) and math.isnan(baa) and missing == 1
    keep = days != d_star - 87                              # outside the DHW window, inside the BAA7d windows
    dhw, baa, missing = CC.heat_stats(days[keep], sst[keep], 28.0, d_star)
    assert math.isfinite(dhw) and math.isnan(baa)


def test_h16_baa_levels():
    CC = _cc()
    for hs, dhw, want in [(-0.5, 9, 0), (0.0, 9, 0), (0.5, 9, 1), (1.0, 0.5, 2), (1.0, 4.0, 3), (2.0, 8.0, 4),
                          (3.0, 30.0, 4)]:
        assert CC.baa_level(hs, dhw) == want == O.baa_level(hs, dhw), (hs, dhw)


def test_h16_sst_npz_is_memory_mapped_and_a_compressed_member_refuses(tmp_path):
    CC = _cc()
    k1, k2 = int(TP.site_key(-17.5, 146.25)), int(TP.site_key(10.0, -80.0))
    d1, s1 = _series(seed=2)
    d2, s2 = _series(n_days=50, seed=3)
    p = TP.write_sst_npz(tmp_path / "sst.npz", {k1: (d1, s1), k2: (d2, s2)})
    cache = HK.need(CC, "SstCache", "B1")(p)
    pos = cache.position(k1)
    d, s = cache.series(pos)
    assert np.array_equal(d, d1) and np.array_equal(np.asarray(s), s1)
    assert isinstance(cache.sst, np.memmap)
    assert cache.position(12345) == -1
    pc = tmp_path / "sst_compressed.npz"
    np.savez_compressed(str(pc), uk=np.array([k1]), start=np.array([0]), end=np.array([3]),
                        day=np.array([1, 2, 3], np.int32), sst=np.array([1, 2, 3], np.float32))
    HK.refuses("compressed", CC.member_map, pc, "sst.npy")


def _mmm_file(tmp_path):
    lat = np.round(np.arange(1.975, -2.0, -0.05), 3)            # north -> south, 0.05 degree centres
    lon = np.round(np.arange(100.025, 104.0, 0.05), 3)
    mmm = 28.0 + 0.01 * np.add.outer(np.arange(lat.size), np.arange(lon.size)) % 3
    valid = np.ones_like(mmm, dtype=bool)
    i0, j0 = 40, 40
    valid[i0 - 1:i0 + 2, j0 - 1:j0 + 2] = False                 # the pixel and its ring 1 masked
    valid[i0 + 2, j0 + 2] = True                                # ring 2 corner valid ...
    valid[i0 - 2, j0] = True                                    # ... and ring 2 straight up (closer: chosen)
    valid[10:20, 10:20] = False                                 # a 10 x 10 masked block: centre has nothing within 3
    p = TP.write_mmm_nc(tmp_path / "clim.nc", lat, lon, mmm, valid)
    return p, lat, lon, np.round(mmm, 2)


def test_h16_mmm_masked_pixel_takes_the_nearest_valid_within_3_cells(tmp_path):
    CC = _cc()
    p, lat, lon, mmm = _mmm_file(tmp_path)
    M = HK.need(CC, "OfficialMmm", "B1")(p)
    v, i, j, ring = M.at(float(lat[5]), float(lon[7]))
    assert ring == 0 and (i, j) == (5, 7) and v == pytest.approx(mmm[5, 7], abs=1e-12)
    v, i, j, ring = M.at(float(lat[40]), float(lon[40]))
    assert ring == 2 and (i, j) == (38, 40) and v == pytest.approx(mmm[38, 40], abs=1e-12)
    v, i, j, ring = M.at(float(lat[15]), float(lon[15]))
    assert math.isnan(v) and ring == -1


def test_h16_the_store_reader_never_reads_the_label_column(tmp_path):
    CC = _cc()
    f = pd.DataFrame({"row_id": ["a"], "unit_id": ["s1"], "lat": [1.0], "lon": [2.0],
                      "target_date": [dt.date(2015, 3, 1)], "issue_date": [dt.date(2015, 3, 1)],
                      "feature_end": [dt.date(2015, 2, 27)], "mark": ["train"], "pct_bleached": [12.5]})
    p = HK.write_parquet(tmp_path / "lead_0.parquet", f)
    got = HK.need(CC, "read_store", "B1")(p, "pct_bleached")
    assert "pct_bleached" not in got.columns
    HK.refuses(("label column", "pct_bleached"), CC.read_store, p, "pct_bleached",
               list(CC.STORE_KEY_COLUMNS) + ["pct_bleached"])


def test_h16_outlook_week20_window_and_nearest_ocean_ring(tmp_path):
    CO = HK.tool("coral_outlook")
    icwk = dt.date(2015, 1, 4)
    start = icwk + dt.timedelta(days=1 + 7 * 19)
    stop = icwk + dt.timedelta(days=1 + 7 * 20)
    fmt = lambda d: d.strftime("%Y%m%dT000000Z")                    # noqa: E731
    baa = np.full((360, 720), 0, dtype=np.int8)
    land = np.zeros((360, 720), dtype=bool)
    i, j = CO.grid_index(-17.5, 146.25)
    land[i, j] = True
    baa[i, j] = -5
    baa[i - 1, j] = 2
    baa[i + 1, j + 1] = 3                                           # ring 1: max 3
    p = TP.write_outlook_nc(tmp_path / "cfsv2_outlook-060perc_4mon-and-wkly_v5_icwk20150104_for_x.nc", "20150104",
                            {20: (fmt(start), fmt(stop))}, {20: baa}, land)
    arr, s, e = HK.need(CO, "read_week", "B2")(p, icwk.toordinal(), 20)
    assert (s, e) == (start.toordinal(), stop.toordinal())
    assert CO.nearest_ocean(arr, i, j) == (3, 1)
    bad = TP.write_outlook_nc(tmp_path / "bad_window.nc", "20150104",
                              {20: (fmt(start + dt.timedelta(days=7)), fmt(stop + dt.timedelta(days=7)))},
                              {20: baa}, land)
    HK.refuses(("window", "icwk"), CO.read_week, bad, icwk.toordinal(), 20)
    far = np.full((360, 720), -5, dtype=np.int8)
    assert CO.nearest_ocean(far, i, j) == (-5, -1)


def test_h16_mmm_index_holds_on_a_global_float32_axis(tmp_path):
    """Regression (2026-10-23, Part 613 addendum): NOAA's ct5km climatology stores float32 centres, so lat[1] - lat[0]
    is -0.04998779 and a step taken from the first pair drifts one whole row by -18 deg (the real D6 site
    (-17.975, -38.675) was refused). The step over the full span must map every centre back to its own index."""
    CC = _cc()
    lat = (np.float32(89.975) - np.arange(3600, dtype=np.float32) * np.float32(0.05)).astype(np.float32)
    lon = (np.float32(-38.975) + np.arange(16, dtype=np.float32) * np.float32(0.05)).astype(np.float32)
    first_pair = float(np.float64(lat[1]) - np.float64(lat[0]))
    assert abs(first_pair + 0.05) > 1e-6, "the toy axis must reproduce the float32 drift to test anything"
    mmm = np.full((lat.size, lon.size), 27.5)
    p = TP.write_mmm_nc(tmp_path / "clim_global.nc", lat, lon, mmm, np.ones_like(mmm, dtype=bool))
    M = HK.need(CC, "OfficialMmm", "B1")(p)
    for i in range(0, lat.size, 1):
        ii, jj = M.index(round(float(lat[i]), 3), round(float(lon[6]), 3))
        assert (ii, jj) == (i, 6), (i, float(lat[i]), ii)
    assert M.index(-17.975, -38.675) == (2159, 6)


def test_h16_a_hotspot_of_exactly_one_degree_counts_in_float32():
    """Regression (D6, 2026-10-23): CoralTemp SST is served to 0.01 and stored float32, so SST - MMM can be 0.99999 on a
    day NOAA counts as HotSpot 1.00. The DHW must count it (NOAA's 2-decimal arithmetic): 84 such days give DHW 12."""
    CC = _cc()
    mmm = 29.64
    days = np.arange(20000 - 120, 20001, dtype=np.int64)
    sst = np.full(days.size, np.float32(30.64), dtype=np.float32)       # float32(30.64) - 29.64 = 0.99999... in float64
    assert float(np.float64(sst[0]) - mmm) < 1.0
    dhw, baa, missing = CC.heat_stats(days, sst, mmm, int(days[-1]))
    assert missing == 0 and dhw == pytest.approx(12.0, abs=1e-9)
