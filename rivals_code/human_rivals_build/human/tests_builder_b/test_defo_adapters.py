"""Toy tests of adapters/defo_prep.py and adapters/defo_vt0007.py (SPEC_HUMAN 7 T-H17). Toy rasters only.

Toy world: two 10-degree granules (10N_000E, 10N_010E) of 64 x 64 pixels (pixel 10/64 deg), cells of 4 x 4 pixels.
Every reference here is computed the slow, obvious way (per pixel, brute-force distances) and compared."""
import datetime as dt
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from adapters import defo_prep as DP
from adapters import defo_vt0007 as VT

NPX = 64
PX = 10.0 / NPX
TILES = [(10, 0), (10, 10)]
PREFIX = "Hansen_TOY-v1"
BINS = {"d_lo": 1000.0, "d_max": 400000.0, "n_bins": 64}
REGION = "toyland"


# ---------------------------------------------------------------------------------------------------- toy products
def toy_layers(seed=1):
    """Global-mosaic arrays (64 rows x 128 cols) of treecover2000, datamask, lossyear."""
    rng = np.random.default_rng(seed)
    tc = rng.integers(0, 101, size=(NPX, 2 * NPX)).astype(np.uint8)
    tc[(tc > 20) & (tc < 60)] = 85                      # plenty of forest
    dm = np.ones((NPX, 2 * NPX), np.uint8)
    dm[40:46, 70:90] = 2                                # a lake (water: never a source)
    dm[:, :3] = 0                                       # no-data strip
    ly = np.zeros((NPX, 2 * NPX), np.uint8)
    hit = rng.random((NPX, 2 * NPX)) < 0.10
    ly[hit] = rng.integers(1, 23, size=int(hit.sum()))  # loss years 2001..2022
    return tc, dm, ly


def write_tiles(folder, tc, dm, ly, drop_loss_tile=None):
    import rasterio
    from rasterio.transform import from_origin
    folder.mkdir(parents=True, exist_ok=True)
    for k, (tlat, tlon) in enumerate(TILES):
        tn = DP.tile_name(tlat, tlon)
        sl = (slice(0, NPX), slice(k * NPX, (k + 1) * NPX))
        for layer, arr in (("treecover2000", tc), ("datamask", dm), ("lossyear", ly)):
            if layer == "lossyear" and drop_loss_tile == tn:
                continue
            p = folder / ("%s_%s_%s.tif" % (PREFIX, layer, tn))
            with rasterio.open(str(p), "w", driver="GTiff", width=NPX, height=NPX, count=1, dtype="uint8",
                               crs="EPSG:4326", transform=from_origin(tlon, tlat, PX, PX)) as d:
                d.write(arr[sl], 1)


def toy_cells():
    """Cells of 4 x 4 pixels: centres at pixel (4i + 10, 4j + 10) + half a pixel edge, a few holes."""
    rows = []
    for j in range(10):
        for i in range(24):
            if (i, j) in ((3, 2), (10, 5), (20, 0)):
                continue
            lon = (4 * i + 10) * PX
            lat = 10.0 - (4 * j + 10) * PX
            rows.append({"cell_id": "%s_%d_%d" % (REGION, i, j), "region": REGION, "lat": lat, "lon": lon})
    return pd.DataFrame(rows)


def naive_assign(cells):
    """Pixel (row, col) of the mosaic -> cell ordinal, by nearest centre per axis (no pixel centre is on a midpoint).
    The region window per granule is defo_ingest.py:160-172 (floor / ceil of the half-cell padded box)."""
    g = DP.region_grid(cells["cell_id"], cells["lon"], cells["lat"])
    ulon, ulat = np.sort(cells["lon"].unique()), np.sort(cells["lat"].unique())
    pos = {(round(a, 9), round(b, 9)): k for k, (a, b) in enumerate(zip(cells["lon"], cells["lat"]))}
    out = np.full((NPX, 2 * NPX), -1, np.int64)
    for k, (tlat, tlon) in enumerate(TILES):
        c0 = max(0, min(int(np.floor((g["lon0"] - tlon) / PX)), NPX))
        c1 = max(0, min(int(np.ceil((g["lon1"] - tlon) / PX)), NPX))
        r0 = max(0, min(int(np.floor((tlat - g["lat1"]) / PX)), NPX))
        r1 = max(0, min(int(np.ceil((tlat - g["lat0"]) / PX)), NPX))
        for r in range(r0, r1):
            plat = tlat - (r + 0.5) * PX
            for c in range(c0, c1):
                plon = tlon + (c + 0.5) * PX
                a = ulon[np.argmin(np.abs(ulon - plon))]
                b = ulat[np.argmin(np.abs(ulat - plat))]
                out[r, k * NPX + c] = pos.get((round(a, 9), round(b, 9)), -1)
    return out


