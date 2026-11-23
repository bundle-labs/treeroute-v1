"""Builder C toy tests: PM2.5 reanalysis adapter (T-H18), NDVI H1 runner (T-H19), Kraft (CPU toy), Kraft prep.

Run from D:\\treeroute\\human_rivals_build\\human (fresh basetemp; its parent must exist):
  set PYTHONDONTWRITEBYTECODE=1
  py -3.9 -B -m pytest tests_builder_c -p no:cacheprovider --basetemp D:\\treeroute\\human_rivals_build\\pt\\pm25_ndvi\\<fresh>

Toy data only, written under the basetemp. The ctx objects here are minimal stand-ins of builder A's AdapterCtx
(rivals_human/index.py:184-310): the same method names and return shapes. Builder D may fold these into
rivals_human/tests.
"""
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True
HUMAN_ROOT = Path(__file__).resolve().parents[1]
if str(HUMAN_ROOT) not in sys.path:
    sys.path.insert(0, str(HUMAN_ROOT))

from adapters import pm25_reanalysis as PM        # noqa: E402
from adapters import ndvi_bardl as BD             # noqa: E402

KEYS = ["unit", "group", "time", "issue", "lead"]
D1_LINE = "D1 (CAMS EAC4) is not on disk: run DOWNLOAD_COMMANDS.md 2.2 first"


def step(y, m):
    return y * 12 + m


class FakeRun(object):
    def __init__(self, offset=0, r8=None):
        self.derived = {"R17": {"inputs": {"steps_per_year": 12}, "value": {"start_offset_steps": offset}},
                        "R8": {"value": r8 or {}}}


# =============================================================================================== PM2.5 (T-H18)
LAT_NODES = np.arange(-90.0, 90.0 + 1e-9, 30.0)          # 7
LON360_NODES = np.arange(0.0, 360.0, 30.0)               # 12
UNITS = pd.DataFrame({"cell_id": ["u_a", "u_b", "u_seam", "u_other"],
                      "region": ["r1", "r1", "r2", "r2"],
                      "lat": [15.0, -40.0, 0.0, 50.0], "lon": [45.0, -100.0, -10.0, 10.0]})


def field(lat, lon360, k):
    """Linear in latitude and in [0, 360) longitude inside every grid cell (bilinear is exact away from the seam)."""
    return (10.0 + 0.1 * lat + 0.05 * lon360) * (1.0 + 0.01 * k)


def month_list():
    return [(2003, m) for m in range(1, 13)] + [(2004, m) for m in range(1, 13)]


def write_merra(folder: Path):
    import netCDF4

    folder.mkdir(parents=True)
    lon = np.where(LON360_NODES >= 180, LON360_NODES - 360, LON360_NODES)
    order = np.argsort(lon)
    lon_sorted = lon[order]
    files = {}
    for k, (y, m) in enumerate(month_list()):
        name = "aer_%04d%02d.nc" % (y, m)
        ds = netCDF4.Dataset(str(folder / name), "w")
        ds.createDimension("time", 1)
        ds.createDimension("lat", LAT_NODES.size)
        ds.createDimension("lon", lon_sorted.size)
        t = ds.createVariable("time", "i4", ("time",))
        t.units = "minutes since %04d-%02d-01T00:30:00" % (y, m)
        t[:] = [0]
        la = ds.createVariable("lat", "f8", ("lat",))
        la[:] = LAT_NODES
        lo = ds.createVariable("lon", "f8", ("lon",))
        lo[:] = lon_sorted
        f = field(LAT_NODES[:, None], np.mod(lon_sorted, 360.0)[None, :], k) * 1e-9
        shares = {"DUSMASS25": 0.2, "SSSMASS25": 0.2, "BCSMASS": 0.2, "OCSMASS": 0.2 / 1.4, "SO4SMASS": 0.2 / 1.375}
        for v, sh in shares.items():
            var = ds.createVariable(v, "f4", ("time", "lat", "lon"))
            var.units = "kg m-3"
            var[0] = (f * sh).astype(np.float32)
        ds.close()
        files[name] = {"sha256": "x"}
    return files


