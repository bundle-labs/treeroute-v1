"""T-F04 the SEAS5 lead mapping (SPEC_HUMAN_PARTB.txt 3.2, 3.5; Q16 start M-5, daily leads 150-184, members 0-24).

- month_days_in_window gives exactly the daily leads k whose valid date (start + k days) lies in the target month,
  for all 12 start months of 2015-2020 and the leap February (start 2015-09 -> Feb 2016, 29 days at leads 153..181);
  a month not wholly inside the lead window refuses;
- members 0..24 are kept and 25 dropped BY NUMBER VALUE (the reversed-number copy reads the same), a start missing
  member 7 refuses, valid_time != time + step refuses, a step set other than 150..184 d + 12 h refuses;
- x__fwi_mean equals a hand mean over 25 members x the days of the month; info_end = issue; the adapter asserts
  start = issue + 1 (a key with time - issue = 5 refuses); the scalar `surface` coordinate is ignored; a single-start
  file (scalar time, 1-D valid_time) reads the same values as the 2-D layout.
"""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def _add_months(y, m, k):
    z = y * 12 + (m - 1) + k
    return z // 12, z % 12 + 1


def _ks(res):
    return [int(k) for k in res]


def test_f04_month_days_in_window_every_start_month(geff):
    seen_leads = set()
    for y in range(2015, 2021):
        for m in range(1, 13):
            s = dt.date(y, m, 1)
            ty, tm = _add_months(y, m, 5)
            got = _ks(geff.month_days_in_window(s, ty, tm, FF.seas5_options()["lead_days"]))
            d0 = (dt.date(ty, tm, 1) - s).days
            want = list(range(d0, d0 + FF.days_in(ty, tm)))
            assert got == want, (s, ty, tm, got[:3], want[:3])
            assert all((s + dt.timedelta(days=k)).month == tm for k in got)
            assert 150 <= min(got) <= 153 and max(got) <= 183
            seen_leads |= set(got)
    assert seen_leads <= set(FF.SEAS_LEADS)


def test_f04_leap_february(geff):
    got = _ks(geff.month_days_in_window(dt.date(2015, 9, 1), 2016, 2, FF.seas5_options()["lead_days"]))
    assert got == list(range(153, 182))                  # 29 days, leads 153..181
    got = _ks(geff.month_days_in_window(dt.date(2016, 9, 1), 2017, 2, FF.seas5_options()["lead_days"]))
    assert got == list(range(153, 181))                  # 28 days


def test_f04_month_outside_the_window_refuses(geff):
    for start, (ty, tm) in ((dt.date(2019, 1, 1), (2019, 8)), (dt.date(2019, 1, 1), (2019, 5))):
        FF.refuses(geff.month_days_in_window, start, ty, tm, FF.seas5_options()["lead_days"],
                   kinds=_refusals(geff))


def _point(path, unit):
    lat, lon, valid = FF.grid_of(path)
    la, lo = FF.unit_coords(unit)
    return FF.expected_point(lat, lon, valid, la, lo, 2)


def test_f04_hand_mean_over_members_0_24(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)
    ds = FF.open_nc(raw_subsets["seas_gp_2019"])
    assert list(ds["number"].values) == list(range(26))        # member 25 is in the file: it must be dropped
    frame = geff.build(toy.ctx(), toy.rival, 6, "all")
    n = 0
    for key, starts in (("seas_gp_2015", ("2015-09-01", "2015-10-01")), ("seas_gp_2019", ("2019-01-01", "2019-02-01")),
                        ("seas_ce_2019", ("2019-01-01", "2019-02-01"))):
        group = "cerrado" if "ce" in key else "great_plains"
        for u in [r[0] for r in FF.REAL_UNITS if r[1] == group]:
            e = _point(raw_subsets[key], u)
            for s in starts:
                t, want = FF.seas5_target_hand(raw_subsets[key], s, e["i"], e["j"])
                with26 = FF.seas5_target_hand(raw_subsets[key], s, e["i"], e["j"], members=range(26))[1]
                assert want != with26                              # member 25 changes the mean: the filter shows
                row = frame[(frame["unit"] == u) & (frame["time"] == t)]
                assert len(row) == 1, (u, t)
                assert float(row["x__fwi_mean"].iloc[0]) == pytest.approx(want, rel=1e-6), (u, s)
                assert int(row["info_end"].iloc[0]) == int(row["issue"].iloc[0]) == t - 6
                n += 1
    assert n == 3 * 4 + 2 * 2
    feb = frame[(frame["time"] == FF.step(2016, 2))]
    assert len(feb) and np.isfinite(feb.loc[feb["group"] == "great_plains", "x__fwi_mean"]).all()   # leap month
    assert frame.loc[frame["time"] == FF.step(2019, 8), "x__fwi_mean"].isna().all()                 # no start
    assert frame["target_obs_end"].isna().all()


def _variant(raw, out, fn, key="seas_gp_2019"):
    ds = fn(FF.open_nc(raw[key]))
    return FF.write_nc(ds, out)


def _toy_with(raw, tmp_path, gp_2019_src):
    files = FF.seas5_raw_files(raw, srcs={"gp_2019": gp_2019_src})
    return FF.seas5_toy(tmp_path, raw, files=files)


