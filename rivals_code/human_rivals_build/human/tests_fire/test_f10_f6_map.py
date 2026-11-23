"""T-F10 F6PctRatio after the 4.4 edit of rivals_human/maps.py (SPEC_HUMAN_PARTB.txt 4.4; research C-A; PLAN rule
5; review R-1, R-2). No test of F6 existed before Part B.

  cells c = (unit, season key) of the PASSED rows; n_c, S_c = count and sum of y; the slim normal z0 must be the
  in-sample cell mean (|S_c / n_c - z0| <= F6_NORMAL_TOL on every row of a complete cell; incomplete rows dropped and
  counted; more than F6_MAX_INCOMPLETE_SHARE of the passed rows refuses through rivals_human.common.refuse);
  N_loo = (S_c - y) / (n_c - 1) from the cell SUM; n_c < 2 and N_loo <= 0 dropped and counted;
  r = y / N_loo fitted isotonic with weights N_loo^2 (argmin sum (y - N_loo r(x))^2), pooled and per group (>= 100
  KEPT rows); direction = Spearman sign of (x, y) on the passed rows; predict = z0 (the scored rows' own normal) x r(x).

Also: the other link refuses as NotCalibratable (tune records not_calibratable); the default Iso.fit path, F2 and F4
are byte-equal to the baseline module (_moved/<utc>_partB_baseline/rivals_human/maps.py, sha f38d7ce7...); the geff
rivals of registry/fire.yaml have 30 candidates.
"""

import json

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF

C_ = 0.012987012987012988
UB = 1.0
BASELINE_MAPS_SHA = "f38d7ce78ede1b101b5fba89fb4aa89559171e63e1532e60d58bd030acb91a59"
INFO_KEYS = ("rows_passed", "rows_kept", "rows_incomplete_cell", "rows_single_row_cell", "rows_zero_loo_normal",
             "rows_zero_loo_normal_burned", "normal_check_max_abs_diff", "weighted_level")


@pytest.fixture(scope="module")
def MP():
    from rivals_human import maps
    return maps


@pytest.fixture(scope="module")
def base_maps():
    return FF.load_module_from(FF.baseline_file("rivals_human/maps.py", BASELINE_MAPS_SHA), "tests_fire_maps_partA")


# ------------------------------------------------------------------------------------------ toys
def frame_of(cells):
    """cells: [(unit, group, season key, ys, xs)] -> rows (one per year) with the in-sample cell mean z0."""
    rows = []
    for (u, g, k, ys, xs) in cells:
        for n, (y, x) in enumerate(zip(ys, xs)):
            rows.append({"unit": u, "group": g, "time": FF.step(2003 + n, k), "season_key": int(k), "y": float(y),
                         "x": float(x)})
    f = pd.DataFrame(rows)
    f["issue"] = f["time"]
    f["lead"] = 0
    f["z0"] = f.groupby(["unit", "season_key"])["y"].transform("mean")
    return f


def keys_of(f):
    k = f[["unit", "group", "time", "issue", "lead", "season_key"]].reset_index(drop=True).copy()
    k["unit"] = k["unit"].astype(str)
    k["group"] = k["group"].astype(str)
    return k


def fit(MP, f, z0=None, link="identity", family="F6", module=None):
    m = module or MP
    z = f["z0"] if z0 is None else z0
    return m.fit(family, f["x"].to_numpy(np.float64), f["y"].to_numpy(np.float64), np.asarray(z, np.float64), link,
                 C_, UB, f["unit"].astype(str).to_numpy(), keys_of(f))


def ratio_at(m, x, group="__none__"):
    """The fitted ratio at x (predict with z0 = 1 on a group without its own map -> the pooled map)."""
    x = np.atleast_1d(np.asarray(x, np.float64))
    k = pd.DataFrame({"unit": ["q"] * x.size, "group": [group] * x.size, "time": [1] * x.size, "issue": [1] * x.size,
                      "lead": [0] * x.size, "season_key": [1] * x.size})
    return np.asarray(m.predict(x, np.ones(x.size), k["unit"].to_numpy(), k), np.float64)


