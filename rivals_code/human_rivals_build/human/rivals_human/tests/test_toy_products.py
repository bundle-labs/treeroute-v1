"""The synthetic products the tool tests read are what they claim to be (SPEC_HUMAN.txt 7 "Fixtures")."""

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import toy_products as TP


def test_sst_npz_is_stored_in_the_real_layout(tmp_path):
    sites = {int(TP.site_key(-17.5, 146.25)): (np.arange(100, 400), np.linspace(26, 30, 300)),
             int(TP.site_key(10.0, -80.0)): (np.arange(50, 60)[::-1], np.arange(10, dtype=float))}
    p = TP.write_sst_npz(tmp_path / "sst_compact_toy.npz", sites)
    off = TP.npz_member_offsets(p)
    assert set(off) == {"uk.npy", "start.npy", "end.npy", "day.npy", "sst.npy", "manifest.npy"}
    assert all(ct == zipfile.ZIP_STORED for ct, _ in off.values())
    with np.load(str(p)) as z:
        assert z["uk"].dtype == np.int64 and (np.diff(z["uk"]) > 0).all()
        assert z["day"].dtype == np.int32 and z["sst"].dtype == np.float32
        k = int(np.searchsorted(z["uk"], int(TP.site_key(10.0, -80.0))))
        d = z["day"][z["start"][k]:z["end"][k]]
        assert (np.diff(d) > 0).all()                            # days sorted per site
        assert z["manifest"].tolist() == [2, 310]


def test_site_key_matches_coral_safe():
    assert int(TP.site_key(0.0, 0.0)) == 900000 * (3600001) + 1800000


def test_mmm_netcdf_round_trip(tmp_path):
    import netCDF4
    lat = np.array([0.075, 0.025, -0.025, -0.075])               # north -> south, 0.05 degrees
    lon = np.array([10.025, 10.075, 10.125])
    mmm = np.array([[28.11, 28.12, 28.13], [28.21, 28.22, 28.23], [28.31, 28.32, 28.33], [28.41, 28.42, 28.43]])
    valid = np.ones_like(mmm, dtype=bool)
    valid[1, 1] = False
    p = TP.write_mmm_nc(tmp_path / "clim.nc", lat, lon, mmm, valid)
    with netCDF4.Dataset(str(p)) as ds:
        ds.set_auto_maskandscale(False)
        raw = ds.variables["sst_clim_mmm"][0]
        assert raw[1, 1] == -32768 and raw[0, 0] == 2811
        assert ds.variables["mask_for_sst_clim_mmm"][0][1, 1] == 1


def test_outlook_netcdf_has_week20_window_attributes(tmp_path):
    import netCDF4
    lat = np.array([0.25, -0.25])
    lon = np.array([0.25, 0.75])
    p = TP.write_outlook_nc(tmp_path / "o.nc", "20150104", {20: ("20150518T000000Z", "20150525T000000Z")},
                            {20: np.array([[0, 1], [2, 4]])}, land=np.array([[False, True], [False, False]]),
                            lat=lat, lon=lon)
    with netCDF4.Dataset(str(p)) as ds:
        v = ds.variables["CRW_BAA_Week_20"]
        assert v.start_time == "20150518T000000Z" and v.stop_time == "20150525T000000Z"
        assert ds.variables["surface_flag"][0, 1] == 1


def test_hansen_tiles_and_gadm_zip(tmp_path):
    import pyogrio
    import rasterio
    from shapely.geometry import box
    ly = np.zeros((64, 64), np.uint8)
    ly[10, 10] = 12
    paths = TP.write_hansen_toy(tmp_path / "hansen", "10N_020E", ly, np.full((64, 64), 80, np.uint8),
                                np.ones((64, 64), np.uint8), west=20.0, north=10.0, pixel=1.0 / 64)
    with rasterio.open(str(paths["lossyear"])) as src:
        a = src.read(1)
        assert a[10, 10] == 12 and src.transform.a == pytest.approx(1.0 / 64)
    zp = TP.write_gadm_toy(tmp_path / "gadm", [("TOY.1.1_1", box(20.0, 9.0, 20.5, 10.0)),
                                               ("TOY.1.2_1", box(20.5, 9.0, 21.0, 10.0))])
    layers = pyogrio.list_layers("/vsizip/%s/gadm36_TOY.gpkg" % zp.as_posix())
    assert "gadm36_TOY_2" in [l[0] for l in layers]
    with zipfile.ZipFile(str(zp)) as z:
        assert sorted(z.namelist()) == ["gadm36_TOY.gpkg", "license.txt"]


def test_product_manifest_lists_every_file_with_its_sha(tmp_path):
    d = tmp_path / "prod" / "v1"
    d.mkdir(parents=True)
    (d / "a.bin").write_bytes(b"abc")
    mp = TP.write_product_manifest(d, "toy", "v1")
    m = json.loads(mp.read_text(encoding="utf-8"))
    assert m["complete"] is True
    assert m["files"]["a.bin"]["sha256"] == HK.sha256_file(d / "a.bin")


def test_grid_product_holds_the_x1_driver_and_the_coverage_hole(grid_toy, grid_export, tmp_path):
    fit0 = grid_toy.cuts(0)["fit_cut"]
    prod = TP.grid_products(tmp_path / "products", grid_export, fit0)
    ui, si, val = TP.read_unit_step_nc(prod["file"], "val")
    f = TP.export_frame(grid_export[0], ["unit", "group", "time", "x__x1"])
    assert np.nanmin(val) == pytest.approx(0.1)               # shifted onto the legal range
    shift = 0.1 - float(np.nanmin(f["x__x1"].to_numpy(np.float64)))
    r = f.iloc[len(f) // 3]
    if str(r["unit"]) not in prod["hole_units"] or int(r["time"]) < fit0:
        assert val[ui[str(r["unit"])], si[int(r["time"])]] == pytest.approx(float(r["x__x1"]) + shift)
    grp_c = sorted(set(f.loc[f["group"] == "grp_c", "unit"].astype(str)))
    assert prod["hole_units"] == grp_c[1:]
    later = [s for s in si if s >= fit0]
    for u in prod["hole_units"]:
        assert np.isnan(val[ui[u], [si[s] for s in later]]).all()
