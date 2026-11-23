"""The hand computations of oracles.py are themselves checked before any tool test leans on them (SPEC_HUMAN.txt 7):
against a closed form, a brute force, or the LIVE engine's own saved columns of the toy runs.

The persistence oracle is the spec's recipe of 1.10 (persistence from x__hist_last_1, damped persistence with the
engine's metrics functions) applied at a lead >= 1, where the run saved base__persistence and
base__damped_persistence: it must reproduce them byte for byte, which is the parity proof the tool's refs.py must
pass before it writes any nowcast reference row.
"""

import itertools
from pathlib import Path
import math

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O


# ------------------------------------------------------------------------------------------ coral rule
def test_dhw_oracle_closed_form():
    """A flat HotSpot of 1.5 for 84 days -> DHW = 84 x 1.5 / 7 = 18; a HotSpot of 0.9 counts nothing."""
    mmm = 28.0
    d_star = 1000
    sst = {d: mmm + 1.5 for d in range(d_star - 200, d_star + 1)}
    dhw, baa = O.dhw_baa(sst, mmm, d_star)
    assert dhw == pytest.approx(18.0, abs=1e-12)
    assert baa == 4.0
    sst = {d: mmm + 0.9 for d in range(d_star - 200, d_star + 1)}
    dhw, baa = O.dhw_baa(sst, mmm, d_star)
    assert dhw == 0.0 and baa == 1.0                       # Watch: 0 < HS < 1


def test_dhw_oracle_window_ends_at_dstar_and_missing_day_is_nan():
    mmm = 28.0
    d_star = 500
    sst = {d: mmm for d in range(d_star - 200, d_star + 30)}
    sst[d_star + 1] = mmm + 5.0                            # after d*: never read
    sst[d_star - 84] = mmm + 5.0                           # one day before the 84-day window: not in DHW(d*)
    dhw, _ = O.dhw_baa(sst, mmm, d_star)
    assert dhw == 0.0
    sst[d_star - 83] = mmm + 2.0                           # first day of the window
    assert O.dhw_at(sst, mmm, d_star) == pytest.approx(2.0 / 7.0, abs=1e-15)
    del sst[d_star - 10]
    dhw, baa = O.dhw_baa(sst, mmm, d_star)
    assert math.isnan(dhw) and math.isnan(baa)


def test_baa_levels_in_order():
    assert O.baa_level(-0.1, 10) == 0
    assert O.baa_level(0.0, 10) == 0
    assert O.baa_level(0.5, 10) == 1                       # Watch even with a high DHW (alerts need HS >= 1)
    assert O.baa_level(1.0, 0.5) == 2
    assert O.baa_level(1.0, 4.0) == 3
    assert O.baa_level(1.2, 7.99) == 3
    assert O.baa_level(1.2, 8.0) == 4
    assert O.baa_level(3.0, 20.0) == 4                     # NOAA levels 5-7 merged into 4


# ------------------------------------------------------------------------------------------ bilinear
def test_bilinear_oracle_exact_on_a_plane_any_axis_order():
    lat_desc = np.arange(90.0, -90.01, -0.75)               # EAC4: north -> south
    lon = np.arange(0.0, 360.0, 0.75)
    f = 3.0 + 0.5 * lat_desc[:, None] + 0.0 * lon[None, :]
    assert O.bilinear(lat_desc, lon, f, 12.3, 45.6) == pytest.approx(3.0 + 0.5 * 12.3, abs=1e-12)
    lat_asc = np.arange(-90.0, 90.01, 0.5)                  # MERRA-2: ascending, lon -180..179.375
    lon_m = np.arange(-180.0, 180.0, 0.625)
    g = 1.0 + 0.25 * lon_m[None, :] + 0.1 * lat_asc[:, None]
    assert O.bilinear(lat_asc, lon_m, g, -33.3, 100.1) == pytest.approx(1.0 + 0.25 * 100.1 + 0.1 * -33.3, abs=1e-12)


def test_bilinear_oracle_wraps_longitude():
    lat = np.array([-1.0, 1.0])
    lon = np.arange(0.0, 360.0, 0.75)
    f = np.zeros((2, lon.size))
    f[:, -1] = 10.0                                         # the column at 359.25
    f[:, 0] = 20.0                                          # the column at 0.0 (= 360)
    v = O.bilinear(lat, lon, f, 0.0, 359.625)               # half way between 359.25 and 360
    assert v == pytest.approx(15.0, abs=1e-12)
    assert O.bilinear(lat, lon, f, 0.0, -0.375) == pytest.approx(15.0, abs=1e-12)


# ------------------------------------------------------------------------------------------ L1 isotonic
def _l1(y, f):
    return float(np.abs(np.asarray(y) - np.asarray(f)).sum())