def row_window(cells):
    g = DP.region_grid(cells["cell_id"], cells["lon"], cells["lat"])
    return int(np.floor((10.0 - g["lat1"]) / PX)), int(np.ceil((10.0 - g["lat0"]) / PX))


def naive_counts(cells, tc, dm, ly, ymax):
    asg = naive_assign(cells)
    n = len(cells)
    f2000 = (dm == 1) & (tc >= 30)
    forest = np.zeros(n, np.int64)
    loss = np.zeros((n, ymax - 2000), np.int64)
    for (r, c), k in np.ndenumerate(asg):
        if k < 0 or not f2000[r, c]:
            continue
        forest[k] += 1
        if 1 <= ly[r, c] <= ymax - 2000:
            loss[k, ly[r, c] - 1] += 1
    return asg, forest, loss


def write_target(folder, cells, forest, loss):
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, cid in enumerate(cells["cell_id"]):
        for y in range(2001, 2023):
            rows.append({"cell_id": cid, "year": y, "loss_px": int(loss[k, y - 2001]) if y - 2001 < loss.shape[1]
                         else 0, "forest2000_px": int(forest[k])})
    pd.DataFrame(rows).to_parquet(folder / ("%s.parquet" % REGION), index=False)


def write_gadm(folder, level2=True, iso="AAA"):
    """A zipped GeoPackage: level 0 (one box) and level 2 (two boxes split at lon 7.0), or level 1 only."""
    import geopandas as gpd
    import shapely
    folder.mkdir(parents=True, exist_ok=True)
    gp = folder / ("gadm36_%s.gpkg" % iso)
    g0 = gpd.GeoDataFrame({"GID_0": [iso]}, geometry=[shapely.box(0.0, 0.0, 20.0, 10.0)], crs="EPSG:4326")
    g0.to_file(str(gp), layer="gadm36_%s_0" % iso, driver="GPKG", engine="pyogrio")
    lv = 2 if level2 else 1
    # west unit ends at lon 7.0; east unit starts at lon 7.2 (a 0.2 deg gap: cells there go 'nearest');
    # nothing south of lat 4.5 in the east (cells there go 'none' unless within half a cell)
    g = gpd.GeoDataFrame({"GID_%d" % lv: ["%s.1_1" % iso, "%s.2_1" % iso]},
                         geometry=[shapely.box(0.0, 0.0, 7.0, 10.0), shapely.box(7.2, 4.5, 20.0, 10.0)],
                         crs="EPSG:4326")
    g.to_file(str(gp), layer="gadm36_%s_%d" % (iso, lv), driver="GPKG", engine="pyogrio", mode="a")
    zp = folder / ("gadm36_%s_gpkg.zip" % iso)
    with zipfile.ZipFile(str(zp), "w") as z:
        z.write(str(gp), gp.name)
    gp.unlink()
    return zp


def make_defo(tmp_path, ymax=2019, tamper_target=False, drop_loss_tile=None):
    root = Path(tmp_path)
    tc, dm, ly = toy_layers()
    write_tiles(root / "hansen", tc, dm, ly, drop_loss_tile)
    cells = toy_cells()
    st = root / "static"
    st.mkdir(parents=True, exist_ok=True)
    asg, forest, loss = naive_counts(cells, tc, dm, ly, 2022)
    cells = cells.assign(forest2000_px=forest.astype(float))
    cells.to_parquet(st / "part-0.parquet", index=False)
    lt = loss.copy()
    if tamper_target:
        k = int(np.argmax(lt[:, 5]))
        lt[k, 5] += 1
    write_target(root / "target", cells, forest, lt)
    write_gadm(root / "gadm")
    products = {"hansen_gfc_v1_13": root / "hansen", "defo_static": st, "defo_target": root / "target",
                "gadm36_defo42": root / "gadm"}
    return products, cells, (tc, dm, ly), asg