def positive(rng, groups=("A", "B", "C"), units=4, keys=12, years=4, x=None):
    cells = []
    for g in groups:
        for k in range(units):
            for sk in range(1, keys + 1):
                xs = rng.uniform(0.0, 1.0, years) if x is None else np.full(years, float(x))
                cells.append(("%s_u%d" % (g, k), g, sk, rng.uniform(0.01, 0.2, years), xs))
    return cells


def loo(f):
    g = f.groupby(["unit", "season_key"])["y"]
    S = g.transform("sum").to_numpy(np.float64)
    n = g.transform("count").to_numpy(np.int64)
    y = f["y"].to_numpy(np.float64)
    nl = np.full(y.size, np.nan)
    multi = n >= 2
    nl[multi] = (S[multi] - y[multi]) / (n[multi] - 1)
    return nl, multi & (nl > 0)


def info_of(m):
    d = m.to_json()
    return d, d["info"]


def pooled_of(d):
    p = d.get("pooled")
    return p if isinstance(p, dict) else d["info"]["pooled"]


# ------------------------------------------------------------------------------------------ link
def test_f10_other_links_are_not_calibratable(MP):
    f = frame_of(positive(np.random.default_rng(1)))
    for link in ("log_c", "arcsine"):
        with pytest.raises(MP.NotCalibratable):
            fit(MP, f, link=link)
        with pytest.raises(MP.NotCalibratable):
            MP.F6PctRatio.fit(f["x"].to_numpy(), f["y"].to_numpy(), f["z0"].to_numpy(), link, C_, UB,
                              f["unit"].to_numpy(), keys_of(f))


def test_f10_module_constants(MP):
    assert MP.F6_NORMAL_TOL == 1e-12
    assert MP.F6_MAX_INCOMPLETE_SHARE == 0.05


# ------------------------------------------------------------------------------------------ normal check
def test_f10_normal_check(MP):
    from rivals_human.common import HumanRefusal
    rng = np.random.default_rng(2)
    f = frame_of(positive(rng, keys=3, years=16))                       # 144 cells of 16 rows = 2,304 rows
    m = fit(MP, f)
    d, info = info_of(m)
    assert info["rows_passed"] == len(f) and info["rows_incomplete_cell"] == 0
    assert 0.0 <= info["normal_check_max_abs_diff"] <= 1e-12
    exc = FF.refuses(fit, MP, f, z0=f["z0"] + 0.01)                     # not the in-sample mean anywhere
    assert isinstance(exc, HumanRefusal) and not isinstance(exc, MP.NotCalibratable)
    # one row removed from one 16-row cell: that cell (15 rows, < 5%) is dropped and counted, the fit goes on
    cell = (f["unit"] == "B_u2") & (f["season_key"] == 2)
    assert cell.sum() == 16 and f.loc[cell, "y"].nunique() == 16
    part = f.drop(index=f.index[cell][5]).reset_index(drop=True)
    m2 = fit(MP, part)
    d2, info2 = info_of(m2)
    assert info2["rows_passed"] == len(f) - 1
    assert info2["rows_incomplete_cell"] == 15
    assert info2["rows_kept"] == len(f) - 16
    # above 5%: 9 partial cells of 15 rows = 135 of 2,295 rows (5.9%) -> refuse
    drop = []
    for k, (u, sk) in enumerate([(u, sk) for u in ("A_u0", "A_u1", "A_u2") for sk in (1, 2, 3)]):
        drop.append(f.index[(f["unit"] == u) & (f["season_key"] == sk)][0])
    many = f.drop(index=drop).reset_index(drop=True)
    exc = FF.refuses(fit, MP, many)
    assert isinstance(exc, HumanRefusal) and not isinstance(exc, MP.NotCalibratable)


# ------------------------------------------------------------------------------------------ leave-year-out
def _burn_cell_size():
    """A cell size n where n * mean(y) - 0.1 leaves a POSITIVE float residue (y = one burn of 0.1, the rest 0): a
    leave-one-out normal computed as n z0 - y would keep the burned row with a ratio ~1e16 (facts list)."""
    for n in range(3, 30):
        y = np.zeros(n)
        y[0] = 0.1
        z0 = float(pd.Series(y).mean())
        if n * z0 - 0.1 > 0:
            return n
    pytest.fail("no cell size with a positive residue (the toy needs one)")


