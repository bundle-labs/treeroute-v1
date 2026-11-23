"""T-H17 the defo rule on toy arrays, tiles and polygons (SPEC_HUMAN.txt section 3; adapters/defo_prep.py,
defo_vt0007.py): the lossyear guard and the refusal of a loss year past the stage's bound (PLAN R8); 30 classes cut
at the 99.5% HRP-loss distance; the quantity scaling with the pixel cap (total = Q exactly; water-filling); the cell
sum over forest2000; the frequency fallback; GADM overlap assignment, the nearest-within-half-a-cell fallback and the
level-1 fallback; the parity check against a toy target."""

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O
from rivals_human.tests import toy_products as TP


def _dp():
    return HK.tool("defo_prep")


def _vt():
    return HK.tool("defo_vt0007")


def test_h17_lossyear_guard_and_forest_mask():
    DP = _dp()
    ly = np.array([[0, 5, 19], [20, 22, 11]], dtype=np.uint8)
    g = HK.need(DP, "lossyear_guard", "B3")(ly, 2019)
    assert g.tolist() == [[0, 5, 19], [0, 0, 11]]
    tc = np.full_like(ly, 50)
    dm = np.ones_like(ly)
    # forest at the end of 2015 from the guarded layer equals the oracle on the raw layer (later loss is invisible)
    assert np.array_equal(O.forest_mask(tc, dm, g, 2015), O.forest_mask(tc, dm, ly, 2015))


def test_h17_a_loss_year_past_the_stage_bound_refuses():
    DP = _dp()
    HK.refuses(("ymax", "must lie"), HK.need(DP, "map_pass", "B3"), {"T": 2020, "ymax": 2019, "loss_years": []})
    HK.refuses(("ymax", "must lie"), DP.map_pass, {"T": 2010, "ymax": 2019, "loss_years": [2011, 2020]})
    HK.refuses(("contiguous",), DP.map_pass, {"T": 2010, "ymax": 2019, "loss_years": [2011, 2013]})


def test_h17_thirty_classes_cut_at_the_nrt():
    DP, VT = _dp(), _vt()
    bins = DP.FineBins(10.0, 1.0e5, 200)
    nrt = float(bins.upper()[120])
    cls = HK.need(VT, "class_of_bins", "B3")(bins, nrt)
    up = bins.upper()
    assert cls.min() >= 1 and cls.max() == 30
    assert (np.diff(cls) >= 0).all()
    assert (cls[up <= nrt * (1 + 1e-12)] <= 29).all() and (cls[up > nrt * (1 + 1e-12)] == 30).all()
    assert len(set(cls[up <= nrt].tolist())) <= 29


@pytest.mark.parametrize("Q", [0.5, 3.0, 20.0])
def test_h17_quantity_scaling_with_the_cap_matches_the_oracle(Q):
    VT = _vt()
    rng = np.random.default_rng(4)
    P = rng.integers(1, 6, size=40).astype(float)
    f = rng.uniform(0.001, 0.4, size=40)
    s, capped = HK.need(VT, "solve_scale", "B3")(P, f, Q)
    e = np.minimum(1.0, s * f)
    assert not capped
    assert float((P * e).sum()) == pytest.approx(Q, rel=1e-9)
    want = O.vt0007_quantity(np.repeat(f, P.astype(int)), Q)       # pixel by pixel
    got = np.repeat(e, P.astype(int))
    assert np.allclose(got, want, atol=1e-9)
    s2, capped2 = VT.solve_scale(P, f, float(P.sum()) + 1)
    assert capped2 and not np.isfinite(s2)


def test_h17_vt0007_region_allocates_q_over_forest_and_divides_by_forest2000():
    DP, VT = _dp(), _vt()
    bins = DP.FineBins(10.0, 1.0e5, 60)
    nb1 = bins.n + 1
    rng = np.random.default_rng(9)
    ncell = 6
    F1 = rng.integers(0, 50, size=(ncell, nb1)).astype(float)
    F1[:, -1] = 0
    Lh = np.zeros_like(F1)
    Lh[:, :20] = rng.integers(0, 3, size=(ncell, 20))               # loss close to the edge
    F3 = np.maximum(F1 - Lh, 0)
    div = np.array([0, 0, 1, 1, 2, 2])
    forest2000 = np.array([500.0, 400.0, 0.0, 300.0, 250.0, 100.0])
    x, rep = HK.need(VT, "vt0007_region", "B3")(F1, Lh, F3, div, forest2000, bins, 10)
    Q = Lh.sum() / 10.0
    assert rep["Q"] == pytest.approx(Q)
    assert np.isnan(x[2])                                         # no forest in 2000: not covered
    has = forest2000 > 0
    if not rep["all_capped"]:
        assert float(np.nansum(x[has] * forest2000[has])) <= Q * (1 + 1e-9)
        assert rep["allocated"] == pytest.approx(Q, rel=1e-9)
    cum = np.cumsum(Lh.sum(axis=0))
    b_star = int(np.searchsorted(cum, 0.995 * cum[-1] - 1e-9 * cum[-1], side="left"))
    assert rep["nrt_m"] == pytest.approx(float(bins.upper()[b_star]))