def defo_rivals():
    import yaml
    reg = yaml.safe_load((Path(DP.__file__).resolve().parents[1] / "registry" / "defo.yaml").read_text())
    out = {}
    for r in reg["rivals"]:
        r = json.loads(json.dumps(r))
        r["options"].update({"pixel_deg": PX, "d_lo_m": BINS["d_lo"], "d_max_m": BINS["d_max"],
                             "n_bins": BINS["n_bins"], "block_px": 40} if r["id"] == "vt0007_shipped" else
                            {"d_lo_m": BINS["d_lo"], "d_max_m": BINS["d_max"], "n_bins": BINS["n_bins"]})
        out[r["id"]] = r
    return out


def keys_of(cells, years, lead):
    rows = [{"unit": c, "group": REGION, "time": t, "issue": t - lead, "lead": lead}
            for c in cells["cell_id"] for t in years]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------- unit pieces
def test_fine_bins_edges_and_overflow():
    b = DP.FineBins(1.0, 1000.0, 3)
    assert np.allclose(b.edges, [1, 10, 100, 1000])
    assert b.bin_of(np.array([0.5, 1.0, 9.99, 10.0, 999.0, 1000.0, 1000.1, np.inf])).tolist() == \
        [0, 0, 0, 1, 2, 2, 3, 3]


def test_lossyear_guard():
    ly = np.array([0, 5, 19, 20, 25], np.uint8)
    assert DP.lossyear_guard(ly, 2019).tolist() == [0, 5, 19, 0, 0]


def test_stage_plan_never_reads_past_t_minus_1():
    p = DP.stage_plan([2011, 2019], 10, 2019)
    assert p[2000] == list(range(2001, 2011)) and p[2008] == list(range(2009, 2019)) and p[2010] == []
    assert p[2018] == []
    with pytest.raises(DP.DefoPrepRefusal):
        DP.stage_plan([2021], 10, 2019)


def test_class_edges_and_scale_with_cap():
    bins = DP.FineBins(1.0, 1000.0, 30)
    cls = VT.class_of_bins(bins, nrt=float(bins.upper()[20]), d0=30.0)
    assert cls[0] == 1 and cls[20] == 29 and (cls[21:] == 30).all() and (np.diff(cls) >= 0).all()
    P = np.array([10.0, 10.0, 100.0])
    f = np.array([0.5, 0.05, 0.01])
    s, capped = VT.solve_scale(P, f, 15.0)
    tot = (P * np.minimum(1.0, s * f)).sum()
    assert not capped and tot == pytest.approx(15.0, rel=1e-12) and s == pytest.approx(10.0 / 3.0, rel=1e-12)
    assert s * f[0] >= 1.0 - 1e-12                        # the first class is capped at 1 per pixel
    s, capped = VT.solve_scale(P, f, 500.0)
    assert capped and math.isinf(s)


def test_assign_divisions_overlap_nearest_none_and_level1(tmp_path):
    cells = toy_cells()
    g = DP.region_grid(cells["cell_id"], cells["lon"], cells["lat"])
    zp = write_gadm(tmp_path / "g2")
    d, rep = DP.assign_divisions(cells["cell_id"], cells["lon"], cells["lat"], g["hx"], g["hy"], [zp])
    lon = cells["lon"].values
    lat = cells["lat"].values
    west = lon + g["hx"] <= 7.0
    assert (d.loc[west, "division"] == "AAA.1_1").all() and (d.loc[west, "step"] == "overlap").all()
    half = max(g["hx"], g["hy"])
    east = lon - g["hx"] >= 7.2
    near = east & (lat + g["hy"] < 4.5) & (lat + g["hy"] >= 4.5 - half)
    assert near.any() and (d.loc[near, "step"] == "nearest").all() and (d.loc[near, "division"] == "AAA.2_1").all()
    south_east = east & (lat + g["hy"] < 4.5 - half)
    assert south_east.any() and (d.loc[south_east, "division"] == DP.NONE_DIVISION).all()
    assert rep["overlap"] + rep["nearest"] + rep["none"] == len(cells)
    zp1 = write_gadm(tmp_path / "g1", level2=False, iso="BBB")
    d1, rep1 = DP.assign_divisions(cells["cell_id"], cells["lon"], cells["lat"], g["hx"], g["hy"], [zp1])
    assert rep1["level_by_country"] == {"BBB": 1} and (d1.loc[west, "level"] == 1).all()