def write_eac4(folder: Path):
    import netCDF4
    import datetime as dt

    folder.mkdir(parents=True)
    nc = folder / "_inner.nc"
    ds = netCDF4.Dataset(str(nc), "w")
    months = month_list()
    lat_desc = LAT_NODES[::-1]
    ds.createDimension("valid_time", len(months))
    ds.createDimension("latitude", lat_desc.size)
    ds.createDimension("longitude", LON360_NODES.size)
    t = ds.createVariable("valid_time", "i8", ("valid_time",))
    t.units = "seconds since 1970-01-01"
    t[:] = [int((dt.datetime(y, m, 1) - dt.datetime(1970, 1, 1)).total_seconds()) for y, m in months]
    la = ds.createVariable("latitude", "f8", ("latitude",))
    la[:] = lat_desc
    lo = ds.createVariable("longitude", "f8", ("longitude",))
    lo[:] = LON360_NODES
    v = ds.createVariable("pm2p5", "f8", ("valid_time", "latitude", "longitude"))
    v.units = "kg m**-3"
    for k in range(len(months)):
        v[k] = field(lat_desc[:, None], LON360_NODES[None, :], k) * 1e-9
    ds.close()
    zpath = folder / "eac4_pm2p5_monthly_2003-2023.zip"
    with zipfile.ZipFile(str(zpath), "w") as zf:
        zf.write(str(nc), "data_sfc.nc")
    nc.rename(folder / "_inner.nc.kept")      # not listed in the manifest; never opened
    return {zpath.name: {"sha256": "x"}}


class PmCtx(object):
    def __init__(self, base: Path, keys: pd.DataFrame, available=("merra2", "eac4", "static")):
        self.run = FakeRun(offset=0, r8={"burn_frac": {"steps": 1}})
        self._keys = keys
        self.lines = []
        self.products = {}
        st = base / "static"
        st.mkdir(parents=True, exist_ok=True)
        UNITS.to_parquet(str(st / "part-0.parquet"), index=False)
        self.products["static"] = (st, {"part-0.parquet": {}})
        if not (base / "merra2").exists():
            self.products["merra2"] = (base / "merra2", write_merra(base / "merra2"))
            self.products["eac4"] = (base / "eac4", write_eac4(base / "eac4"))
        else:
            self.products["merra2"] = (base / "merra2", {p.name: {} for p in (base / "merra2").glob("aer_*.nc")})
            self.products["eac4"] = (base / "eac4", {p.name: {} for p in (base / "eac4").glob("*.zip")})
        self.available = set(available)
        self.opened = []

    def keys(self, set_name="stage"):
        return self._keys.copy()

    def product_available(self, pid):
        return pid in self.available

    def product_files(self, pid):
        if pid not in self.available:
            raise RuntimeError("product %s refused" % pid)
        return sorted(self.products[pid][1])

    def open_product(self, pid, name):
        if pid not in self.available:
            raise RuntimeError("product %s refused" % pid)
        self.opened.append((pid, name))
        return self.products[pid][0] / name

    def log(self, message):
        self.lines.append(message)


def pm_rival(pid, reader, offset, shift=0):
    opt = {"product": pid, "reader": reader, "scale": 1e9, "month_offset": offset, "units_attr": "kg m-3",
           "unit_centres": {"product": "static", "file": "part-0.parquet", "id": "cell_id", "lat": "lat", "lon": "lon"},
           "missing_message": D1_LINE if pid == "eac4" else None}
    if reader == "monthly_files":
        opt["file_pattern"] = "aer_{year:04d}{month:02d}.nc"
        opt["variables"] = {"DUSMASS25": 1.0, "SSSMASS25": 1.0, "BCSMASS": 1.0, "OCSMASS": 1.4, "SO4SMASS": 1.375}
    else:
        opt["variables"] = {"pm2p5": 1.0}
    if shift:
        opt["placebo_shift_years"] = shift
    return {"id": "%s_%d_%d" % (pid, offset, shift), "kind": "N", "stats": ["x__pm25"], "options": opt,
            "products": [pid, "static"], "leads": {0: {"tier": "P"}}, "reads_target_in_test_window": False}


def pm_keys():
    rows = []
    for u in ["u_a", "u_b", "u_seam"]:
        for y, m in month_list():
            t = step(y, m)
            rows.append({"unit": u, "group": "g1", "time": t, "issue": t, "lead": 0})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def pm_base(tmp_path_factory):
    return tmp_path_factory.mktemp("pm25")


def expected(unit, k):
    r = UNITS.set_index("cell_id").loc[unit]
    return field(r["lat"], np.mod(r["lon"], 360.0), k)