def test_h17_no_hrp_loss_gives_zero(tmp_path):
    DP, VT = _dp(), _vt()
    bins = DP.FineBins(10.0, 1.0e5, 20)
    F = np.ones((3, bins.n + 1))
    x, rep = VT.vt0007_region(F, np.zeros_like(F), F, np.array([0, 0, 0]), np.array([1.0, 0.0, 2.0]), bins, 10)
    assert x[0] == 0.0 and np.isnan(x[1]) and x[2] == 0.0


def _gadm(tmp_path, iso="TOY", level=2):
    from shapely.geometry import box
    return TP.write_gadm_toy(tmp_path / ("gadm_%s_%d" % (iso, level)),
                             [("%s.1.1_1" % iso, box(20.0, 9.0, 20.5, 10.0)), ("%s.1.2_1" % iso, box(20.5, 9.0, 21.0, 10.0))],
                             iso=iso, level=level)


def test_h17_overlap_assignment_and_the_half_cell_fallback(tmp_path):
    DP = _dp()
    zp = _gadm(tmp_path)
    h = 0.05                                                       # cells of 0.1 degree
    cells = ["c_left", "c_right", "c_straddle", "c_near", "c_far"]
    lon = np.array([20.20, 20.80, 20.53, 21.08, 22.00])
    lat = np.array([9.50, 9.50, 9.50, 9.50, 9.50])
    out, rep = HK.need(DP, "assign_divisions", "B3")(cells, lon, lat, h, h, [zp])
    d = dict(zip(out["cell_id"], out["division"]))
    s = dict(zip(out["cell_id"], out["step"]))
    assert d["c_left"] == "TOY.1.1_1" and s["c_left"] == "overlap"
    assert d["c_right"] == "TOY.1.2_1"
    assert d["c_straddle"] == "TOY.1.2_1"                          # 0.08 of 0.1 overlaps the right division
    assert s["c_near"] == "nearest" and d["c_near"] == "TOY.1.2_1"  # 0.03 gap <= half a cell (0.05)
    assert s["c_far"] == "none"
    assert rep["overlap"] == 3 and rep["nearest"] == 1 and rep["none"] == 1


def test_h17_level_1_fallback(tmp_path):
    DP = _dp()
    zp = _gadm(tmp_path, iso="TOI", level=1)
    out, rep = DP.assign_divisions(["c"], np.array([20.2]), np.array([9.5]), 0.05, 0.05, [zp])
    assert int(out["level"].iloc[0]) == 1 and rep["level1_cells"] == 1
    assert rep["level_by_country"] == {"TOI": 1}


def test_h17_parity_with_toy_loss_counts(tmp_path):
    DP = _dp()
    cells = np.array(["a", "b"])
    forest = np.array([10, 20], dtype=np.int64)
    loss = np.zeros((2, 19), dtype=np.int64)                       # years 2001..2019
    loss[0, 4] = 3                                                 # 2005
    loss[1, 18] = 2                                                # 2019
    rows = []
    for ci, c in enumerate(cells):
        for y in range(2001, 2023):
            rows.append({"cell_id": c, "year": y, "loss_px": int(loss[ci, y - 2001]) if y <= 2019 else 99,
                         "forest2000_px": int(forest[ci])})
    tp = HK.write_parquet(tmp_path / "target.parquet", pd.DataFrame(rows))
    rec = HK.need(DP, "parity_check", "B3")("toy", cells, forest, loss, 2019, tp)
    assert rec["rows_compared"] == 2 * 19                           # labels after the stage bound are never read
    bad = loss.copy()
    bad[1, 18] = 1
    HK.refuses("PARITY", DP.parity_check, "toy", cells, forest, bad, 2019, tp)