# ---------------------------------------------------------------------------------------------------- map pass
def brute_distance(src, rows, cols, dy, dx):
    """Distance (m) from each (row, col) to the nearest True of src (mosaic grid), brute force."""
    sr, sc = np.nonzero(src)
    out = np.empty(len(rows))
    for a in range(0, len(rows), 256):
        r = rows[a:a + 256, None]
        c = cols[a:a + 256, None]
        d2 = ((r - sr[None, :]) * dy) ** 2 + ((c - sc[None, :]) * dx) ** 2
        out[a:a + 256] = np.sqrt(d2.min(axis=1)) if len(sr) else np.inf
    return out


def run_pass(products, cells, T, years, ymax, block=40):
    _, names = DP.index_tiles(p.name for p in Path(products["hansen_gfc_v1_13"]).iterdir())
    paths = {lay: {tn: str(Path(products["hansen_gfc_v1_13"]) / n) for tn, n in names[lay].items()}
             for lay in DP.LAYERS}
    task = {"region": REGION, "cell_id": cells["cell_id"].values, "lon": cells["lon"].values,
            "lat": cells["lat"].values, "paths": paths, "px": PX, "T": T, "loss_years": years, "ymax": ymax,
            "bins": BINS, "block": block, "tc_thresh": 30}
    return DP.map_pass(task)


def test_map_pass_parity_distances_and_loss_counts(tmp_path):
    products, cells, (tc, dm, ly), asg = make_defo(tmp_path)
    T, ymax = 2008, 2019
    years = list(range(2009, 2019))
    res = run_pass(products, cells, T, years, ymax, block=64)       # one block per granule: one dx per block row
    _, forest, loss = naive_counts(cells, tc, dm, ly, ymax)
    assert np.array_equal(res["parity_forest"], forest)
    assert np.array_equal(res["parity_loss"], loss)
    # reference forest(T) and distances, brute force over the whole two-granule mosaic
    lyg = DP.lossyear_guard(ly, ymax)
    f2000 = (dm == 1) & (tc >= 30)
    fT = f2000 & ~((lyg >= 1) & (lyg <= T - 2000))
    src = (dm == 1) & ~fT
    r0, r1 = row_window(cells)                                      # one block holds the whole region window
    lat_c = 10.0 - ((r0 + r1) / 2.0) * PX
    dy = PX * DP.M_PER_DEG
    dx = dy * math.cos(math.radians(lat_c))
    sel = (asg >= 0) & fT
    rr, cc = np.nonzero(sel)
    dist = brute_distance(src, rr, cc, dy, dx)
    bins = DP.FineBins(**BINS)
    b = bins.bin_of(dist)
    NB1 = bins.n + 1
    want = pd.Series(1, index=asg[rr, cc] * NB1 + b).groupby(level=0).sum()
    got = pd.Series(res["forest_n"], index=res["forest_cell"].astype(np.int64) * NB1 + res["forest_bin"])
    assert want.sort_index().equals(got.sort_index().astype(want.dtype))
    # loss counts by (cell, bin, year): forest(T) pixels lost in each counted year
    yy = lyg[rr, cc].astype(int) + 2000
    m = (yy >= years[0]) & (yy <= years[-1])
    want_l = pd.Series(1, index=(asg[rr, cc][m] * NB1 + b[m]) * 100 + (yy[m] - 2000)).groupby(level=0).sum()
    got_l = pd.Series(res["loss_n"], index=(res["loss_cell"].astype(np.int64) * NB1 + res["loss_bin"]) * 100
                      + (res["loss_year"].astype(np.int64) - 2000))
    assert want_l.sort_index().equals(got_l.sort_index().astype(want_l.dtype))
    assert res["counts"]["max_lossyear_used"] <= ymax - 2000


def test_map_pass_small_blocks_equal_one_block_counts_where_dx_matches(tmp_path):
    products, cells, _, _ = make_defo(tmp_path)
    a = run_pass(products, cells, 2010, [], 2019, block=64)
    b = run_pass(products, cells, 2010, [], 2019, block=16)
    assert np.array_equal(a["parity_forest"], b["parity_forest"])
    assert int(a["forest_n"].sum()) == int(b["forest_n"].sum())