def test_pm25_bilinear_flip_wrap_and_tiers(pm_base):
    keys = pm_keys()
    ctx = PmCtx(pm_base, keys)
    first = step(2003, 1)
    out = {}
    for pid, reader in (("merra2", "monthly_files"), ("eac4", "netcdf_zip")):
        for off in (-1, 0):
            f = PM.build(ctx, pm_rival(pid, reader, off), 0, "all")
            assert list(f.columns) == KEYS + ["x__pm25", "info_end", "target_obs_end", "product_cell", "src"]
            assert f["info_end"].dtype == np.int64
            np.testing.assert_array_equal(f["info_end"].to_numpy(), keys["issue"].to_numpy() + off)
            out[(pid, off)] = f
    # the two products agree (lat flip of EAC4, lon -180.. of MERRA-2 vs 0..360 of EAC4; the seam wrap)
    for off in (-1, 0):
        a, b = out[("merra2", off)], out[("eac4", off)]
        np.testing.assert_allclose(a["x__pm25"].to_numpy(), b["x__pm25"].to_numpy(), rtol=1e-6, equal_nan=True)
        assert (a["product_cell"].to_numpy() == b["product_cell"].to_numpy()).all()
    # exact values away from the seam: P row reads month t-1, A row month t; the first P month has no product
    for off in (-1, 0):
        f = out[("eac4", off)]
        for u in ("u_a", "u_b"):
            r = f[f["unit"] == u]
            k = r["issue"].to_numpy() + off - first
            ok = k >= 0
            np.testing.assert_allclose(r["x__pm25"].to_numpy()[ok], [expected(u, kk) for kk in k[ok]], rtol=1e-12)
            assert np.isnan(r["x__pm25"].to_numpy()[~ok]).all()
            assert (r["src"].to_numpy()[~ok] == "").all()
            assert np.isnan(r["target_obs_end"].to_numpy()[~ok]).all()
            np.testing.assert_array_equal(r["target_obs_end"].to_numpy()[ok], (r["issue"].to_numpy() + off)[ok])
        assert int(np.isnan(f["x__pm25"]).sum()) == (3 if off == -1 else 0)
    # the seam point (lon 350 = between the 330 and 0/360 nodes): hand bilinear
    f = out[("eac4", 0)]
    r = f[f["unit"] == "u_seam"].iloc[0]
    k = int(r["issue"]) - first
    left, right = field(0.0, 330.0, k), field(0.0, 0.0, k)
    assert abs(r["x__pm25"] - (left + (350.0 - 330.0) / 30.0 * (right - left))) < 1e-9


def test_pm25_eac4_refuses_without_d1(pm_base):
    ctx = PmCtx(pm_base, pm_keys(), available=("merra2", "static"))
    rival = pm_rival("eac4", "netcdf_zip", -1)
    ok, line = PM.availability(ctx, rival)
    assert not ok and line == D1_LINE
    with pytest.raises(PM.Pm25AdapterRefusal) as e:
        PM.build(ctx, rival, 0, "all")
    assert str(e.value) == D1_LINE
    assert ctx.opened == []                       # nothing was opened before the refusal


def test_pm25_placebo_and_unit_refusal(pm_base):
    keys = pm_keys()
    ctx = PmCtx(pm_base, keys)
    first = step(2003, 1)
    f = PM.build(ctx, pm_rival("merra2", "monthly_files", -1, shift=1), 0, "all")
    read = keys["issue"].to_numpy() - 1 - 12
    np.testing.assert_array_equal(f["info_end"].to_numpy(), read)
    ok = read >= first
    r = f[f["unit"] == "u_a"]
    rk = r["issue"].to_numpy() - 1 - 12 - first
    good = rk >= 0
    np.testing.assert_allclose(r["x__pm25"].to_numpy()[good], [expected("u_a", kk) for kk in rk[good]], rtol=1e-6)
    assert int(np.isfinite(f["x__pm25"]).sum()) == int(ok.sum())
    assert (f["info_end"].to_numpy() <= keys["issue"].to_numpy() - 1).all()      # never a later month
    bad = keys.copy()
    bad.loc[0, "unit"] = "u_missing"
    with pytest.raises(PM.Pm25AdapterRefusal):
        PM.build(PmCtx(pm_base, bad), pm_rival("merra2", "monthly_files", -1), 0, "all")


def test_pm25_grid_checks():
    g = PM.Grid(np.array([90.0, 0.0, -90.0]), np.arange(0.0, 360.0, 90.0))
    assert g.flip_lat and list(g.lat) == [-90.0, 0.0, 90.0]
    with pytest.raises(PM.Pm25AdapterRefusal):
        PM.Grid(np.array([0.0, 1.0, 3.0]), np.arange(0.0, 360.0, 90.0))       # irregular
    with pytest.raises(PM.Pm25AdapterRefusal):
        PM.Grid(np.array([0.0, 1.0]), np.arange(0.0, 180.0, 90.0))            # not global
    w = g.weights(np.array([45.0]), np.array([-45.0]))                        # 315 deg: between 270 and 0
    f = np.arange(12, dtype=float).reshape(3, 4)
    v = PM.Grid.interpolate(f, w)
    assert abs(v[0] - (0.5 * (0.5 * f[1, 3] + 0.5 * f[1, 0]) + 0.5 * (0.5 * f[2, 3] + 0.5 * f[2, 0]))) < 1e-12


