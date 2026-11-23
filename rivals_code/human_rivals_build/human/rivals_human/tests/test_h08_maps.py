"""T-H08 calibration maps (SPEC_HUMAN.txt 1.6, A4; maps.py): F1-F5 recover known synthetic maps; the isotonic
direction follows the Spearman sign of the fit rows; F5 equals the hand shrinkage formula with K = 10; a unit with
fewer than 3 rows takes the pooled map (counted); fewer than 100 rows or 3 groups -> not calibratable; the link
round trip is exact to 1e-12; the L1 isotonic map is an L1-optimal monotone fit. Synthetic data, no toy run."""

import math

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O

N_UNITS, N_GROUPS = 30, 6


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    """The common package loaded through the tool's pinned import (maps reaches the engine links through it)."""
    cfg = HK.minimal_config(tmp_path_factory.mktemp("maps_cfg"))
    HK.common_modules(cfg)
    return cfg


def _frame(n=720, seed=11):
    rng = np.random.default_rng(seed)
    units = np.array(["u%02d" % (i % N_UNITS) for i in range(n)])
    groups = np.array(["g%d" % ((i % N_UNITS) % N_GROUPS) for i in range(n)])
    time = 24000 + np.arange(n) // N_UNITS
    season = (time - 1) % 12 + 1
    keys = pd.DataFrame({"unit": units, "group": groups, "time": time, "issue": time, "lead": 0,
                         "season_key": season})
    x = rng.uniform(1.0, 10.0, size=n)
    z0 = rng.normal(2.0, 0.3, size=n)
    return keys, x, z0, rng


def _maps():
    return HK.tool("maps")


def test_h08_constants(loaded):
    C = HK.tool("config")
    assert C.SHRINK_K == 10 and C.MIN_FIT_ROWS == 100 and C.MIN_FIT_GROUPS == 3 and C.MIN_UNIT_ROWS == 3


