"""T-F02 the ERA5 reader (SPEC_HUMAN_PARTB.txt 3.2, 3.3, 3.5; review R-15): adapters/fire_geff.py on a subset of
D:/fire/cems/raw/SMOKE_hist_multiyear.nc (greece 2018-2019, 6 x 6 points with sea points), the RAW layout kept.

- x__fwi_mean of every covered (unit, month) equals a hand numpy mean of the finite days at the unit's point (the
  brute-force haversine point of spec 3.3);
- the sea points of the subset are found (all-NaN); a coastal unit whose nearest point is sea takes the nearest land
  point inside the 5 x 5 window, with its distance recorded in the audit file;
- 8 NaN days of a 31-day month -> NaN (MINDAYS 0.8); 5 NaN days -> the mean of the 26 finite days;
- a missing calendar day in valid_time -> refuse; two files of one box on different grids -> refuse;
- the subset with the scalar `surface` coordinate and an extra data variable (kbdi, written before fwinx) reads
  byte-equal to the same subset without them; fwinx with an extra (non-scalar) dim -> refuse.
"""

import json

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def _build(geff, toy, **ctx_over):
    ctx = toy.ctx(**ctx_over)
    return geff.build(ctx, toy.rival, toy.lead, "all"), ctx


def _sorted(frame):
    return frame.sort_values(["unit", "time", "issue"], kind="mergesort").reset_index(drop=True)


def _audit(ctx, lead):
    p = ctx.work_dir() / ("map_units_lead_%d.json" % lead)
    assert p.is_file(), "the adapter wrote no audit file %s (spec 3.3)" % p
    return json.loads(p.read_text(encoding="utf-8"))


def _hand_frame(path, units, window=2, min_share=0.8):
    """{(unit, step): hand mean} for every unit of the toy (spec 3.3 point, 3.5 mean)."""
    lat, lon, valid = FF.grid_of(path)
    out, pts = {}, {}
    for u in units:
        la, lo = FF.unit_coords(u)
        e = FF.expected_point(lat, lon, valid, la, lo, window)
        pts[u] = e
        if e["uncovered"]:
            continue
        for s, v in FF.era5_monthly_hand(path, e["i"], e["j"], min_share).items():
            out[(u, s)] = v
    return out, pts