# =============================================================================================== NDVI H1 (T-H19)
class SS(object):
    def __init__(self, keys, normal, history, extras):
        self.keys, self.normal, self.history, self.extras, self.y = keys, normal, history, extras, None


class NdCtx(object):
    FIT = ("refit", "tune", "guardfit")

    def __init__(self, sets, units, offset=1, lead=0):
        self.run = FakeRun(offset=offset)
        self.sets = sets
        self._units = units
        self.lead = lead
        self.label_calls = []
        self.lines = []

    def units(self):
        return self._units.copy()

    def features(self, name):
        k, y, z, h, e = self.sets[name]
        return SS(k.copy(), {"identity": z.copy()}, h.copy(), e.copy())

    def fit_labels(self, name):
        if name not in self.FIT:
            raise RuntimeError("labels of %s refused" % name)
        self.label_calls.append(name)
        k, y, z, h, e = self.sets[name]
        return k.copy(), y.copy(), {"identity": z.copy()}

    def t2_step(self, keys):        # builder A's Timing.t2_step (rivals_human/index.py:84-89)
        t = keys["time"].to_numpy(np.int64)
        return t - (1 if self.lead == 0 else self.lead) - int(self.run.derived["R17"]["value"]["start_offset_steps"])

    def log(self, m):
        self.lines.append(m)


H1_RIVAL = {"id": "bardl_h1", "kind": "M",
            "options": {"history": ["hist_last_1", "hist_last_2", "hist_last_3"],
                        "climate": {"precip": ["V02_total_precip_mm", "V02_total_precip_mm_lag1",
                                               "V02_total_precip_mm_lag2"],
                                    "soil_moisture": ["V30_soil_moisture_pct", "V30_soil_moisture_pct_lag1",
                                                      "V30_soil_moisture_pct_lag2"]},
                        "min_fit_rows": 36}}


def make_ndvi(seed_rng=0):
    """A synthetic per-unit ARDL: a(s) = 0.6 a(s-2) + 0.001 (P(s) - Pclim) + noise(0.02). At lead 0 with offset 1
    the newest readable label is t-2, so hist_last_1 = y(t-2) carries the AR term. The innovation is large enough
    that a(t-2) is not a near-copy of a(t-4) and P(t-2) (else the lag split is not identified)."""
    rng = np.random.default_rng(seed_rng)
    s0, s1 = step(2000, 1), step(2019, 12)
    S = np.arange(s0, s1 + 1)
    pos = (S - 1) % 12 + 1
    series = {}
    for j, u in enumerate(["u0", "u1", "u2", "u3", "u4"]):
        nrm = 0.3 + 0.15 * np.sin(2 * np.pi * pos / 12) + 0.02 * j
        pcl = 60 + 40 * np.sin(2 * np.pi * pos / 12 + 1)
        P = pcl + rng.normal(0, 15, S.size)
        SM = 30 + 5 * np.sin(2 * np.pi * pos / 12) + rng.normal(0, 2, S.size)
        a = np.zeros(S.size)
        for i in range(2, S.size):
            a[i] = 0.6 * a[i - 2] + 0.001 * (P[i] - pcl[i]) + rng.normal(0, 0.02)
        series[u] = {"S": S, "pos": pos, "nrm": nrm, "P": P, "SM": SM, "y": nrm + a,
                     "signal": None, "a": a, "pcl": pcl}
    return series


def ndvi_set(series, t_lo, t_hi, lead=0, units=("u0", "u1", "u2", "u3", "u4")):
    rows, z, y, H, E = [], [], [], [], []
    for u in units:
        d = series[u]
        S = d["S"]
        at = {int(s): i for i, s in enumerate(S)}
        for t in range(t_lo, t_hi + 1):
            i = t - lead
            t2 = (t - 1 if lead == 0 else t - lead) - 1
            if (t2 - 2) not in at or (i - 2) not in at:
                continue
            rows.append({"unit": u, "group": "g_" + u, "time": t, "issue": i, "lead": lead})
            z.append(d["nrm"][at[t]])
            y.append(d["y"][at[t]])
            H.append({"x__hist_last_%d" % k: d["y"][at[t2 - (k - 1)]] for k in (1, 2, 3)})
            E.append({"x__V02_total_precip_mm": d["P"][at[i]], "x__V02_total_precip_mm_lag1": d["P"][at[i - 1]],
                      "x__V02_total_precip_mm_lag2": d["P"][at[i - 2]],
                      "x__V30_soil_moisture_pct": d["SM"][at[i]], "x__V30_soil_moisture_pct_lag1": d["SM"][at[i - 1]],
                      "x__V30_soil_moisture_pct_lag2": d["SM"][at[i - 2]]})
    return (pd.DataFrame(rows), np.array(y), np.array(z), pd.DataFrame(H), pd.DataFrame(E))