def test_pav_l1_is_monotone_and_optimal_against_brute_force():
    rng = np.random.default_rng(7)
    for trial in range(30):
        n = 6
        x = np.sort(rng.integers(0, 4, size=n)).astype(float)
        y = rng.integers(0, 5, size=n).astype(float)
        fit = O.pav_l1(x, y, True)
        order = np.argsort(x, kind="mergesort")
        assert (np.diff(fit[order]) >= -1e-12).all()
        best = math.inf
        levels = sorted(set(y.tolist()))
        groups = sorted(set(x.tolist()))
        for vals in itertools.product(levels, repeat=len(groups)):
            if any(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
                continue
            m = dict(zip(groups, vals))
            best = min(best, _l1(y, [m[v] for v in x]))
        assert _l1(y, fit) == pytest.approx(best, abs=1e-12), (x, y, fit)


def test_pav_l1_decreasing():
    x = np.arange(9.0)
    y = -np.arange(9.0)
    assert np.allclose(O.pav_l1(x, y, False), y)


# ------------------------------------------------------------------------------------------ F5 by hand
def test_f5_oracle_matches_least_squares_and_the_shrink_formula():
    rng = np.random.default_rng(3)
    units = np.repeat(["u%d" % i for i in range(5)], [12, 8, 2, 30, 5])
    xa = rng.normal(size=units.size)
    r = 0.2 + 0.6 * xa + rng.normal(scale=0.1, size=units.size)
    per, (a, b), fb = O.f5_shrunk(xa, r, units, k=10, min_rows=3)
    A = np.c_[np.ones(units.size), xa]
    coef = np.linalg.lstsq(A, r, rcond=None)[0]
    assert (a, b) == pytest.approx((coef[0], coef[1]), abs=1e-12)
    assert fb == ["u2"] and per["u2"] == (a, b)
    m = units == "u3"
    cu = np.linalg.lstsq(A[m], r[m], rcond=None)[0]
    n = int(m.sum())
    assert per["u3"][0] == pytest.approx((n * cu[0] + 10 * a) / (n + 10), abs=1e-12)
    assert per["u3"][1] == pytest.approx((n * cu[1] + 10 * b) / (n + 10), abs=1e-12)


# ------------------------------------------------------------------------------------------ defo pieces
def test_forest_mask_and_quantity_oracles():
    tc = np.array([[50, 29, 80], [30, 90, 100]])
    dm = np.array([[1, 1, 2], [1, 1, 1]])
    ly = np.array([[0, 0, 0], [5, 11, 12]])
    f = O.forest_mask(tc, dm, ly, 2011)
    assert f.tolist() == [[True, False, False], [False, False, True]]
    p = np.array([0.1, 0.2, 0.7])
    e = O.vt0007_quantity(p, 2.0)
    assert e.sum() == pytest.approx(2.0, abs=1e-12)          # the total is the quantity ...
    assert e.tolist() == pytest.approx([1 / 3, 2 / 3, 1.0])  # ... with the top pixel capped at 1 (s = 10/3)
    assert O.vt0007_quantity(p, 0.5).tolist() == pytest.approx([0.05, 0.1, 0.35])
    assert O.vt0007_quantity(p, 5.0).tolist() == [1.0, 1.0, 1.0]
    cv = O.cell_value(np.array([0.2, 0.4, 1.0]), np.array([0, 0, 1]), {0: 2.0, 1: 4.0})  # (0.2+0.4)/2, 1/4
    assert cv == {0: pytest.approx(0.3), 1: pytest.approx(0.25)}


# ------------------------------------------------------------------------------------------ persistence (engine)
def _grid_facts(toy):
    d = toy.derived()
    offset = int(d["R17"]["value"]["start_offset_steps"])
    spy = int(d["R2"]["value"]["steps_per_year"])           # derived R2: season kind and steps per year
    legal = toy.legal()
    return offset, spy, legal


def _saved_base(toy, lead):
    return HK.read_parquet(toy.saved_test_preds(lead), ["unit", "time", "lead", "base__persistence",
                                                       "base__damped_persistence"])


def test_export_history_is_float32_so_persistence_parity_needs_the_float64_labels(grid_toy, grid_export):
    """FINDING (spec 1.10 reads persistence from x__hist_last_1): the export stores every x__ column as float32
    (common export), so clip(x__hist_last_1) can never equal the saved float64 base__persistence byte for byte; the
    parity recipe must read the float64 label at the T2 step (slim train y; the saved lead-0 test y after the lock).
    Pinned here so the tool's parity proof is built on the labels, not on x__hist_last_1."""
    import pyarrow.parquet as pq
    f = sorted((grid_export[6] / "test").glob("*.parquet"))[0]
    assert str(pq.read_schema(str(f)).field("x__hist_last_1").type) == "float"
    offset, spy, legal = _grid_facts(grid_toy)
    via_hist = O.persistence_parity(grid_toy.run, grid_export, 6, offset, spy, legal, grid_toy.cuts(6)["fit_cut"])
    saved = _saved_base(grid_toy, 6)
    j = saved.merge(via_hist, on=["unit", "time", "lead"], validate="one_to_one")
    d = np.abs(j["persistence"].to_numpy(np.float64) - j["base__persistence"].to_numpy(np.float64))
    assert np.nanmax(d) < 1e-5                          # float32 rounding only
    assert j["persistence"].to_numpy(np.float64).tobytes() != j["base__persistence"].to_numpy(np.float64).tobytes()


@pytest.mark.parametrize("lead", [6, 12])
def test_persistence_oracle_reproduces_the_runs_saved_columns_byte_for_byte(grid_toy, grid_export, lead):
    offset, spy, legal = _grid_facts(grid_toy)
    fit_cut = grid_toy.cuts(lead)["fit_cut"]
    labels = O.label_table(grid_export[0], HK.read_parquet(grid_toy.saved_test_preds(0), ["unit", "time", "y"]))
    got = O.persistence_parity(grid_toy.run, grid_export, lead, offset, spy, legal, fit_cut, "lead0_refit",
                               labels=labels)
    saved = _saved_base(grid_toy, lead)
    j = saved.merge(got, on=["unit", "time", "lead"], how="left", validate="one_to_one")
    assert len(j) == len(saved) == len(got)
    a = j["persistence"].to_numpy(np.float64)
    b = j["base__persistence"].to_numpy(np.float64)
    assert a.tobytes() == b.tobytes(), "persistence differs on %d rows" % int((a != b).sum())
    a = j["damped_persistence"].to_numpy(np.float64)
    b = j["base__damped_persistence"].to_numpy(np.float64)
    if a.tobytes() != b.tobytes():
        alt = O.persistence_parity(grid_toy.run, grid_export, lead, offset, spy, legal, fit_cut, "lead_refit",
                                   labels=labels)
        j2 = saved.merge(alt, on=["unit", "time", "lead"], how="left", validate="one_to_one")
        same_alt = j2["damped_persistence"].to_numpy(np.float64).tobytes() == b.tobytes()
        pytest.fail("damped persistence differs on %d rows (max |d| %.3g); the lead's own refit rows %s"
                    % (int((~np.isclose(a, b, rtol=0, atol=0)).sum()), float(np.nanmax(np.abs(a - b))),
                       "DO reproduce it" if same_alt else "do not either"))


def table_site_of(table_toy):
    """row id -> site from the toy package's own data (the export does not carry the site of a train visit)."""
    t = HK.read_parquet(Path(table_toy.package) / "data" / "lead_0.parquet", ["row_id", "site"])
    return dict(zip(t["row_id"].astype(str), t["site"].astype(str)))


def test_table_toy_export_units_are_visits_without_a_site_key(table_toy, table_export):
    """FINDING (spec 1.10 coral last visit: 'site key = the part of the unit id before |'): in the engine's table toy
    the export unit is the visit row id (no '|') and the site is a separate package column that neither the export's
    units.parquet nor its train rows carry; only the saved test rows have it. A generic last-visit row therefore needs
    the site key from the run (saved test rows) and the package (train visits), not from the unit id. Pinned."""
    units = HK.read_parquet(table_export[0] / "units.parquet")
    assert "site" not in units.columns
    assert not units["unit"].astype(str).str.contains("|", regex=False).any()
    saved = HK.read_parquet(table_toy.saved_test_preds(0))
    assert "site" in saved.columns


def test_last_visit_oracle_reproduces_the_table_runs_saved_persistence(table_toy, table_export):
    legal = table_toy.legal()
    train0 = O.read_export_part(table_export[0], "train", ["unit", "time", "y"])
    test0 = HK.read_parquet(table_toy.saved_test_preds(0), ["unit", "time", "y"])
    labels = pd.concat([train0, test0], ignore_index=True)
    site_of = table_site_of(table_toy)
    for lead in [L for L in table_toy.leads if L > 0]:
        saved = HK.read_parquet(table_toy.saved_test_preds(lead), ["unit", "time", "issue", "lead",
                                                                   "base__persistence"])
        got = O.last_visit(labels, saved, legal, site_of=site_of)
        b = saved["base__persistence"].to_numpy(np.float64)
        assert got.tobytes() == b.tobytes(), "lead %d: last visit differs on %d rows" % (
            lead, int((~((got == b) | (np.isnan(got) & np.isnan(b)))).sum()))
