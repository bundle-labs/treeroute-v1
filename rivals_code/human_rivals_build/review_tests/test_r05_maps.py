"""R05: calibration maps (rivals_human/maps.py) - fitted on the rows handed to them only, and a fair shape.

ISSUE 5 (fairness, low): F4 iso_anom fits iso(x - xbar) to link(y) - z0 (maps.py:296-300) but takes its direction
from Spearman(x, y) on the RAW values (maps.py:298). When x and y share a season cycle but their anomalies move
the other way, F4 is forced the wrong way and collapses to a flat map, so the rival loses a candidate it should have.
ISSUE 6 mechanism: the 100-row / 3-group floor (config.py:119-120) applies to EVERY map fit, including the guard fit
of a lead scored without the safety net (coral Outlook 365: 38 guard-fit rows in 11 groups).
"""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

from rivals_human import config as C
from rivals_human import maps as MP


def _seasonal(n_years=20, seed=0):
    rng = np.random.default_rng(seed)
    k = np.tile(np.arange(1, 13), n_years)
    s = np.sin(2 * np.pi * k / 12.0)
    e = rng.normal(0, 1, k.size)
    x = 10.0 * s + e                                  # index: seasonal + its own anomaly
    z0 = 5.0 * s                                      # the target's normal (same season cycle)
    y = z0 - 0.8 * e + rng.normal(0, 0.2, k.size)     # the ANOMALY relation is negative
    keys = pd.DataFrame({"unit": "u1", "group": np.where(np.arange(k.size) % 3 == 0, "g1",
                                                         np.where(np.arange(k.size) % 3 == 1, "g2", "g3")),
                         "time": np.arange(k.size), "issue": np.arange(k.size), "lead": 0, C.SEASON_KEY: k})
    return x, y, z0, keys


def test_r05_f4_construction_and_current_behaviour():
    """The toy: raw Spearman(x, y) > 0, anomaly Spearman < 0. Before the fix F4 fitted increasing and lost to F3
    (linear, sign free) by a wide margin; now it fits decreasing and stays close to F3."""
    x, y, z0, keys = _seasonal()
    m = MP.fit("F4", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    xa = x - m.xbar(keys["unit"].to_numpy(), keys[C.SEASON_KEY])
    assert spearmanr(x, y).correlation > 0 > spearmanr(xa, y - z0).correlation
    f3 = MP.fit("F3", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    mae = lambda mm: float(np.mean(np.abs(mm.predict(x, z0, keys["unit"].to_numpy(), keys) - y)))   # noqa: E731
    # since the issue-5 fix (2026-10-22) F4 takes the anomaly pair's direction: decreasing here, close to F3
    assert (not m.iso.increasing) and mae(m) <= 1.5 * mae(f3), (m.iso.increasing, mae(m), mae(f3))


# FIXED 2026-10-22 (was xfail strict): "ISSUE 5: F4's isotonic direction comes from Spearman(x, y) on raw values, not from the "
#   "anomaly pair it fits; a seasonal index with a negative anomaly relation gets a flat map"
def test_r05_f4_direction_follows_the_anomaly_relation():
    x, y, z0, keys = _seasonal()
    m = MP.fit("F4", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    xa = x - m.xbar(keys["unit"].to_numpy(), keys[C.SEASON_KEY])
    rho_anom = spearmanr(xa, y - z0).correlation
    f3 = MP.fit("F3", x, y, z0, "identity", None, None, keys["unit"].to_numpy(), keys)
    mae = lambda mm: float(np.mean(np.abs(mm.predict(x, z0, keys["unit"].to_numpy(), keys) - y)))   # noqa: E731
    assert m.iso.increasing == (rho_anom >= 0), "F4 fitted increasing on a decreasing anomaly relation"
    assert mae(m) <= 1.5 * mae(f3), (mae(m), mae(f3))


def test_r05_maps_see_only_the_rows_handed_to_them():
    """Calibration on train rows only: a map's predictions on new rows do not depend on those rows' labels (the
    map object never receives them) and refitting on the same fit rows is byte-identical."""
    x, y, z0, keys = _seasonal()
    fit = keys.index < 180
    sc = ~fit
    for fam in ("F1", "F2", "F3", "F4", "F5"):
        a = MP.fit(fam, x[fit], y[fit], z0[fit], "identity", None, None, keys["unit"].to_numpy()[fit],
                   keys.loc[fit].reset_index(drop=True))
        b = MP.fit(fam, x[fit], y[fit], z0[fit], "identity", None, None, keys["unit"].to_numpy()[fit],
                   keys.loc[fit].reset_index(drop=True))
        ks = keys.loc[sc].reset_index(drop=True)
        pa = a.predict(x[sc], z0[sc], ks["unit"].to_numpy(), ks)
        pb = b.predict(x[sc], z0[sc], ks["unit"].to_numpy(), ks)
        assert pa.tobytes() == pb.tobytes(), fam


def test_r05_floor_blocks_a_38_row_guard_fit():
    """The mechanism of ISSUE 6: 38 covered labelled rows in 11 groups (the coral Outlook's 365-day guard-fit rows,
    research_coral.md:136-138) are NOT calibratable for any family the Outlook lists."""
    rng = np.random.default_rng(1)
    n = 38
    x = rng.uniform(0, 4, n)
    y = rng.uniform(0, 100, n)
    keys = pd.DataFrame({"unit": ["v%d" % i for i in range(n)], "group": ["g%d" % (i % 11) for i in range(n)],
                         "time": np.arange(n), "issue": np.arange(n), "lead": 365, C.SEASON_KEY: (np.arange(n) % 12) + 1})
    for fam in ("F2", "F3", "F4"):
        with pytest.raises(MP.NotCalibratable):
            MP.fit(fam, x, y, np.zeros(n), "identity", None, None, keys["unit"].to_numpy(), keys)