def test_f02_unit_month_means_equal_a_hand_computation(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    frame, ctx = _build(geff, toy)
    hand, pts = _hand_frame(raw_subsets["era5_greece"], toy.units["unit"])
    assert not any(e["uncovered"] for e in pts.values())
    got = frame.set_index(["unit", "time"])["x__fwi_mean"]
    n = 0
    for (u, t), v in got.items():
        want = hand.get((u, t), np.nan)
        if np.isnan(want):
            assert np.isnan(v), (u, t, v)
        else:
            assert v == pytest.approx(want, rel=1e-6, abs=1e-9), (u, t, v, want)
            n += 1
    assert n == len(toy.units) * 23                     # 23 product months among the keys (2019-04 held by no set)
    out = frame[frame["time"] == FF.step(2020, 1)]
    assert len(out) == len(toy.units) and out["x__fwi_mean"].isna().all()     # outside the product -> NaN


def test_f02_sea_points_found_and_the_coastal_unit_substituted(geff, raw_subsets, tmp_path):
    lat, lon, valid = FF.grid_of(raw_subsets["era5_greece"])
    assert (~valid).sum() >= 3, "the subset must hold sea points"
    assert not valid[4, 0] and not valid[4, 1]          # (37.25, 20.75) and (37.25, 21.0): sea in RAW
    toy = FF.era5_toy(tmp_path, raw_subsets)
    frame, ctx = _build(geff, toy)
    units = FF.audit_units(_audit(ctx, 0))
    assert set(units) == set(toy.units["unit"])
    la, lo = FF.unit_coords("greece_mainland_syn_sea")
    e = FF.expected_point(lat, lon, valid, la, lo, 2)
    assert e["substituted"] and not e["uncovered"]
    rec = units["greece_mainland_syn_sea"]
    assert bool(rec["substituted"]) is True and not bool(rec["uncovered"])
    assert (int(rec["i"]), int(rec["j"])) == (e["i"], e["j"])
    assert float(rec["dist_km"]) == pytest.approx(e["dist_km"], rel=1e-9)
    for u in ("greece_mainland_603_1131", "greece_mainland_604_1146", "greece_mainland_595_1135"):
        la, lo = FF.unit_coords(u)
        e = FF.expected_point(lat, lon, valid, la, lo, 2)
        assert not e["substituted"]
        assert (int(units[u]["i"]), int(units[u]["j"])) == (e["i"], e["j"]) and not bool(units[u]["substituted"])
        assert float(units[u]["dist_km"]) == pytest.approx(e["dist_km"], rel=1e-9)
    sub = frame[frame["unit"] == "greece_mainland_syn_sea"]
    assert np.isfinite(sub["x__fwi_mean"]).sum() == 23
    la, lo = FF.unit_coords("greece_mainland_syn_sea")
    e = FF.expected_point(lat, lon, valid, la, lo, 2)
    assert set(sub.loc[np.isfinite(sub["x__fwi_mean"]), "product_cell"]) == {
        geff.product_cell_id("greece_mainland", lat[e["i"]], lon[e["j"]])}
    hand = FF.era5_monthly_hand(raw_subsets["era5_greece"], e["i"], e["j"])
    for t, v in zip(sub["time"], sub["x__fwi_mean"]):
        if np.isfinite(v):
            assert v == pytest.approx(hand[int(t)], rel=1e-6)


def _nan_days(raw, out, point, days_by_month):
    """A copy of the greece subset with NaN days at one LAND point: {(year, month): n days}."""
    ds = FF.open_nc(raw["era5_greece"])
    v = ds["fwinx"].values.copy()
    t = pd.DatetimeIndex(ds["valid_time"].values)
    for (y, m), n in days_by_month.items():
        idx = np.flatnonzero((t.year == y) & (t.month == m))[:n]
        v[idx, point[0], point[1]] = np.nan
    ds["fwinx"] = (ds["fwinx"].dims, v, ds["fwinx"].attrs)
    return FF.write_nc(ds, out)


def test_f02_mindays_rule(geff, raw_subsets, tmp_path):
    lat, lon, valid = FF.grid_of(raw_subsets["era5_greece"])
    la, lo = FF.unit_coords("greece_mainland_603_1131")
    e = FF.expected_point(lat, lon, valid, la, lo, 2)
    assert not e["substituted"]
    p = _nan_days(raw_subsets, tmp_path / "nan_days.nc", (e["i"], e["j"]), {(2018, 7): 8, (2018, 8): 5})
    files = [{"file": "hist_greece_mainland_2018-2019.nc", "src": p,
              "request": FF.era5_request(FF.GREECE_AREA, [2018, 2019]), "regions": ["greece_mainland"]}]
    toy = FF.era5_toy(tmp_path / "toy", raw_subsets, files=files)
    frame, ctx = _build(geff, toy)
    f = frame[frame["unit"] == "greece_mainland_603_1131"].set_index("time")["x__fwi_mean"]
    assert np.isnan(f[FF.step(2018, 7)])                       # 23 of 31 days: 0.74 < 0.8 -> not covered
    hand = FF.era5_monthly_hand(p, e["i"], e["j"])
    assert f[FF.step(2018, 8)] == pytest.approx(hand[FF.step(2018, 8)], rel=1e-6)    # 26 of 31 finite days
    assert np.isfinite(f[FF.step(2018, 6)])
    la2, lo2 = FF.unit_coords("greece_mainland_604_1146")
    e2 = FF.expected_point(lat, lon, valid, la2, lo2, 2)
    if (e2["i"], e2["j"]) != (e["i"], e["j"]):                     # another point is untouched
        other = frame[(frame["unit"] == "greece_mainland_604_1146") & (frame["time"] == FF.step(2018, 7))]
        assert np.isfinite(other["x__fwi_mean"]).all()


def test_f02_missing_calendar_day_refuses(geff, raw_subsets, tmp_path):
    ds = FF.open_nc(raw_subsets["era5_greece"])
    keep = np.ones(ds.sizes["valid_time"], dtype=bool)
    keep[200] = False                                          # 2018-07-20 gone
    p = FF.write_nc(ds.isel(valid_time=np.flatnonzero(keep)), tmp_path / "gap.nc")
    files = [{"file": "hist_greece_mainland_2018-2019.nc", "src": p,
              "request": FF.era5_request(FF.GREECE_AREA, [2018, 2019]), "regions": ["greece_mainland"]}]
    toy = FF.era5_toy(tmp_path / "toy", raw_subsets, files=files)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f02_a_date_outside_the_request_years_refuses(geff, raw_subsets, tmp_path):
    files = [{"file": "hist_greece_mainland_2018-2018.nc", "src": raw_subsets["era5_greece"],
              "request": FF.era5_request(FF.GREECE_AREA, [2018]), "regions": ["greece_mainland"]}]
    toy = FF.era5_toy(tmp_path / "toy", raw_subsets, files=files)            # the file holds 2019 too
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def _split_years(raw, out, shift_second=False):
    ds = FF.open_nc(raw["era5_greece"])
    t = pd.DatetimeIndex(ds["valid_time"].values)
    a = ds.isel(valid_time=np.flatnonzero(t.year == 2018))
    b = ds.isel(valid_time=np.flatnonzero(t.year == 2019))
    if shift_second:
        b = b.assign_coords(latitude=("latitude", b["latitude"].values - 0.25, dict(b["latitude"].attrs)))
    pa = FF.write_nc(a, out / "a.nc")
    pb = FF.write_nc(b, out / "b.nc")
    return [{"file": "hist_greece_mainland_2018-2018.nc", "src": pa,
             "request": FF.era5_request(FF.GREECE_AREA, [2018]), "regions": ["greece_mainland"]},
            {"file": "hist_greece_mainland_2019-2019.nc", "src": pb,
             "request": FF.era5_request(FF.GREECE_AREA, [2019]), "regions": ["greece_mainland"]}]


def test_f02_two_files_of_one_box(geff, raw_subsets, tmp_path):
    """Same grid: the two-file box reads the same values as the one-file box; another grid: refuse."""
    one, _ = _build(geff, FF.era5_toy(tmp_path / "one", raw_subsets))
    files = _split_years(raw_subsets, tmp_path)
    two, ctx = _build(geff, FF.era5_toy(tmp_path / "two", raw_subsets, files=files))
    np.testing.assert_array_equal(_sorted(one)["x__fwi_mean"].to_numpy(), _sorted(two)["x__fwi_mean"].to_numpy())
    assert set(two["src"]) - {""} == {"hist_greece_mainland_2018-2018.nc", "hist_greece_mainland_2019-2019.nc"}
    bad = _split_years(raw_subsets, tmp_path / "bad", shift_second=True)
    toy = FF.era5_toy(tmp_path / "shifted", raw_subsets, files=bad)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f02_surface_and_extra_variable_are_ignored(geff, raw_subsets, tmp_path):
    ds = FF.open_nc(raw_subsets["era5_greece"])
    assert "surface" in ds.coords and ds["surface"].ndim == 0
    assert list(ds.data_vars)[0] == "kbdi"                       # the extra variable comes first in the file
    plain = FF.open_nc(raw_subsets["era5_plain"])
    assert "surface" not in plain.coords and list(plain.data_vars) == ["fwinx"]
    a, _ = _build(geff, FF.era5_toy(tmp_path / "with", raw_subsets, key="era5_greece"))
    b, _ = _build(geff, FF.era5_toy(tmp_path / "without", raw_subsets, key="era5_plain"))
    pd.testing.assert_frame_equal(_sorted(a), _sorted(b), check_exact=True)


def test_f02_extra_dim_on_fwinx_refuses(geff, raw_subsets, tmp_path):
    ds = FF.open_nc(raw_subsets["era5_plain"])
    v = ds["fwinx"].expand_dims(level=[1, 2]).transpose("valid_time", "level", "latitude", "longitude")
    p = FF.write_nc(ds.drop_vars("fwinx").assign(fwinx=v), tmp_path / "level.nc")
    files = [{"file": "hist_greece_mainland_2018-2019.nc", "src": p,
              "request": FF.era5_request(FF.GREECE_AREA, [2018, 2019]), "regions": ["greece_mainland"]}]
    toy = FF.era5_toy(tmp_path / "toy", raw_subsets, files=files)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f02_missing_variable_refuses(geff, raw_subsets, tmp_path):
    ds = FF.open_nc(raw_subsets["era5_plain"]).rename({"fwinx": "fwi"})
    p = FF.write_nc(ds, tmp_path / "renamed.nc")
    files = [{"file": "hist_greece_mainland_2018-2019.nc", "src": p,
              "request": FF.era5_request(FF.GREECE_AREA, [2018, 2019]), "regions": ["greece_mainland"]}]
    toy = FF.era5_toy(tmp_path / "toy", raw_subsets, files=files)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f02_lead0_keys_must_have_time_equal_issue(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets)
    bad = toy.table.copy()
    bad.loc[bad.index[0], "issue"] = bad.loc[bad.index[0], "issue"] - 1
    toy.table = bad
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))