def ndvi_ctx(lead=0):
    series = make_ndvi()
    tune = ndvi_set(series, step(2002, 1), step(2016, 12), lead)
    # u3 has only 30 fit rows (fallback); u4 is not scored
    k, y, z, h, e = tune
    keep = ~((k["unit"] == "u3") & (k["time"] > step(2002, 1) + 29)).to_numpy()
    tune = (k[keep].reset_index(drop=True), y[keep], z[keep], h[keep].reset_index(drop=True),
            e[keep].reset_index(drop=True))
    inner = ndvi_set(series, step(2017, 1), step(2019, 12), lead)
    units = pd.DataFrame({"unit": ["u0", "u1", "u2", "u3", "u4"], "group": ["g_u0", "g_u1", "g_u2", "g_u3", "g_u4"],
                          "is_scored": [True, True, True, True, False]})
    return NdCtx({"tune": tune, "inner": inner}, units, offset=1, lead=lead), series


def test_ndvi_h1_recovers_ardl_and_fallbacks():
    ctx, series = ndvi_ctx()
    params = BD.fit(ctx, H1_RIVAL, 0, "tune")
    assert ctx.label_calls == ["tune"]
    assert params["units"]["u3"]["fallback"] and params["units"]["u3"]["n"] == 30
    assert "u4" not in params["units"]
    assert params["counts"]["units_fallback_normal"] == 1
    lag1 = [params["units"][u]["coef"][0] for u in ("u0", "u1", "u2")]
    assert all(0.35 < c < 0.7 for c in lag1), lag1                     # the NDVI lag-1 anomaly (y at t-2); shrunk
    ps = BD.fit(ctx, dict(H1_RIVAL, options=dict(H1_RIVAL["options"], standardize=True)), 0, "tune")
    lag1s = [ps["units"][u]["coef"][0] / ps["units"][u]["sd"][0] for u in ("u0", "u1", "u2")]
    assert all(0.4 < c < 0.7 for c in lag1s) and np.mean(lag1s) > np.mean(lag1), (lag1, lag1s)
    calls = list(ctx.label_calls)
    pred = BD.predict(ctx, H1_RIVAL, 0, params, "inner")
    assert ctx.label_calls == calls == ["tune", "tune"]                 # predict never asks for labels
    assert list(pred.columns) == KEYS + ["pre", "info_end", "target_obs_end"]
    k, y, z, h, e = ctx.sets["inner"]
    pd.testing.assert_frame_equal(pred[KEYS], k[KEYS])                  # one row per key, set order
    assert set(pred.loc[pred["pre"].notna(), "unit"]) == {"u0", "u1", "u2", "u3"}    # scored units only
    assert pred.loc[pred["unit"] == "u4", "pre"].isna().all()
    m = pred.merge(k.assign(y=y, z=z), on=KEYS)
    m = m[m["pre"].notna()]
    sc = m[m["unit"] != "u3"]
    oracle = []                                                         # the generator's own conditional mean
    for _, r in sc.iterrows():
        d = series[r["unit"]]
        i = int(np.flatnonzero(d["S"] == r["time"])[0])
        oracle.append(d["nrm"][i] + 0.6 * d["a"][i - 2] + 0.001 * (d["P"][i] - d["pcl"][i]))
    mae_h1 = np.abs(sc["pre"] - sc["y"]).mean()
    mae_nrm = np.abs(sc["z"] - sc["y"]).mean()
    mae_or = np.abs(np.array(oracle) - sc["y"].to_numpy()).mean()
    assert mae_h1 < 0.85 * mae_nrm and mae_h1 < 1.10 * mae_or, (mae_h1, mae_nrm, mae_or)
    fb = m[m["unit"] == "u3"]
    np.testing.assert_array_equal(fb["pre"].to_numpy(), fb["z"].to_numpy())      # fallback = the normal
    np.testing.assert_array_equal(pred["info_end"].to_numpy(), pred["issue"].to_numpy())
    np.testing.assert_array_equal(pred["target_obs_end"].to_numpy(), pred["time"].to_numpy() - 2)   # t-1-offset