def test_map_pass_refuses_loss_years_past_ymax(tmp_path):
    products, cells, _, _ = make_defo(tmp_path)
    with pytest.raises(DP.DefoPrepRefusal):
        run_pass(products, cells, 2008, list(range(2009, 2021)), 2019)


def test_missing_lossyear_tile_reads_zero_loss(tmp_path):
    products, cells, (tc, dm, ly), _ = make_defo(tmp_path, drop_loss_tile="10N_010E")
    res = run_pass(products, cells, 2008, [], 2019)
    ly2 = ly.copy()
    ly2[:, NPX:] = 0
    _, forest, loss = naive_counts(cells, tc, dm, ly2, 2019)
    assert np.array_equal(res["parity_loss"], loss) and np.array_equal(res["parity_forest"], forest)


# ---------------------------------------------------------------------------------------------------- stage + build
def prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class, rival_id="vt0007_shipped", stage="train", **kw):
    products, cells, layers, asg = make_defo(tmp_path, **kw)
    run = fake_run_class({0: {"fit_cut": 2019}, 1: {"fit_cut": 2019}})
    train_keys = keys_of(cells, range(2004, 2020), 0)
    test_keys = keys_of(cells, range(2020, 2024), 0)
    products["defo_vt0007_prep"] = Path(tmp_path) / "_work" / "vt0007_shipped"
    ctx = fake_ctx_class(tmp_path, run, rival_id, products,
                         keys={"train": train_keys, "test": test_keys,
                               "all": pd.concat([train_keys, test_keys], ignore_index=True)}, stage=stage)
    return ctx, products, cells, layers, asg


def naive_vt0007(cells, layers, asg, t, divisions, hrp=10, frozen=None):
    """Per-pixel reference of the method for issue year t (brute-force distances, bisection scale)."""
    tc, dm, ly = layers
    t_eff = t if frozen is None else min(t, frozen + 1)
    T1, T3 = t_eff - hrp - 1, t_eff - 1
    lyg = DP.lossyear_guard(ly, t_eff - 1)
    f2000 = (dm == 1) & (tc >= 30)
    bins = DP.FineBins(**BINS)
    out = {}
    for T in (T1, T3):
        fT = f2000 & ~((lyg >= 1) & (lyg <= T - 2000))
        src = (dm == 1) & ~fT
        rr, cc = np.nonzero((asg >= 0) & fT)
        # the prep's dx: one per block of 40 rows of the region window (block_px 40 in the toy registry)
        dist = np.empty(len(rr))
        r0, r1 = row_window(cells)
        for rs in range(r0, r1, 40):
            re_ = min(rs + 40, r1)
            lat_c = 10.0 - ((rs + re_) / 2.0) * PX
            dy = PX * DP.M_PER_DEG
            dx = dy * math.cos(math.radians(lat_c))
            m = (rr >= rs) & (rr < re_)
            dist[m] = brute_distance(src, rr[m], cc[m], dy, dx)
        out[T] = (rr, cc, bins.bin_of(dist))
    rr1, cc1, b1 = out[T1]
    yy = lyg[rr1, cc1].astype(int) + 2000
    lost = (yy >= t_eff - hrp) & (yy <= t_eff - 1)
    total = lost.sum()
    hist = np.bincount(b1[lost], minlength=bins.n + 1)
    b_star = int(np.searchsorted(np.cumsum(hist), 0.995 * total - 1e-9 * total))
    nrt = bins.upper()[b_star]
    cls = VT.class_of_bins(bins, nrt)
    div = divisions[asg[rr1, cc1]]
    F = pd.Series(1, index=pd.MultiIndex.from_arrays([div, cls[b1]])).groupby(level=[0, 1]).sum()
    L = pd.Series(lost.astype(int), index=pd.MultiIndex.from_arrays([div, cls[b1]])).groupby(level=[0, 1]).sum()
    freq = (L / F).to_dict()
    pooled = (L.groupby(level=1).sum() / F.groupby(level=1).sum()).to_dict()
    rr3, cc3, b3 = out[T3]
    d3, k3 = divisions[asg[rr3, cc3]], cls[b3]
    f = np.array([freq.get((a, b), pooled.get(b, 0.0)) for a, b in zip(d3, k3)])
    Q = total / float(hrp)
    lo, hi = 0.0, 1e12
    for _ in range(200):
        mid = (lo + hi) / 2
        if np.minimum(1.0, mid * f).sum() < Q:
            lo = mid
        else:
            hi = mid
    e = np.minimum(1.0, hi * f)
    exp_cell = np.bincount(asg[rr3, cc3], weights=e, minlength=len(cells))
    f2000c = cells["forest2000_px"].values
    return np.where(f2000c > 0, exp_cell / np.where(f2000c > 0, f2000c, 1), np.nan)


