"""T-F08 units -> grid points (SPEC_HUMAN_PARTB.txt 3.3): every slim unit must match one cell_id of the static
table (else refuse); a unit with no valid point inside the sea window is uncovered (all its rows NaN, product_cell and
src ""), and more uncovered bank units than max_uncovered_unit_share (1%, RF:26) refuses; the audit file
map_units_lead_<L>.json lists EVERY unit with box, i, j, lat, lon, substituted, dist_km, uncovered.
"""

import json

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF


def _refusals(geff):
    return (geff.FireGeffRefusal,) + FF.tool_refusals()


def test_f08_a_unit_missing_from_the_static_table_refuses(geff, raw_subsets, tmp_path):
    extra = [("greece_mainland_999_999", "greece_mainland", True)]
    toy = FF.era5_toy(tmp_path, raw_subsets, extra_units=extra)
    assert "greece_mainland_999_999" in set(toy.units["unit"])
    exc = FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))
    assert "greece_mainland_999_999" in str(exc) or "cell" in str(exc).lower() or "static" in str(exc).lower()


def test_f08_uncovered_units_above_the_share_refuse(geff, raw_subsets, tmp_path):
    """sea_window_steps 0: the synthetic coastal unit (nearest point sea) has no substitute -> uncovered; 1 of 4
    bank units is far above 1%."""
    toy = FF.era5_toy(tmp_path, raw_subsets, rival=FF.era5_rival(sea_window_steps=0))
    FF.refuses(geff.build, toy.ctx(), toy.rival, 0, "all", kinds=_refusals(geff))


def test_f08_uncovered_unit_rows_and_the_audit_file(geff, raw_subsets, tmp_path):
    toy = FF.era5_toy(tmp_path, raw_subsets, rival=FF.era5_rival(sea_window_steps=0, max_uncovered_unit_share=0.5))
    ctx = toy.ctx()
    frame = geff.build(ctx, toy.rival, 0, "all")
    sea = frame[frame["unit"] == "greece_mainland_syn_sea"]
    assert len(sea) and sea[FF.STATS].isna().all().all()
    assert (sea["product_cell"] == "").all() and (sea["src"] == "").all()
    assert (sea["info_end"].to_numpy(np.int64) == sea["time"].to_numpy(np.int64)).all()   # the rule value stays
    land = frame[frame["unit"] != "greece_mainland_syn_sea"]
    assert np.isfinite(land["x__fwi_mean"]).sum() == 3 * 23
    p = ctx.work_dir() / "map_units_lead_0.json"
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    units = FF.audit_units(doc)
    assert set(units) == set(toy.units["unit"])
    for u, rec in units.items():
        for field in ("box", "i", "j", "lat", "lon", "substituted", "dist_km", "uncovered"):
            assert field in rec, (u, field)
    assert bool(units["greece_mainland_syn_sea"]["uncovered"]) is True
    assert not any(bool(units[u]["uncovered"]) for u in units if u != "greece_mainland_syn_sea")
    assert all(units[u]["box"] == "greece_mainland" for u in units)
    la, lo = FF.unit_coords("greece_mainland_604_1146")
    assert float(units["greece_mainland_604_1146"]["lat"]) == pytest.approx(la, abs=1e-12)
    assert float(units["greece_mainland_604_1146"]["lon"]) == pytest.approx(lo, abs=1e-12)


def test_f08_the_window_rule_on_map_units(geff, raw_subsets):
    """map_units directly: window 2 substitutes the coastal unit, window 0 leaves it uncovered; land units never move."""
    lat, lon, valid = FF.grid_of(raw_subsets["era5_greece"])
    units = ["greece_mainland_syn_sea", "greece_mainland_603_1131", "greece_mainland_595_1135"]
    la = np.array([FF.unit_coords(u)[0] for u in units])
    lo = np.array([FF.unit_coords(u)[1] for u in units])
    for window in (0, 1, 2):
        m = {k: np.asarray(v) for k, v in geff.map_units(lat, lon, valid, la, lo, window).items()}
        for k in range(len(units)):
            e = FF.expected_point(lat, lon, valid, la[k], lo[k], window)
            assert bool(m["uncovered"][k]) == e["uncovered"], (units[k], window)
            assert bool(m["substituted"][k]) == e["substituted"], (units[k], window)
            if not e["uncovered"]:
                assert (int(m["i"][k]), int(m["j"][k])) == (e["i"], e["j"]), (units[k], window)
                assert float(m["dist_km"][k]) == pytest.approx(e["dist_km"], rel=1e-9)
        assert m["i"].dtype.kind == "i" and m["j"].dtype.kind == "i"
    e0 = FF.expected_point(lat, lon, valid, la[0], lo[0], 0)
    assert e0["uncovered"]
