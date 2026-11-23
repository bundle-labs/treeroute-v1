"""T-H18 PM2.5 readers (SPEC_HUMAN.txt section 4; adapters/pm25_reanalysis.py): bilinear interpolation on a known
field equals the hand computation, with the EAC4 axes (lon 0..359.25 wrapped, lat north -> south) and the MERRA-2
axes (lon -180..179.375, lat ascending); product month m = t-1 gives tier-P rows and m = t tier-A rows under the
tool's own timing rules; EAC4 without its manifest refuses with the plain D1 line, through the tool's own adapter
context."""

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import oracles as O

D1_LINE = "D1 (CAMS EAC4) is not on disk"


def _pm():
    return HK.tool("pm25_reanalysis")


@pytest.mark.parametrize("axes", ["eac4", "merra2"])
def test_h18_bilinear_equals_the_hand_computation(axes):
    PM = _pm()
    if axes == "eac4":
        lat = np.arange(90.0, -90.01, -0.75)
        lon = np.arange(0.0, 360.0, 0.75)
    else:
        lat = np.arange(-90.0, 90.01, 0.5)
        lon = np.arange(-180.0, 180.0, 0.625)
    rng = np.random.default_rng(8)
    field = rng.uniform(1.0, 50.0, size=(lat.size, lon.size))
    G = HK.need(PM, "Grid", "C1")(lat, lon)
    q_lat = np.array([12.34, -45.6, 0.1, 60.0, -10.0, 33.3])
    q_lon = np.array([45.67, -0.2, 359.9, 179.9, -179.95, 0.3])     # seams of both conventions
    w = G.weights(q_lat, q_lon)
    got = G.interpolate(G.orient(field), w)
    want = [O.bilinear(lat, lon, field, a, b) for a, b in zip(q_lat, q_lon)]
    assert np.allclose(got, want, rtol=0, atol=1e-10)


def test_h18_product_month_t_minus_1_is_p_and_t_is_a(grid_human, grid_slim):
    PM = _pm()
    run = grid_human.h_run()
    sl = HK.slim_lead(grid_human, grid_slim[0])
    keys = sl.keys("refit").iloc[:300].reset_index(drop=True)
    rival = {"id": "pm", "kind": "N", "t1_kind_columns": []}
    tm = HK.timing(run, rival, 0)
    for offset, ok_tier, bad_tier in ((-1, "P", "A"), (0, "A", "P")):
        m, read = HK.need(PM, "product_months", "C1")(keys, {"month_offset": offset, "placebo_shift_years": 0})
        assert np.array_equal(m, keys["issue"].to_numpy(np.int64) + offset)
        HK.check_tier_timing(ok_tier, tm, keys, read, read.astype(float))
        HK.refuses(("T1", "T2", "tier-A", "neither"), HK.check_tier_timing, bad_tier, tm, keys, read,
                   read.astype(float))


def test_h18_the_placebo_never_reads_a_later_year():
    PM = _pm()
    keys = pd.DataFrame({"issue": np.array([2015 * 12 + 3, 2016 * 12 + 1])})
    m, read = PM.product_months(keys, {"month_offset": -1, "placebo_shift_years": 4})
    assert np.array_equal(read, m - 48) and (read < m).all()


def test_h18_eac4_without_its_manifest_refuses_with_the_d1_line(grid_human, grid_slim):
    """The real registry entry of eac4_lag1 (registry/pm25.yaml), put on the grid toy with the toy's package name and
    a product registry whose EAC4 manifest does not exist (the state before D1 is downloaded)."""
    reg_pm = HK.read_yaml(HK.HUMAN_ROOT / "registry" / "pm25.yaml")
    eac4 = dict(next(r for r in reg_pm["rivals"] if r["id"] == "eac4_lag1"))
    eac4["t1_kind_columns"] = []
    eac4["stats"] = ["x__" + s if not str(s).startswith("x__") else s for s in eac4["stats"]]
    eac4["slim_extra_columns"] = ["x__x1"]
    leads = {L: ({"tier": "P"} if L == 0 else {"tier": "none", "reason": "toy"}) for L in grid_human.leads}
    eac4["leads"] = leads
    pid = eac4["products"][0]
    reg = {"format": "human-registry/1", "package": grid_human.package, "rivals": [eac4]}
    v = HK.variant_config(grid_human, "eac4", reg)
    prods = HK.read_yaml(v.roots["on_disk_products"])
    prods["products"][pid] = {"path": str(v.base / "_products" / pid), "manifest":
                              str(v.base / "_products" / pid / "not_downloaded" / "product_manifest.json"),
                              "waiting_line": "D1 (CAMS EAC4) is not on disk: run DOWNLOAD_COMMANDS.md 2.2 first",
                              "licence": "CAMS", "source": "toy test"}
    from rivals_human.tests import toy_products as TP
    TP.write_yaml(v.roots["on_disk_products"], prods)
    ctx = HK.adapter_ctx(v, "eac4_lag1", 0, "all")
    PM = _pm()
    ok, line = HK.need(PM, "availability", "C1")(ctx, eac4)
    assert ok is False and D1_LINE in line
    HK.refuses(D1_LINE, PM.build, ctx, eac4, 0, "all")
    HK.refuses(D1_LINE, HK.adapt, v, "eac4_lag1", 0)
    # review B issue 9: human_board.json is write-once, so init refuses while this non-optional P rival waits,
    # unless the owner passes --allow-waiting (then lock --without ... --decision)
    from rivals_human import board as B
    HK.refuses(("waiting", "allow-waiting"), B.init, str(v.run), str(v.config))
    out = B.init(str(v.run), str(v.config), allow_waiting=True)
    doc = HK.read_json(out / "human_board.json")
    assert doc["rivals"]["eac4_lag1"]["status"] == "waiting" and doc["allow_waiting"] is True