def test_h08_f1_recovers_a_line_in_link_space(loaded):
    keys, x, z0, _ = _frame()
    y = 2.0 + 0.5 * x
    m = HK.fit_map("F1", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    assert m.info["a"] == pytest.approx(2.0, abs=1e-9) and m.info["b"] == pytest.approx(0.5, abs=1e-9)
    assert np.allclose(m.predict(x, z0, keys["unit"].to_numpy(), keys), y, atol=1e-9)
    c = 1.0
    y2 = np.exp(0.3 + 0.8 * np.log(x + c)) - c
    m2 = HK.fit_map("F1", x, y2, z0, "log_c", c, None, keys["unit"].to_numpy(), keys)
    assert m2.info["a"] == pytest.approx(0.3, abs=1e-9) and m2.info["b"] == pytest.approx(0.8, abs=1e-9)


def test_h08_f3_recovers_an_anomaly_line_with_the_spec_xbar(loaded):
    keys, x, z0, _ = _frame()
    xbar = O.xbar_table(x, keys["unit"].to_numpy(), keys["season_key"].to_numpy())
    y = z0 + 0.1 + 0.7 * (x - xbar)
    m = HK.fit_map("F3", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    assert m.info["a"] == pytest.approx(0.1, abs=1e-9) and m.info["b"] == pytest.approx(0.7, abs=1e-9)
    assert np.allclose(m.predict(x, z0, keys["unit"].to_numpy(), keys), y, atol=1e-9)


def test_h08_isotonic_maps_recover_monotone_maps_and_follow_the_spearman_sign(loaded):
    keys, x, z0, _ = _frame()
    u = keys["unit"].to_numpy()
    y = np.floor(x)                                         # increasing step function
    m = HK.fit_map("F2", x, y, z0, "identity", None, None, u, keys)
    assert np.allclose(m.predict(x, z0, u, keys), y, atol=1e-9)
    assert m.to_json()["info"]["iso"]["increasing"] is True
    yd = 20.0 - np.floor(x)                                 # decreasing
    md = HK.fit_map("F2", x, yd, z0, "identity", None, None, u, keys)
    assert md.to_json()["info"]["iso"]["increasing"] is False
    assert np.allclose(md.predict(x, z0, u, keys), yd, atol=1e-9)
    xbar = O.xbar_table(x, u, keys["season_key"].to_numpy())
    ya = z0 + np.tanh(x - xbar)                             # monotone in the anomaly
    m4 = HK.fit_map("F4", x, ya, z0, "identity", None, None, u, keys)
    assert np.allclose(m4.predict(x, z0, u, keys), ya, atol=1e-9)


def test_h08_f5_equals_the_hand_shrinkage_with_k_10_and_counts_the_pooled_units(loaded):
    keys, x, z0, rng = _frame()
    # two units with only 2 rows each: drop their other rows
    keep = np.ones(len(keys), dtype=bool)
    for name in ("u03", "u17"):
        idx = np.flatnonzero(keys["unit"].to_numpy() == name)
        keep[idx[2:]] = False
    keys = keys.loc[keep].reset_index(drop=True)
    x, z0 = x[keep], z0[keep]
    u = keys["unit"].to_numpy()
    slope = {name: 0.3 + 0.02 * i for i, name in enumerate(sorted(set(u)))}
    xbar = O.xbar_table(x, u, keys["season_key"].to_numpy())
    xa = x - xbar
    y = z0 + 0.05 + np.array([slope[v] for v in u]) * xa + rng.normal(scale=0.01, size=len(u))
    m = HK.fit_map("F5", x, y, z0, "identity", None, None, u, keys)
    per, (a, b), fb = O.f5_shrunk(xa, y - z0, u, k=10, min_rows=3)
    assert m.info["shrink_k"] == 10
    assert m.info["a_pool"] == pytest.approx(a, abs=1e-12) and m.info["b_pool"] == pytest.approx(b, abs=1e-12)
    assert m.info["units_pooled_fewer_than_min_rows"] == len(fb) == 2
    js = m.to_json()["per_unit"]
    for name, (au, bu) in per.items():
        if name in fb:
            assert name not in js
            continue
        assert js[name]["a"] == pytest.approx(au, abs=1e-12) and js[name]["b"] == pytest.approx(bu, abs=1e-12)
    want = z0 + np.array([per[v][0] for v in u]) + np.array([per[v][1] for v in u]) * xa
    assert np.allclose(m.predict(x, z0, u, keys), want, atol=1e-10)


def test_h08_not_calibratable_below_100_rows_or_3_groups(loaded):
    M = _maps()
    keys, x, z0, _ = _frame()
    u = keys["unit"].to_numpy()
    y = 1.0 + x
    for fam in ("F1", "F2", "F3", "F4", "F5"):
        HK.refuses(("needs >= 100", "calibratable", "rows"), HK.fit_map, fam, x[:99], y[:99], z0[:99], "identity",
                   None, None, u[:99], keys.iloc[:99])
        two = keys["group"].isin(["g0", "g1"]).to_numpy()
        assert two.sum() >= 100
        with pytest.raises(M.NotCalibratable):
            HK.fit_map(fam, x[two], y[two], z0[two], "identity", None, None, u[two], keys.loc[two])
    HK.fit_map("F1", x[:100], y[:100], z0[:100], "identity", None, None, u[:100], keys.iloc[:100])


@pytest.mark.parametrize("link,c,ub", [("identity", None, None), ("log_c", 0.7, None), ("arcsine", None, 1.0)])
def test_h08_link_round_trip(loaded, link, c, ub):
    M = _maps()
    y = np.linspace(0.0, 1.0, 1001)
    back = M.link_inverse(M.link_forward(y, link, c, ub), link, c, ub)
    assert np.max(np.abs(back - y)) <= 1e-12


def test_h08_l1_isotonic_is_monotone_and_l1_optimal(loaded):
    M = _maps()
    rng = np.random.default_rng(5)
    x = np.sort(rng.integers(0, 40, size=300)).astype(float)
    t = np.round(x / 4 + rng.normal(size=x.size), 1)
    xk, yk = HK.need(M, "l1_isotonic", "A6")(x, t, True)
    fit = np.interp(x, xk, yk)
    assert (np.diff(fit[np.argsort(x, kind="mergesort")]) >= -1e-12).all()
    ref = O.pav_l1(x, t, True)
    assert np.abs(t - fit).sum() == pytest.approx(np.abs(t - ref).sum(), abs=1e-9)


def test_h08_f0_is_native_and_has_no_link(loaded):
    keys, x, z0, _ = _frame()
    m = HK.fit_map("F0", x, x, z0, None, None, None, keys["unit"].to_numpy(), keys)
    assert np.array_equal(m.predict(x, z0, keys["unit"].to_numpy(), keys), x)
    assert m.to_json()["link"] is None