def test_f04_members_filtered_by_number_value(geff, raw_subsets, tmp_path):
    base = geff.build(*_args(FF.seas5_toy(tmp_path / "base", raw_subsets)))
    rev = _variant(raw_subsets, tmp_path / "rev.nc", lambda ds: ds.isel(number=slice(None, None, -1)))
    assert list(FF.open_nc(rev)["number"].values)[:2] == [25, 24]
    got = geff.build(*_args(_toy_with(raw_subsets, tmp_path / "rev", rev)))
    a = _by_key(base)
    b = _by_key(got)
    np.testing.assert_allclose(b["x__fwi_mean"].to_numpy(), a["x__fwi_mean"].to_numpy(), rtol=1e-12, atol=0.0)


def _args(toy):
    return toy.ctx(), toy.rival, toy.lead, "all"


def _by_key(frame):
    return frame.sort_values(["unit", "time", "issue"], kind="mergesort").reset_index(drop=True)


def test_f04_a_missing_member_refuses(geff, raw_subsets, tmp_path):
    p = _variant(raw_subsets, tmp_path / "no7.nc", lambda ds: ds.sel(number=[k for k in range(26) if k != 7]))
    toy = _toy_with(raw_subsets, tmp_path / "toy", p)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f04_valid_time_not_time_plus_step_refuses(geff, raw_subsets, tmp_path):
    def shift(ds):
        vt = ds["valid_time"].values.copy()
        vt[1, 3] = vt[1, 3] + np.timedelta64(1, "D")
        return ds.assign_coords(valid_time=(ds["valid_time"].dims, vt, dict(ds["valid_time"].attrs)))
    p = _variant(raw_subsets, tmp_path / "vt.nc", shift)
    toy = _toy_with(raw_subsets, tmp_path / "toy", p)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f04_other_steps_refuse(geff, raw_subsets, tmp_path):
    def unrelabel(ds):
        st = ds["step"].values - np.timedelta64(1, "D")              # 149..183 d + 12 h
        ds = ds.assign_coords(step=("step", st, dict(ds["step"].attrs)))
        vt = ds["time"].values[:, None] + st[None, :]
        return ds.assign_coords(valid_time=(("time", "step"), vt, dict(ds["valid_time"].attrs)))
    p = _variant(raw_subsets, tmp_path / "steps.nc", unrelabel)
    toy = _toy_with(raw_subsets, tmp_path / "toy", p)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f04_start_must_be_issue_plus_one(geff, raw_subsets, tmp_path):
    toy = FF.seas5_toy(tmp_path, raw_subsets)
    bad = toy.table.copy()
    k = bad.index[(bad["time"] == FF.step(2019, 7))][0]
    bad.loc[k, "issue"] = bad.loc[k, "time"] - 5                     # time - issue = 5 at lead 6
    toy.table = bad
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))


def test_f04_surface_is_ignored_and_single_start_reads_the_same(geff, raw_subsets, tmp_path):
    base = _by_key(geff.build(*_args(FF.seas5_toy(tmp_path / "base", raw_subsets))))
    assert "surface" in FF.open_nc(raw_subsets["seas_gp_2019"]).coords
    nosurf = _variant(raw_subsets, tmp_path / "nosurf.nc", lambda ds: ds.drop_vars("surface"))
    got = _by_key(geff.build(*_args(_toy_with(raw_subsets, tmp_path / "nosurf", nosurf))))
    pd.testing.assert_frame_equal(got, base, check_exact=True)
    # one start per file: scalar time, 1-D valid_time (the layout of SMOKE_greece_seas_2020-06.nc)
    ds = FF.open_nc(raw_subsets["seas_gp_2019"])
    one = FF.write_nc(ds.isel(time=0), tmp_path / "one.nc")
    chk = FF.open_nc(one)
    assert chk["time"].ndim == 0 and chk["valid_time"].dims == ("step",)
    assert chk["fwinx"].dims == ("number", "step", "latitude", "longitude")
    files = FF.seas5_raw_files(raw_subsets, which=("gp_2015",))
    area = files[0]["request"]["area"]
    files.append({"file": "seas_great_plains_2019.nc", "src": one, "request": FF.seas5_request(area, 2019, [1]),
                  "regions": ["great_plains"], "starts": 1})
    files += FF.seas5_raw_files(raw_subsets, which=("ce_2019",))
    single = _by_key(geff.build(*_args(FF.seas5_toy(tmp_path / "single", raw_subsets, files=files))))
    jun = FF.step(2019, 6)
    sel = (base["time"] == jun) & (base["group"] == "great_plains")
    assert sel.sum() == 3 and np.isfinite(base.loc[sel, "x__fwi_mean"]).all()
    np.testing.assert_allclose(single.loc[sel, "x__fwi_mean"].to_numpy(), base.loc[sel, "x__fwi_mean"].to_numpy(),
                               rtol=1e-12, atol=0.0)
    jul = (single["time"] == FF.step(2019, 7)) & (single["group"] == "great_plains")
    assert single.loc[jul, "x__fwi_mean"].isna().all()               # the Feb start is not in that file


def test_f04_request_starts_must_match_the_file(geff, raw_subsets, tmp_path):
    """Each file's starts are exactly the request's (year x month) at day 1 00:00 (3.2)."""
    files = FF.seas5_raw_files(raw_subsets)
    for f in files:
        if f["file"] == "seas_great_plains_2019.nc":
            f["request"] = FF.seas5_request(f["request"]["area"], 2019, [1, 3])
    toy = FF.seas5_toy(tmp_path, raw_subsets, files=files)
    FF.refuses(geff.build, toy.ctx(), toy.rival, 6, "all", kinds=_refusals(geff))