def test_ndvi_h1_labels_only_from_fit_sets_and_deterministic():
    ctx, _ = ndvi_ctx()
    with pytest.raises(BD.BardlRefusal):
        BD.fit(ctx, H1_RIVAL, 0, "inner")
    with pytest.raises(RuntimeError):
        ctx.fit_labels("inner")
    p1 = BD.fit(ctx, H1_RIVAL, 0, "tune")
    p2 = BD.fit(ctx, H1_RIVAL, 0, "tune")
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    p3 = json.loads(json.dumps(p1))
    a = BD.predict(ctx, H1_RIVAL, 0, p1, "inner")
    b = BD.predict(ctx, H1_RIVAL, 0, p3, "inner")
    pd.testing.assert_frame_equal(a, b)
    with pytest.raises(BD.BardlRefusal):
        BD.predict(ctx, H1_RIVAL, 0, p1, "test")                      # tune params score inner only


def test_ndvi_h1_missing_lag_and_normal_rules():
    ctx, _ = ndvi_ctx()
    params = BD.fit(ctx, H1_RIVAL, 0, "tune")
    k, y, z, h, e = ctx.sets["inner"]
    h2 = h.copy()
    h2.loc[(k["unit"] == "u0").to_numpy(), "x__hist_last_2"] = np.nan
    ctx.sets["inner"] = (k, y, z, h2, e)
    pred = BD.predict(ctx, H1_RIVAL, 0, params, "inner")
    assert np.isfinite(pred.loc[pred["unit"] != "u4", "pre"]).all()
    assert any("NDVI lag values missing -> 0" in l and " 0 NDVI" not in l for l in ctx.lines)
    # the hand rule for a missing lag: anomaly 0
    X, ok, counts = BD.design(k, z, h2, e, params["climate_means"], BD._options(H1_RIVAL), 0, 12, 1)
    assert counts["ndvi_lag_values_missing_set_to_0"] == int((k["unit"] == "u0").sum())
    assert (X[(k["unit"] == "u0").to_numpy(), 1] == 0.0).all()
    # a normal that takes two values for one unit x season key refuses
    z2 = z.copy()
    z2[0] += 0.1
    ctx.sets["inner"] = (k, y, z2, h, e)
    with pytest.raises(BD.BardlRefusal):
        BD.predict(ctx, H1_RIVAL, 0, params, "inner")


def test_ndvi_t2_steps_and_lead6():
    t = np.array([step(2020, 7)])
    assert BD.t2_step(t, 0, 1)[0] == t[0] - 2
    assert BD.t2_step(t, 6, 1)[0] == t[0] - 7
    assert BD.t2_step(t, 12, 0)[0] == t[0] - 12
    ctx, _ = ndvi_ctx(lead=6)
    params = BD.fit(ctx, H1_RIVAL, 6, "tune")
    pred = BD.predict(ctx, H1_RIVAL, 6, params, "inner")
    np.testing.assert_array_equal(pred["target_obs_end"].to_numpy(), pred["time"].to_numpy() - 7)
    np.testing.assert_array_equal(pred["info_end"].to_numpy(), pred["time"].to_numpy() - 6)


# =============================================================================================== Kraft (optional)
KRAFT_RIVAL = {"id": "kraft_lstm", "kind": "M", "products": ["kstore"],
               "t1_kind_columns": ["d1", "d2"],
               "options": {"store_product": "kstore", "drivers": ["d1", "d2"], "statics": ["s1"], "seq": 12,
                           "hidden": 8, "head": 8, "epochs": 2, "batch": 4, "lr": 0.01, "seed": 0, "threads": 2}}


class KCtx(object):
    def __init__(self, folder, sets, units):
        self.run = FakeRun(offset=1, r8={"d1": {"steps": 0}, "d2": {"steps": 0}})
        self.folder, self.sets, self._units, self.lines = folder, sets, units, []

    def units(self):
        return self._units

    def product_files(self, pid):
        return ["r1.parquet"]

    def open_product(self, pid, name):
        return self.folder / name

    def features(self, name):
        k, y = self.sets[name]
        return SS(k, {"identity": np.zeros(len(k))}, pd.DataFrame(index=k.index), pd.DataFrame(index=k.index))

    def fit_labels(self, name):
        if name not in ("tune", "refit", "guardfit"):
            raise RuntimeError("refused")
        k, y = self.sets[name]
        return k, y, {"identity": np.zeros(len(k))}

    def log(self, m):
        self.lines.append(m)