def test_stage_train_then_build_matches_per_pixel_reference(tmp_path, fake_ctx_class, fake_run_class):
    ctx, products, cells, layers, asg = prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class)
    rv = defo_rivals()
    # one prep issue year range shortened for speed: the toy target years 2011..2019 + frozen 2020
    man = DP.run_stage(ctx, rv["vt0007_shipped"], "train", workers=1)
    assert man["ymax"] == 2019 and set(man["parity"]) == {REGION}
    assert all(max(v) <= 2019 for v in man["plan"].values() if v)
    out0 = VT.build(ctx, rv["vt0007_shipped"], 0, "train")
    # src: every covered row names prep files opened through the product, the divisions and the static file
    cov = out0["x__vt0007"].notna()
    names = set(n for v in out0.loc[cov, "src"] for n in v.split(";"))
    assert names <= set(ctx.opened["defo_vt0007_prep"]) | set(ctx.opened["defo_static"])
    one = out0.loc[cov & (out0["time"] == 2015), "src"].iloc[0].split(";")
    assert "%s/map_T2004__train.npz" % REGION in one and "%s/map_T2014__train.npz" % REGION in one
    # coverage: issue years before 2011 are NaN
    assert out0.loc[out0["time"] < 2011, "x__vt0007"].isna().all()
    f0 = out0["unit"].map(cells.set_index("cell_id")["forest2000_px"]).values > 0
    assert out0.loc[(out0["time"] >= 2011).values & f0, "x__vt0007"].notna().all()
    assert out0.loc[~f0, "x__vt0007"].isna().all() and (~f0).any()      # the lake cells: no forest2000
    # review issue 1: info_end = the newest non-label input (treecover2000: 2000); the loss years are target obs (T2)
    assert (out0["info_end"] == 2000).all() and (out0["target_obs_end"] == out0["time"] - 1).all()
    # per-pixel reference for two issue years
    import pyarrow.parquet as pq
    dv = pq.read_table(str(DP.prep_dir(ctx, rv["vt0007_shipped"]) / REGION / DP.DIVISION_FILE)).to_pandas()
    codes, _ = pd.factorize(dv["division"], sort=True)
    for t in (2013, 2019):
        want = naive_vt0007(cells, layers, asg, t, codes)
        got = out0[out0["time"] == t].set_index("unit")["x__vt0007"].reindex(cells["cell_id"]).values
        assert np.allclose(got, want, rtol=1e-9, atol=1e-12, equal_nan=True)
    # quantity: the group's expected loss pixels equal the HRP mean annual loss
    rep = out0.attrs["adapter_report"]["groups_years"]["%s:2019" % REGION]
    assert rep["allocated"] == pytest.approx(rep["Q"], rel=1e-9)
    # lead 1: identical values per (unit, time)
    ctx1 = fake_ctx_class(tmp_path, ctx.run, "vt0007_shipped", products,
                          keys={"train": keys_of(cells, range(2004, 2020), 1)}, stage="train")
    out1 = VT.build(ctx1, rv["vt0007_shipped"], 1, "train")
    assert np.array_equal(out0["x__vt0007"].values, out1["x__vt0007"].values, equal_nan=True)
    assert (out1["issue"] == out1["time"] - 1).all() and (out1["info_end"] == 2000).all()
    assert (out1["target_obs_end"] == out1["time"] - 1).all()
    # the calibrated rival reads the same prep (sibling work folder) and gives the same index
    ctxc = fake_ctx_class(tmp_path, ctx.run, "vt0007_cal", products, keys={"train": keys_of(cells, range(2004, 2020),
                                                                                             0)}, stage="train")
    outc = VT.build(ctxc, rv["vt0007_cal"], 0, "train")
    assert np.array_equal(out0["x__vt0007"].values, outc["x__vt0007"].values, equal_nan=True)
    # resume: a second run of the stage skips every finished map
    n_before = len(ctx.lines)
    DP.run_stage(ctx, rv["vt0007_shipped"], "train", workers=1)
    assert any("0 map passes to run" in l for l in ctx.lines[n_before:])


