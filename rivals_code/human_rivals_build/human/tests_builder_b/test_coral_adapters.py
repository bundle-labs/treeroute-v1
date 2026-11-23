"""Toy tests of adapters/coral_crw.py and adapters/coral_outlook.py (SPEC_HUMAN 7 T-H16 and the coral checks)."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adapters import coral_crw as CC
from adapters import coral_outlook as CO

E = CC.EPOCH_ORDINAL
WINDOWS = {"enso": {"lags": [3, 6, 9], "reach_months": 2}, "dmi": {"lags": [2, 5, 8], "reach_months": 1}}
IDX = [(3, 2), (6, 2), (9, 2), (2, 1), (5, 1), (8, 1)]


def day(s):
    return dt.date.fromisoformat(s).toordinal() - E


# ---------------------------------------------------------------------------------------------------- the rule
def test_dhw_and_baa_hand_computation():
    days = np.arange(day("2015-01-01"), day("2015-06-30") + 1)
    sst = np.full(len(days), 28.0, dtype=np.float32)
    d_star = day("2015-05-31")
    hot = (days > d_star - 20) & (days <= d_star)          # the last 20 days to d*: HotSpot 2
    sst[hot] = 30.0
    sst[days > d_star] = 35.0                              # after d*: must never be read
    dhw, baa, miss = CC.heat_stats(days, sst, 28.0, d_star)
    assert miss == 0
    assert dhw == pytest.approx(20 * 2.0 / 7.0, abs=1e-12)
    # day d*-6 has 14 hot days -> DHW 4.0 -> Alert 1 (3); the 7-day max is 4 only if DHW >= 8 (not reached)
    assert baa == 3.0
    # one more hot day inside the window lifts DHW; a hot day after d* does not
    dhw2, _, _ = CC.heat_stats(days, sst, 28.0, d_star - 1)
    assert dhw2 == pytest.approx(19 * 2.0 / 7.0, abs=1e-12)


def test_missing_day_gives_nan_and_hotspot_below_one_does_not_count():
    days = np.arange(day("2015-01-01"), day("2015-06-30") + 1)
    sst = np.full(len(days), 28.9, dtype=np.float32)       # HotSpot 0.9: never accumulates
    d_star = day("2015-05-31")
    dhw, baa, _ = CC.heat_stats(days, sst, 28.0, d_star)
    assert dhw == 0.0 and baa == 1.0                       # Watch
    keep = days != d_star - 10
    dhw, baa, miss = CC.heat_stats(days[keep], sst[keep], 28.0, d_star)
    assert np.isnan(dhw) and np.isnan(baa) and miss == 1
    keep = days != d_star - 86                             # inside the BAA span only
    dhw, baa, miss = CC.heat_stats(days[keep], sst[keep], 28.0, d_star)
    assert np.isfinite(dhw) and np.isnan(baa)


def test_baa_levels_both_rules():
    assert CC.baa_level(-0.1, 9.0) == 0
    assert CC.baa_level(0.5, 0.0) == 1
    assert CC.baa_level(1.2, 2.0) == 2
    assert CC.baa_level(1.2, 4.0) == 3
    assert CC.baa_level(1.2, 8.0) == 4
    assert CC.baa_level(1.2, 25.0) == 4                    # NOAA's later levels merged into 4
    assert CC.baa_level(0.5, 9.0, alert_needs_hotspot=True) == 1
    assert CC.baa_level(0.5, 9.0, alert_needs_hotspot=False) == 4


def test_package_rule_and_calendar_rule_agree_on_complete_windows():
    rng = np.random.default_rng(0)
    days = np.arange(day("2014-01-01"), day("2015-12-31") + 1)
    sst = (28.5 + rng.normal(0, 1.2, len(days))).astype(np.float32)
    cut = day("2015-08-10")
    d, h = CC.package_heat(days, sst, 28.1, cut)
    w = CC._dense_window(days, sst, cut - 84, cut - 1)
    assert d == CC._dhw_from(w - 28.1)
    assert h == float(np.max(w - 28.1))


# ---------------------------------------------------------------------------------------------------- d* and store
def test_dstar_day_month_and_first_of_month_rows():
    g = 1
    # day row: C = issue = 2016-05-18 -> d* = 2016-05-16, feature_end = d*
    iss = dt.date(2016, 5, 18).toordinal()
    fe = CC.feature_end_of(iss, g, IDX)
    C, ds, kinds = CC.derive_dstar(np.array([iss]), np.array([iss]), np.array([fe]), 0, g, IDX)
    assert ds[0] == iss - 2 and fe == iss - 2 and kinds["day"] == 1
    # day row with C on the 1st: feature_end = C - 1 (index month end), but d* stays C - 2
    iss = dt.date(2016, 6, 1).toordinal()
    fe = CC.feature_end_of(iss, g, IDX)
    assert fe == iss - 1
    C, ds, _ = CC.derive_dstar(np.array([iss]), np.array([iss]), np.array([fe]), 0, g, IDX)
    assert ds[0] == iss - 2
    # month row at lead 183: target 2010-05-31, anchor 2010-05-01, C = anchor - 183
    T = dt.date(2010, 5, 31).toordinal()
    Cm = dt.date(2010, 5, 1).toordinal() - 183
    fe = CC.feature_end_of(Cm, g, IDX)
    C, ds, kinds = CC.derive_dstar(np.array([T]), np.array([T - 183]), np.array([fe]), 183, g, IDX)
    assert C[0] == Cm and ds[0] == Cm - 2 and kinds["month"] == 1
    # a feature_end that fits neither refuses
    with pytest.raises(CC.CoralAdapterRefusal):
        CC.derive_dstar(np.array([T]), np.array([T - 183]), np.array([fe + 5]), 183, g, IDX)


def test_store_reader_refuses_the_label(tmp_path):
    p = tmp_path / "s.parquet"
    pd.DataFrame({"unit_id": ["a"], "pct_bleached": [3.0]}).to_parquet(p)
    with pytest.raises(CC.CoralAdapterRefusal):
        CC.read_store(p, "pct_bleached", ["unit_id", "pct_bleached"])
    assert list(CC.read_store(p, "pct_bleached", ["unit_id"]).columns) == ["unit_id"]


# ---------------------------------------------------------------------------------------------------- toy products
SITES = [(10.1474, 97.9704), (-17.5003, 146.3012), (12.0126, 93.0833)]
MMM_TRUE = {0: 29.40, 1: 28.10, 2: 29.00}
MMM_PKG = {0: 29.55, 1: 28.02, 2: 29.31}


def write_clim(path, masked_pixel=None):
    import netCDF4
    lat = np.round(29.975 - 0.05 * np.arange(1000), 3)
    lon = np.round(90.025 + 0.05 * np.arange(1200), 3)
    raw = np.full((1, len(lat), len(lon)), 2800, np.int16)
    mask = np.zeros((1, len(lat), len(lon)), np.int8)
    for k, (la, lo) in enumerate(SITES):
        pla, plo = CC.sst_pixel(la, lo)
        i, j = int(round((pla - lat[0]) / -0.05)), int(round((plo - lon[0]) / 0.05))
        raw[0, i - 4:i + 5, j - 4:j + 5] = int(round(MMM_TRUE[k] * 100))
    if masked_pixel is not None:
        pla, plo = CC.sst_pixel(*SITES[masked_pixel])
        i, j = int(round((pla - lat[0]) / -0.05)), int(round((plo - lon[0]) / 0.05))
        raw[0, i, j] = -32768
        mask[0, i, j] = 1
    with netCDF4.Dataset(str(path), "w") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", len(lat))
        ds.createDimension("lon", len(lon))
        ds.createVariable("lat", "f4", ("lat",))[:] = lat
        ds.createVariable("lon", "f4", ("lon",))[:] = lon
        v = ds.createVariable("sst_clim_mmm", "i2", ("time", "lat", "lon"), fill_value=np.int16(-32768))
        v.scale_factor = np.float32(0.01)
        v.add_offset = np.float32(0.0)
        v.set_auto_maskandscale(False)
        v[:] = raw
        m = ds.createVariable("mask_for_sst_clim_mmm", "i1", ("time", "lat", "lon"))
        m[:] = mask


def sst_series(k, days):
    rng = np.random.default_rng(10 + k)
    doy = np.array([dt.date.fromordinal(int(d) + E).timetuple().tm_yday for d in days])
    s = MMM_TRUE[k] - 1.2 + 1.5 * np.sin(2 * np.pi * (doy - 60) / 365.0) + rng.normal(0, 0.4, len(days))
    return np.round(s, 2).astype(np.float32)


def write_npz(path, gap_site=1):
    days = np.arange(day("2008-01-01"), day("2016-12-31") + 1)
    keys = [int(CC.site_key(la, lo)) for la, lo in SITES]
    order = np.argsort(keys)
    uk, st, en, D, S = [], [], [], [], []
    pos = 0
    for k in order:
        d = days.copy()
        if k == gap_site:
            d = d[(d < day("2012-03-01")) | (d > day("2012-03-05"))]
        s = sst_series(k, d)
        uk.append(keys[k])
        st.append(pos)
        en.append(pos + len(d))
        pos += len(d)
        D.append(d)
        S.append(s)
    np.savez(str(path), uk=np.array(uk, np.int64), start=np.array(st, np.int64), end=np.array(en, np.int64),
             day=np.concatenate(D).astype(np.int32), sst=np.concatenate(S).astype(np.float32))


def store_rows(lead):
    """Visits: two per site, one day row and one month row (target = month end)."""
    rows = []
    for k, (la, lo) in enumerate(SITES):
        uid = "%03d_%.4f_%.4f" % (k + 1, la, lo)
        for T, kind in ((dt.date(2012, 4, 9 + k), "day"), (dt.date(2011, 9, 30), "month"),
                        (dt.date(2014, 3, 1), "day"), (dt.date(2015, 8, 17), "day")):
            if kind == "day":
                C = T.toordinal() - lead
            else:
                C = T.replace(day=1).toordinal() - lead
            fe = CC.feature_end_of(C, 1, IDX)
            rows.append({"row_id": "%s|%s" % (uid, T), "unit_id": uid, "group": "G%d" % k, "lat": la, "lon": lo,
                         "target_date": T, "issue_date": dt.date.fromordinal(T.toordinal() - lead),
                         "feature_end": dt.date.fromordinal(fe), "mark": "test" if T.year >= 2015 else "train",
                         "pct_bleached": 1.0, "_C": C})
    return pd.DataFrame(rows)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_coral(tmp_path, lead=0, masked_pixel=None, tamper_d6=False, tamper_replay=False):
    root = Path(tmp_path)
    sst_dir, clim_dir, store_dir, d6_dir = (root / n for n in ("sst", "clim", "store", "d6"))
    for d in (sst_dir, clim_dir, store_dir, d6_dir):
        d.mkdir(parents=True, exist_ok=True)
    write_npz(sst_dir / "sst_compact_all.npz")
    write_clim(clim_dir / "ct5km_climatology_v3.1.nc", masked_pixel)
    files = {}
    for L in (0, 183):
        s = store_rows(L)
        s.drop(columns=["_C"]).to_parquet(store_dir / ("lead_%d.parquet" % L), index=False)
        files["lead_%d.parquet" % L] = sha(store_dir / ("lead_%d.parquet" % L))
    (store_dir / "build_manifest.json").write_text(json.dumps({"params": {"sst_gap_days": 1, **WINDOWS},
                                                               "files": files}))
    s = store_rows(lead)
    keys = pd.DataFrame({"unit": s["row_id"], "group": s["group"],
                         "time": [t.toordinal() for t in s["target_date"]],
                         "issue": [t.toordinal() for t in s["issue_date"]], "lead": lead})
    # D6: two site-days, NOAA's values = our own rule (tampered -> off by 0.02)
    sst = CC.SstCache(sst_dir / "sst_compact_all.npz")
    mmm = CC.OfficialMmm(clim_dir / "ct5km_climatology_v3.1.nc")
    req = {}
    for n, (k, dstr) in enumerate([(0, "2012-04-07"), (2, "2014-02-27")]):
        la, lo = SITES[k]
        pla, plo = CC.sst_pixel(la, lo)
        m, _, _, _ = mmm.at(pla, plo)
        dd, ss = sst.series(sst.position(int(CC.site_key(la, lo))))
        dhw, baa, _ = CC.heat_stats(dd, ss, m, day(dstr))
        if tamper_d6 and n == 0:
            dhw += 0.02
        nn = "%03d" % (n + 1)
        for tag, var, val in (("dhw", "degree_heating_week", "%.2f" % dhw), ("baa7d", "bleaching_alert_area",
                                                                             "%d" % baa)):
            fn = "crw_%s_%s.csv" % (nn, tag)
            (d6_dir / fn).write_text("time,latitude,longitude,%s\nUTC,degrees_north,degrees_east,x\n%sT12:00:00Z,"
                                     "%.3f,%.3f,%s\n" % (var, dstr, pla, plo, val))
            req["%s_%s" % (nn, tag)] = {"row_id": "x", "lat": la, "lon": lo, "px_lat": pla, "px_lon": plo,
                                        "day": dstr, "file": fn}
    (d6_dir / "product_manifest.json").write_text(json.dumps({"requests": req, "files": {}}))
    # slim extras of the train rows: the package rule with the package MMM
    tr = s["mark"] == "train"
    ex = keys[tr.values].reset_index(drop=True)
    vals = []
    for _, r in s[tr].iterrows():
        k = [i for i, (la, lo) in enumerate(SITES) if la == r["lat"]][0]
        dd, ss = sst.series(sst.position(int(CC.site_key(r["lat"], r["lon"]))))
        vals.append(CC.package_heat(dd, ss, MMM_PKG[k], r["_C"] - E - 1) + (MMM_PKG[k],))
    ex["x__dhw_84"] = [v[0] for v in vals]
    ex["x__hs_max_84"] = [v[1] for v in vals]
    ex["c__ctx_mmm"] = [v[2] for v in vals]
    if tamper_replay:
        ex.loc[0, "x__dhw_84"] += 1e-6
    products = {"coral_store_20261020": store_dir, "coral_sst_npz": sst_dir, "crw_climatology": clim_dir,
                "noaa_crw_dhw_sitedays": d6_dir}
    return keys, ex, products, s


def coral_rival():
    import yaml
    reg = yaml.safe_load((Path(CC.__file__).resolve().parents[1] / "registry" / "coral.yaml").read_text())
    return {r["id"]: r for r in reg["rivals"]}


def run_build(tmp_path, fake_ctx_class, fake_run_class, lead=0, **kw):
    CC._D6_DONE.clear()
    keys, ex, products, s = make_coral(tmp_path, lead=lead, **kw)
    run = fake_run_class({0: {"fit_cut": 0}, 183: {"fit_cut": 0}},
                         plan={"max_feature_end_minus_issue_day": {"0": -1, "183": -1}})
    ctx = fake_ctx_class(tmp_path, run, "crw_dhw", products, keys={"all": keys}, extras={"train": ex})
    return CC.build(ctx, coral_rival()["crw_dhw"], lead, "all"), ctx, s


def test_build_end_to_end_d6_and_replay_pass(tmp_path, fake_ctx_class, fake_run_class):
    out, ctx, s = run_build(tmp_path, fake_ctx_class, fake_run_class)
    assert list(out.columns[:5]) == list(CC.KEYS)
    rep = out.attrs["adapter_report"]
    assert rep["d6"]["compared"] == 2 and not rep["d6"]["mismatch"]
    assert rep["replay"]["equal"] == int((s["mark"] == "train").sum())
    # the gap site's 2012-04 visit: window holds 2012-03-01..05 missing -> DHW NaN (not covered)
    gap = out["unit"].str.startswith("002_") & out["unit"].str.contains("2012-04")
    assert out.loc[gap, "x__dhw"].isna().all()
    assert out.loc[~gap, "x__dhw"].notna().all()
    # info_end = d* = C - 2; never later than issue - 1 (T1 for tables)
    assert (out["info_end"] <= out["issue"] - 1).all()
    assert out["target_obs_end"].isna().all()
    # recompute one row by hand with NOAA's MMM
    r = 0
    la, lo = s["lat"].iloc[r], s["lon"].iloc[r]
    sst = CC.SstCache(Path(tmp_path) / "sst" / "sst_compact_all.npz")
    dd, ss = sst.series(sst.position(int(CC.site_key(la, lo))))
    want, _, _ = CC.heat_stats(dd, ss, MMM_TRUE[0], int(s["_C"].iloc[r]) - E - 2)
    assert out["x__dhw"].iloc[r] == want
    assert "pct_bleached" not in str(ctx.opened)


def test_build_at_lead_183_uses_old_heat(tmp_path, fake_ctx_class, fake_run_class):
    out, _, s = run_build(tmp_path, fake_ctx_class, fake_run_class, lead=183)
    assert (out["info_end"].values == s["_C"].values - 2).all()
    assert (out["info_end"] <= out["time"] - 185).all()


def test_d6_mismatch_refuses(tmp_path, fake_ctx_class, fake_run_class):
    with pytest.raises(CC.CoralAdapterRefusal, match="D6"):
        run_build(tmp_path, fake_ctx_class, fake_run_class, tamper_d6=True)


def test_replay_mismatch_refuses(tmp_path, fake_ctx_class, fake_run_class):
    with pytest.raises(CC.CoralAdapterRefusal, match="REPLAY"):
        run_build(tmp_path, fake_ctx_class, fake_run_class, tamper_replay=True)


def test_masked_mmm_takes_nearest_valid_pixel(tmp_path):
    write_clim(tmp_path / "c.nc", masked_pixel=0)
    mmm = CC.OfficialMmm(tmp_path / "c.nc")
    m, i, j, ring = mmm.at(*CC.sst_pixel(*SITES[0]))
    assert ring == 1 and m == pytest.approx(MMM_TRUE[0])
    m2, _, _, ring2 = mmm.at(*CC.sst_pixel(*SITES[1]))
    assert ring2 == 0


def test_mmm_none_within_three_cells_is_nan(tmp_path):
    import netCDF4
    write_clim(tmp_path / "c.nc")
    pla, plo = CC.sst_pixel(*SITES[1])
    with netCDF4.Dataset(str(tmp_path / "c.nc"), "a") as ds:
        lat = ds["lat"][:]
        lon = ds["lon"][:]
        i = int(np.argmin(np.abs(lat - pla)))
        j = int(np.argmin(np.abs(lon - plo)))
        ds["mask_for_sst_clim_mmm"][0, i - 3:i + 4, j - 3:j + 4] = 1
    m, _, _, ring = CC.OfficialMmm(tmp_path / "c.nc").at(pla, plo)
    assert np.isnan(m) and ring == -1


# ---------------------------------------------------------------------------------------------------- Outlook
def write_outlook(folder, icwk, perc, value_at, week=20, bad_start=False):
    import netCDF4
    name = "cfsv2_outlook-%sperc_4mon-and-wkly_v5_icwk%s_for_x.nc" % (perc, icwk.strftime("%Y%m%d"))
    with netCDF4.Dataset(str(Path(folder) / name), "w") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", 360)
        ds.createDimension("lon", 720)
        t = ds.createVariable("time", "i4", ("time",))
        t[:] = int((dt.datetime.combine(icwk, dt.time()) + dt.timedelta(days=7) - dt.datetime(1981, 1, 1)).total_seconds())   # NOAA: icwk + 7
        ds.createVariable("lat", "f4", ("lat",))[:] = 89.75 - 0.5 * np.arange(360)
        ds.createVariable("lon", "f4", ("lon",))[:] = 0.25 + 0.5 * np.arange(720)
        arr = np.full((1, 360, 720), 0, np.int8)
        for (i, j), v in value_at.items():
            arr[0, i, j] = v
        v = ds.createVariable("CRW_BAA_Week_%02d" % week, "i1", ("time", "lat", "lon"), fill_value=np.int8(-5))
        v.set_auto_maskandscale(False)
        start = icwk + dt.timedelta(days=1 + 7 * (week - 1) + (1 if bad_start else 0))
        v.start_time = start.strftime("%Y%m%dT000000Z")
        v.stop_time = (icwk + dt.timedelta(days=1 + 7 * week)).strftime("%Y%m%dT000000Z")
        v[:] = arr
    return name


def test_outlook_week20_ring_and_mean(tmp_path, fake_ctx_class, fake_run_class):
    keys, _, products, s = make_coral(tmp_path, lead=183)
    od = Path(tmp_path) / "outlook"
    od.mkdir()
    # site 0 (10.1474, 97.9704): cell i, j; make the cell land and a ring-1 neighbour alert 2 (060) or 1..4
    i, j = CO.grid_index(*SITES[0])
    T = dt.date(2012, 4, 9)                                 # site 0's 2012 visit (target day)
    ic = T - dt.timedelta(days=134)
    while ic.weekday() != 6:                                # a Sunday with T in [ic + 134, ic + 141)
        ic -= dt.timedelta(days=1)
    assert ic + dt.timedelta(days=134) <= T < ic + dt.timedelta(days=141)
    for perc, val in (("010", 1), ("030", 2), ("060", 3), ("090", 4)):
        write_outlook(od, ic, perc, {(i, j): -5, (i - 1, j): val, (i + 1, j + 1): 0})
    products["crw_outlook"] = od
    run = fake_run_class({183: {"fit_cut": 0}}, plan={"max_feature_end_minus_issue_day": {"183": -1}})
    ctx = fake_ctx_class(tmp_path, run, "crw_outlook", products, keys={"all": keys})
    out = CO.build(ctx, coral_rival()["crw_outlook"], 183, "all")
    row = out["unit"] == s["row_id"].iloc[0]
    assert out.loc[row, "x__baa060_w20"].iloc[0] == 3.0       # max within ring 1
    assert out.loc[row, "x__baa4p_w20"].iloc[0] == 2.5
    assert out.loc[row, "info_end"].iloc[0] == ic.toordinal() + 7          # available at the file time = icwk + 7
    assert out.loc[row, "info_end"].iloc[0] > out.loc[row, "issue"].iloc[0]   # advantaged: breaks T1
    inwin = (out["time"] >= (ic + dt.timedelta(days=134)).toordinal()) & \
            (out["time"] < (ic + dt.timedelta(days=141)).toordinal())
    assert out.loc[~inwin, "x__baa060_w20"].isna().all()      # no issue on disk for the other targets
    assert out.loc[inwin, "x__baa060_w20"].notna().all()
    assert (out.loc[inwin & ~row, "x__baa060_w20"] == 0.0).all()
    assert out.loc[row, "product_cell"].iloc[0].endswith("_r1")


def test_outlook_window_attribute_checked(tmp_path, fake_ctx_class, fake_run_class):
    keys, _, products, s = make_coral(tmp_path, lead=183)
    od = Path(tmp_path) / "outlook"
    od.mkdir()
    T = dt.date(2012, 4, 9)
    ic = T - dt.timedelta(days=134)
    while ic.weekday() != 6:
        ic -= dt.timedelta(days=1)
    for perc in ("010", "030", "060", "090"):
        write_outlook(od, ic, perc, {}, bad_start=(perc == "060"))
    products["crw_outlook"] = od
    run = fake_run_class({183: {"fit_cut": 0}}, plan={"max_feature_end_minus_issue_day": {"183": -1}})
    ctx = fake_ctx_class(tmp_path, run, "crw_outlook", products, keys={"all": keys})
    with pytest.raises(CO.OutlookRefusal, match="window"):
        CO.build(ctx, coral_rival()["crw_outlook"], 183, "all")


def test_outlook_refuses_a_staged_call(tmp_path, fake_ctx_class, fake_run_class):
    with pytest.raises(CO.OutlookRefusal):
        CO.build(None, coral_rival()["crw_outlook"], 183, "train")


def test_dstar_second_of_month_is_a_day_row_not_a_month_row():
    # C = 2005-03-02 (day row): feature_end = 2005-02-28, the same as a month row of March would have
    iss = dt.date(2005, 3, 2).toordinal()
    fe = CC.feature_end_of(iss, 1, IDX)
    assert fe == dt.date(2005, 2, 28).toordinal()
    C, ds, kinds = CC.derive_dstar(np.array([iss]), np.array([iss]), np.array([fe]), 0, 1, IDX)
    assert kinds == {"day": 1, "month": 0} and ds[0] == iss - 2
    with pytest.raises(CC.CoralAdapterRefusal, match="neither"):
        CC.derive_dstar(np.array([iss]), np.array([iss]), np.array([iss - 10]), 0, 1, IDX)