def test_f10_leave_year_out_counts(MP):
    rng = np.random.default_rng(3)
    nb = _burn_cell_size()
    cells = positive(rng)                                               # every row y > 0: no zero N_loo
    cells.append(("H_hand", "A", 1, [0.0, 0.0, 0.3], [0.2, 0.5, 0.8]))  # N_loo = [0.15, 0.15, 0.0]
    cells.append(("H_single", "B", 1, [0.05], [0.4]))                   # a one-row cell
    cells.append(("H_burn", "C", 1, [0.1] + [0.0] * (nb - 1), list(np.linspace(0.1, 0.9, nb))))
    f = frame_of(cells)
    hand = f[f["unit"] == "H_hand"]
    nl, kept = loo(f)
    np.testing.assert_allclose(nl[hand.index], [0.15, 0.15, 0.0], rtol=0, atol=1e-15)
    assert nl[f.index[(f["unit"] == "H_burn")][0]] == 0.0                # from the cell SUM: exactly 0
    m = fit(MP, f)
    d, info = info_of(m)
    for k in INFO_KEYS:
        assert k in info, k
    assert info["rows_passed"] == len(f)
    assert info["rows_incomplete_cell"] == 0
    assert info["rows_single_row_cell"] == 1
    assert info["rows_zero_loo_normal"] == 2
    assert info["rows_zero_loo_normal_burned"] == 2
    assert info["rows_kept"] == int(kept.sum()) == len(f) - 1 - 2
    y = f["y"].to_numpy()
    want = float(np.dot(nl[kept], y[kept]) / np.dot(nl[kept], nl[kept]))
    assert info["weighted_level"] == pytest.approx(want, rel=1e-12)


def test_f10_too_few_kept_rows_is_not_calibratable(MP):
    """check_calibratable runs on the KEPT rows: all-zero cells keep nothing."""
    rng = np.random.default_rng(4)
    cells = [("Z_%d" % k, "ABC"[k % 3], 1, [0.0] * 4, rng.uniform(0, 1, 4)) for k in range(60)]
    cells += [("P_%d" % k, "ABC"[k % 3], 2, rng.uniform(0.01, 0.2, 4), rng.uniform(0, 1, 4)) for k in range(10)]
    f = frame_of(cells)                                                 # 280 passed, 40 kept
    with pytest.raises(MP.NotCalibratable):
        fit(MP, f)


# ------------------------------------------------------------------------------------------ weights
def test_f10_tiny_normal_row_cannot_rule_the_curve(MP):
    """Many rows of ratio 1 (N_loo 0.1) plus one row with N_loo ~0.001 and ratio ~100 at the same x: the fitted ratio
    there is the N_loo^2-weighted mean (hand, rel 1e-12) and stays below 1.001; the unweighted mean is far above."""
    cells = [("b%02d" % k, "ABC"[k % 3], 1, [0.1, 0.1], [0.5, 0.5]) for k in range(50)]
    cells.append(("tiny", "A", 1, [0.1, 0.001, 0.001], [0.5, 0.1, 0.1]))
    f = frame_of(cells)
    nl, kept = loo(f)
    assert kept.all()
    y, x = f["y"].to_numpy(), f["x"].to_numpy()
    at = (x == 0.5) & kept
    r = y[at] / nl[at]
    tiny = int(f.index[f["unit"] == "tiny"][0])
    assert nl[tiny] == pytest.approx(0.001, rel=1e-9) and r.max() == pytest.approx(100.0, rel=1e-9)
    weighted = float(np.dot(nl[at], y[at]) / np.dot(nl[at], nl[at]))
    unweighted = float(r.mean())
    m = fit(MP, f)
    got = float(ratio_at(m, 0.5)[0])
    assert got == pytest.approx(weighted, rel=1e-12)
    assert got < 1.001 and unweighted > 1.5
    assert float(ratio_at(m, 0.1)[0]) < got                              # the partners' block, below