@pytest.mark.slow_ok
def test_kraft_cpu_toy_is_deterministic(tmp_path):
    pytest.importorskip("torch")
    from adapters import ndvi_kraft as KR

    rng = np.random.default_rng(0)
    steps = np.arange(step(2010, 1), step(2010, 1) + 20)
    rows = []
    for u in ("k1", "k2"):
        for s in steps:
            rows.append({"unit": u, "step": int(s), "d1": float(rng.normal()), "d2": float(rng.normal()),
                         "s1": 1.0 if u == "k1" else 2.0})
    pd.DataFrame(rows).to_parquet(str(tmp_path / "r1.parquet"), index=False)
    fit_keys = pd.DataFrame([{"unit": u, "group": "g", "time": int(s), "issue": int(s), "lead": 0}
                             for u in ("k1", "k2") for s in steps[11:17]])
    sc_keys = pd.DataFrame([{"unit": u, "group": "g", "time": int(s), "issue": int(s), "lead": 0}
                            for u in ("k1", "k2") for s in np.r_[steps[5], steps[17:20]]])
    y = np.linspace(0.1, 0.6, len(fit_keys)).astype(np.float32)
    units = pd.DataFrame({"unit": ["k1", "k2"], "group": ["g", "g"], "is_scored": [True, True]})
    ctx = KCtx(tmp_path, {"tune": (fit_keys, y), "inner": (sc_keys, None)}, units)
    p1 = KR.fit(ctx, KRAFT_RIVAL, 0, "tune")
    p2 = KR.fit(ctx, KRAFT_RIVAL, 0, "tune")
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    a = KR.predict(ctx, KRAFT_RIVAL, 0, p1, "inner")
    b = KR.predict(ctx, KRAFT_RIVAL, 0, json.loads(json.dumps(p1)), "inner")
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 8 and int(a["pre"].notna().sum()) == 6   # the step-5 rows have no complete 12-month window
    assert a.loc[a["time"] == steps[5], "pre"].isna().all() and a["target_obs_end"].isna().all()
    np.testing.assert_array_equal(a["info_end"].to_numpy(), a["issue"].to_numpy())   # S = 0 on the toy R8
    with pytest.raises(KR.KraftRefusal):
        KR.fit(ctx, KRAFT_RIVAL, 0, "inner")


def test_kraft_prep_region_frame_and_forbidden(tmp_path):
    from adapters import ndvi_kraft_prep as KP

    for y in (2010, 2011):
        pd.DataFrame({"cell_id": ["c1", "c1", "c2"], "year": [y, y, y], "month": [1, 2, 1],
                      "d1": [1.0, 2.0, 3.0], "s1": [5.0, 5.0, 6.0], "V11_mean_ndvi": [0.5, 0.5, 0.5]}).to_parquet(
            str(tmp_path / ("reg_monthly_%d.parquet" % y)), index=False)
    f = KP.region_frame(tmp_path, "reg", ["c1"], (2010, 2012), ["d1"], ["s1"])
    assert list(f.columns) == ["unit", "step", "d1", "s1"]
    assert f["step"].tolist() == [step(2010, 1), step(2010, 2), step(2011, 1), step(2011, 2)]
    assert "V11_mean_ndvi" not in f.columns
    with pytest.raises(KP.KraftPrepRefusal):
        KP.prep_options({"id": "k", "options": {"drivers": ["d1", "V11_mean_ndvi"], "statics": ["s1"],
                                                "panel_product": "p", "unit_centres": {}, "years": [2010, 2011],
                                                "forbidden_columns": ["V11_mean_ndvi"]}})