def test_stage_test_refuses_without_lock_and_train_refuses_test_rows(tmp_path, fake_ctx_class, fake_run_class):
    ctx, products, cells, _, _ = prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class, stage="test")
    rv = defo_rivals()
    with pytest.raises(Exception, match="lock"):
        DP.run_stage(ctx, rv["vt0007_shipped"], "test")
    with pytest.raises(Exception, match="lock"):
        VT.build(ctx, rv["vt0007_shipped"], 0, "test")
    ctx_tr = fake_ctx_class(tmp_path, ctx.run, "vt0007_shipped", products,
                            keys={"train": keys_of(cells, range(2018, 2021), 0)}, stage="train")
    with pytest.raises(VT.VT0007Refusal, match="fit cut"):
        VT.build(ctx_tr, rv["vt0007_shipped"], 0, "train")


def test_parity_mismatch_stops_the_prep(tmp_path, fake_ctx_class, fake_run_class):
    ctx, *_ = prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class, tamper_target=True)
    with pytest.raises(DP.DefoPrepRefusal, match="PARITY"):
        DP.run_stage(ctx, defo_rivals()["vt0007_shipped"], "train")


def test_stage_test_after_lock_and_frozen_form(tmp_path, fake_ctx_class, fake_run_class):
    ctx, products, cells, layers, asg = prep_and_ctx(tmp_path, fake_ctx_class, fake_run_class)
    rv = defo_rivals()
    DP.run_stage(ctx, rv["vt0007_shipped"], "train")
    called = []
    ctx_t = fake_ctx_class(tmp_path, ctx.run, "vt0007_shipped", products,
                           keys={"test": keys_of(cells, range(2020, 2024), 0)}, stage="test")
    ctx_t.require_human_lock = lambda: called.append(1)
    # the toy target holds loss to 2022: the test stage reads it only now
    man = DP.run_stage(ctx_t, rv["vt0007_shipped"], "test")
    assert called and man["ymax"] == 2022
    out = VT.build(ctx_t, rv["vt0007_shipped"], 0, "test")
    import pyarrow.parquet as pq
    dv = pq.read_table(str(DP.prep_dir(ctx, rv["vt0007_shipped"]) / REGION / DP.DIVISION_FILE)).to_pandas()
    codes, _ = pd.factorize(dv["division"], sort=True)
    for t in (2020, 2023):
        want = naive_vt0007(cells, layers, asg, t, codes)
        got = out[out["time"] == t].set_index("unit")["x__vt0007"].reindex(cells["cell_id"]).values
        assert np.allclose(got, want, rtol=1e-9, atol=1e-12, equal_nan=True)
    # frozen 2019: every test year equals the t = 2020 map; target_obs_end stays 2019 (info_end 2000)
    ctx_f = fake_ctx_class(tmp_path, ctx.run, "vt0007_frozen2019", products,
                           keys={"test": keys_of(cells, range(2020, 2024), 0)}, stage="test")
    ctx_f.require_human_lock = lambda: None
    outf = VT.build(ctx_f, rv["vt0007_frozen2019"], 0, "test")
    a = outf[outf["time"] == 2020].set_index("unit")["x__vt0007"]
    b = outf[outf["time"] == 2023].set_index("unit")["x__vt0007"]
    assert np.array_equal(a.values, b.reindex(a.index).values, equal_nan=True)
    assert (outf["target_obs_end"] == 2019).all() and (outf["info_end"] == 2000).all()
    r2020 = out[out["time"] == 2020].set_index("unit")["x__vt0007"]
    assert np.array_equal(a.values, r2020.reindex(a.index).values, equal_nan=True)


def test_two_workers_give_the_same_files(tmp_path, fake_ctx_class, fake_run_class):
    ctx1, products, cells, _, _ = prep_and_ctx(tmp_path / "a", fake_ctx_class, fake_run_class)
    ctx2, _, _, _, _ = prep_and_ctx(tmp_path / "b", fake_ctx_class, fake_run_class)
    rv = defo_rivals()
    m1 = DP.run_stage(ctx1, rv["vt0007_shipped"], "train", workers=1)
    m2 = DP.run_stage(ctx2, rv["vt0007_shipped"], "train", workers=2)
    assert m1["files_sha256"] == m2["files_sha256"]