def test_f10_one_block_is_the_least_squares_level(MP):
    rng = np.random.default_rng(5)
    f = frame_of(positive(rng, x=0.5))
    nl, kept = loo(f)
    y = f["y"].to_numpy()
    want = float(np.dot(nl[kept], y[kept]) / np.dot(nl[kept], nl[kept]))
    m = fit(MP, f)
    got = float(ratio_at(m, 0.5)[0])
    assert got == pytest.approx(want, rel=1e-12)
    # the argmin of sum (y - N_loo r)^2 over r: a small step either way is worse
    sse = lambda rr: float(np.sum((y[kept] - nl[kept] * rr) ** 2))
    assert sse(got) <= sse(got * (1 + 1e-6)) and sse(got) <= sse(got * (1 - 1e-6))
    assert info_of(m)[1]["weighted_level"] == pytest.approx(want, rel=1e-12)


# ------------------------------------------------------------------------------------------ groups, direction, shape
def test_f10_groups_need_100_kept_rows_for_their_own_map(MP):
    rng = np.random.default_rng(6)
    cells = [("A%02d" % k, "A", 1, rng.uniform(0.01, 0.2, 4), rng.uniform(0, 1, 4)) for k in range(30)]   # 120 kept
    cells += [("B%02d" % k, "B", 1, rng.uniform(0.01, 0.2, 4), rng.uniform(0, 1, 4)) for k in range(20)]  # 80 kept
    cells += [("Bs%02d" % k, "B", 2, rng.uniform(0.01, 0.2, 1), rng.uniform(0, 1, 1)) for k in range(30)]  # dropped
    cells += [("C%02d" % k, "C", 1, rng.uniform(0.01, 0.2, 4), rng.uniform(0, 1, 4)) for k in range(10)]  # 40 kept
    f = frame_of(cells)
    assert (f["group"] == "B").sum() == 110
    m = fit(MP, f)
    d, info = info_of(m)
    assert sorted(d["groups"]) == ["A"]
    xs = np.linspace(0.0, 1.0, 11)
    np.testing.assert_array_equal(ratio_at(m, xs, "B"), ratio_at(m, xs))         # B: the pooled map
    assert not np.array_equal(ratio_at(m, xs, "A"), ratio_at(m, xs))


def test_f10_direction_follows_spearman_of_x_and_y(MP):
    rng = np.random.default_rng(7)
    cells = []
    for k in range(60):
        xs = rng.uniform(0, 1, 4)
        cells.append(("D%02d" % k, "ABC"[k % 3], 1, 0.2 - 0.15 * xs + rng.uniform(0, 0.01, 4), xs))
    f = frame_of(cells)
    m = fit(MP, f)
    d, info = info_of(m)
    p = pooled_of(d)
    assert p["increasing"] is False
    r = ratio_at(m, np.linspace(0, 1, 21))
    assert (np.diff(r) <= 1e-15).all()


def test_f10_recovers_the_ratio_curve(MP):
    """2-row cells (p, 1 - p) with y_b = c and y_a = c r(p_a), r(p) = exp(2 (p - 0.5)): then y / N_loo = r(p) on every
    row exactly, so the weighted isotonic fit returns r at every observed p (and within the knot spacing between)."""
    rng = np.random.default_rng(8)
    r = lambda p: np.exp(2.0 * (np.asarray(p) - 0.5))
    cells = []
    for k in range(300):
        pa = float(rng.uniform(0.02, 0.98))
        c = float(rng.uniform(0.01, 0.05))
        cells.append(("R%03d" % k, "ABC"[k % 3], 1 + k % 12, [c * float(r(pa)), c], [pa, 1.0 - pa]))
    f = frame_of(cells)
    from scipy.stats import spearmanr
    assert spearmanr(f["x"], f["y"]).correlation > 0
    m = fit(MP, f)
    d, info = info_of(m)
    assert info["rows_kept"] == len(f)
    for g in ("A", "B", "C"):
        sel = f["group"] == g
        xs = np.sort(f.loc[sel, "x"].to_numpy())
        np.testing.assert_allclose(ratio_at(m, xs, g), r(xs), rtol=1e-9)
        gap = float(np.max(np.diff(xs)))
        grid = np.linspace(xs[0], xs[-1], 101)
        np.testing.assert_allclose(ratio_at(m, grid, g), r(grid), rtol=0, atol=2.0 * np.exp(1.0) * gap)
    xs = np.sort(f["x"].to_numpy())
    np.testing.assert_allclose(ratio_at(m, xs), r(xs), rtol=1e-9)