class _PrepCtx(object):
    """The calls run_prep uses (units, open_product, product_files, work_dir, write_bytes, log) on toy folders."""

    def __init__(self, tmp, panel, static, units):
        self.tmp, self.panel, self.static, self._units, self.lines = tmp, panel, static, units, []

    def units(self):
        return self._units

    def product_files(self, pid):
        return sorted(p.name for p in self.panel.glob("*.parquet"))

    def open_product(self, pid, name):
        return (self.panel / name) if pid == "panel" else self.static

    def work_dir(self):
        d = self.tmp / "_work" / "kraft_lstm"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_bytes(self, path, data):
        from pathlib import Path as _P
        p = _P(path)
        p.resolve().relative_to(self.work_dir().resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def log(self, m):
        self.lines.append(m)


def test_kraft_prep_resumes_by_region_and_refuses_on_any_mismatch(tmp_path):
    """Review B issue 12: a killed or repeated Kraft prep resumes region by region (file + progress record with its
    sha and inputs); a file without its record, a changed file or other inputs refuse (never overwritten)."""
    import shutil
    from adapters import ndvi_kraft_prep as KP

    panel = tmp_path / "panel"
    panel.mkdir()
    for reg, cells in (("ra", ["c1", "c2"]), ("rb", ["c3"])):
        for y in (2010, 2011):
            pd.DataFrame({"cell_id": cells, "year": y, "month": 1, "d1": 1.0, "s1": 2.0}).to_parquet(
                str(panel / ("%s_monthly_%d.parquet" % (reg, y))), index=False)
    static = tmp_path / "static.parquet"
    pd.DataFrame({"cell_id": ["c1", "c2", "c3"], "region": ["ra", "ra", "rb"]}).to_parquet(str(static), index=False)
    units = pd.DataFrame({"unit": ["c1", "c2", "c3"]})
    rival = {"id": "kraft_lstm", "options": {"drivers": ["d1"], "statics": ["s1"], "panel_product": "panel",
                                             "unit_centres": {"product": "st", "file": "static.parquet",
                                                              "id": "cell_id", "region": "region"},
                                             "years": [2010, 2011], "forbidden_columns": ["V11_mean_ndvi"]}}
    ctx = _PrepCtx(tmp_path, panel, static, units)
    first = KP.run_prep(ctx, rival)
    assert first["resumed_regions"] == 0 and sorted(first["regions"]) == ["ra", "rb"]
    store = ctx.work_dir() / "store"
    shas = {p.name: p.read_bytes() for p in store.glob("*.parquet")}
    again = KP.run_prep(ctx, rival)
    assert again["resumed_regions"] == 2
    assert {p.name: p.read_bytes() for p in store.glob("*.parquet")} == shas
    prog = ctx.work_dir() / ("store" + KP.PROGRESS_SUFFIX)
    moved = tmp_path / "_moved_by_test"
    moved.mkdir()
    # a pass killed after writing rb's file but before its record: refuses (move the file aside, rerun)
    shutil.move(str(prog / "rb.json"), str(moved / "rb.json"))
    with pytest.raises(KP.KraftPrepRefusal, match="do not both exist"):
        KP.run_prep(ctx, rival)
    shutil.move(str(store / "rb.parquet"), str(moved / "rb.parquet"))
    third = KP.run_prep(ctx, rival)
    assert third["resumed_regions"] == 1 and (store / "rb.parquet").read_bytes() == shas["rb.parquet"]
    # other inputs (another driver list) refuse
    other = {"id": "kraft_lstm", "options": dict(rival["options"], drivers=["d1"], statics=[])}
    with pytest.raises(KP.KraftPrepRefusal, match="other inputs"):
        KP.run_prep(ctx, other)


# =============================================================================================== against builder A's checks
def _tool():
    pytest.importorskip("rivals_human.methods")
    from rivals_human import index as IX
    from rivals_human import methods as MT
    return IX, MT


def test_tool_timing_accepts_pm25_tiers(pm_base):
    """builder A's Timing / check_tier_timing (rivals_human/index.py:42-126): the t-1 row passes as P, the same-month
    row passes as A (it breaks T1 and T2) and refuses as P; the t-1 row refuses as A (registry error)."""
    IX, _ = _tool()
    keys = pm_keys()
    ctx = PmCtx(pm_base, keys)
    ctx.run.plan = {}
    for off, ok_tier, bad_tier in ((-1, "P", "A"), (0, "A", "P")):
        rival = pm_rival("merra2", "monthly_files", off)
        rival["t1_kind_columns"] = ["burn_frac"]
        f = PM.build(ctx, rival, 0, "all")
        tm = IX.Timing(ctx.run, rival, 0)
        cov = np.isfinite(f["x__pm25"].to_numpy())
        IX.check_tier_timing(ok_tier, tm, f[KEYS], f["info_end"].to_numpy(), f["target_obs_end"].to_numpy(), cov, "t")
        with pytest.raises(Exception):
            IX.check_tier_timing(bad_tier, tm, f[KEYS], f["info_end"].to_numpy(), f["target_obs_end"].to_numpy(), cov,
                                 "t")


def test_tool_runner_checks_accept_h1():
    """builder A's methods.run_fit / run_predict (JSON round trip, one row per key, T1/T2 of tier P at lead 0 and
    tier X at lead 6) accept the H1 runner."""
    IX, MT = _tool()
    r8 = {c: {"steps": 0} for c in ("V02_total_precip_mm", "V02_total_precip_mm_lag1", "V02_total_precip_mm_lag2",
                                     "V30_soil_moisture_pct", "V30_soil_moisture_pct_lag1",
                                     "V30_soil_moisture_pct_lag2")}
    rival = dict(H1_RIVAL, runner="adapters.ndvi_bardl", t1_kind_columns=sorted(r8))
    runner = MT.load_runner(rival)
    for lead, tier in ((0, "P"), (6, "X")):
        ctx, _ = ndvi_ctx(lead=lead)
        ctx.run.derived["R8"] = {"value": r8}
        ctx.run.plan = {}
        params = MT.run_fit(runner, ctx, rival, lead, "tune")
        frame, rec = MT.run_predict(runner, ctx, rival, lead, params, "inner", ctx.sets["inner"][0], tier)
        assert rec["t1_breaks"] == 0 and rec["t2_breaks"] == 0
        assert rec["predicted"] == int((ctx.sets["inner"][0]["unit"] != "u4").sum())