def test_f10_predict_uses_the_passed_normal_and_json(MP):
    rng = np.random.default_rng(9)
    f = frame_of(positive(rng))
    m = fit(MP, f)
    k = keys_of(f)
    x = f["x"].to_numpy()
    z0 = f["z0"].to_numpy()
    p1 = np.asarray(m.predict(x, z0, f["unit"].to_numpy(), k), np.float64)
    p2 = np.asarray(m.predict(x, 2.0 * z0, f["unit"].to_numpy(), k), np.float64)
    np.testing.assert_array_equal(p2, 2.0 * p1)                           # z0 x ratio(x)
    ratio = np.array([ratio_at(m, xi, g)[0] for xi, g in zip(x[:50], f["group"].to_numpy()[:50])])
    np.testing.assert_allclose(p1[:50], z0[:50] * ratio, rtol=1e-15)
    nl, kept = loo(f)
    assert not np.allclose(p1[:50], nl[:50] * ratio)                      # never the leave-one-out normal
    d, info = info_of(m)
    assert d["family"] == "F6" and d["link"] == "identity"
    assert isinstance(d["groups"], dict) and isinstance(pooled_of(d), dict)
    for key in INFO_KEYS:
        assert key in info
    text = json.dumps(d, sort_keys=True)
    again = json.dumps(fit(MP, f).to_json(), sort_keys=True)
    assert text == again                                                  # fit twice -> byte-equal


# ------------------------------------------------------------------------------------------ unchanged paths
def test_f10_iso_fit_default_path_is_byte_equal_to_the_baseline(MP, base_maps):
    rng = np.random.default_rng(10)
    for inc in (True, False):
        x = np.round(rng.uniform(0, 1, 500), 3)
        t = rng.normal(0, 1, 500) + (2 * x if inc else -2 * x)
        a = base_maps.Iso.fit(x, t, inc, 0.5)
        for b in (MP.Iso.fit(x, t, inc, 0.5), MP.Iso.fit(x, t, inc, 0.5, weights=None)):
            assert a.xk.tobytes() == b.xk.tobytes() and a.yk.tobytes() == b.yk.tobytes()
            assert json.dumps(a.to_json(), sort_keys=True) == json.dumps(b.to_json(), sort_keys=True)
    w = MP.Iso.fit(x, t, False, 0.5, weights=np.full(x.size, 3.0))       # equal weights: the same curve
    np.testing.assert_allclose(w.yk, a.yk, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("family", ["F2", "F4"])
@pytest.mark.parametrize("link", ["identity", "log_c"])
def test_f10_f2_f4_are_byte_equal_to_the_baseline(MP, base_maps, family, link):
    rng = np.random.default_rng(11)
    f = frame_of(positive(rng))
    a = fit(MP, f, link=link, family=family, module=base_maps)
    b = fit(MP, f, link=link, family=family)
    assert json.dumps(a.to_json(), sort_keys=True) == json.dumps(b.to_json(), sort_keys=True)
    k = keys_of(f)
    pa = a.predict(f["x"].to_numpy(), f["z0"].to_numpy(), f["unit"].to_numpy(), k)
    pb = b.predict(f["x"].to_numpy(), f["z0"].to_numpy(), f["unit"].to_numpy(), k)
    assert np.asarray(pa).tobytes() == np.asarray(pb).tobytes()


def test_f10_candidates_of_the_geff_rivals(MP):
    C, cfg = FF.real_registry_cfg()
    reg = C.load_registry(cfg, "fire")
    for rid in ("geff_era5", "geff_seas5"):
        rival = next(r for r in reg["rivals"] if r["id"] == rid)
        cands = MP.candidates(rival, FF.LINKS)
        assert len(cands) == 30, (rid, len(cands))
        fams = [c["family"] for c in cands]
        assert fams.count("F6") == 6 and "F0" not in fams and "F1" not in fams
        assert sorted(set(c["stat"] for c in cands)) == sorted(FF.STATS)
        assert len(set(c["id"] for c in cands)) == 30
