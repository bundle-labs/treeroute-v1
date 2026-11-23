"""T-H09 the pick (SPEC_HUMAN.txt 1.6; HQ6 a, Q2.HQ10): the lowest inner MAE wins; ties follow the fixed order (stat
order, family F0..F6, R22 link order); a forecast-only product is picked on the guard rows of its lowest covered
lead; the pick is pinned at every lead and refit per lead."""

import numpy as np
import pytest

from rivals_human.tests import hooks as HK


def test_h09_candidates_come_in_the_fixed_order():
    rival = {"id": "r", "kind": "N", "stats": ["x__b", "x__a"], "families": ["F0", "F1", "F3"]}
    got = [(c["stat"], c["family"], c["link"]) for c in HK.candidates(rival, ["identity", "log_c"])]
    want = [("x__b", "F0", None), ("x__b", "F1", "identity"), ("x__b", "F1", "log_c"), ("x__b", "F3", "identity"),
            ("x__b", "F3", "log_c"), ("x__a", "F0", None), ("x__a", "F1", "identity"), ("x__a", "F1", "log_c"),
            ("x__a", "F3", "identity"), ("x__a", "F3", "log_c")]
    assert got == want


def _rec(cand, order, mae, status="ok"):
    return {"candidate": cand, "order": list(order), "status": status, "pick_mae": mae}


def test_h09_lowest_mae_wins_and_ties_follow_the_fixed_order():
    recs = [_rec("c", [1, 3, 0], 0.5), _rec("a", [0, 0, 0], 0.7), _rec("b", [0, 1, 1], 0.5),
            _rec("d", [0, 1, 0], 0.9), _rec("e", [0, 2, 0], float("nan"), status="not_calibratable")]
    assert HK.pick_of(recs)["candidate"] == "b"            # 0.5 twice: order [0,1,1] before [1,3,0]
    assert HK.pick_of(list(reversed(recs)))["candidate"] == "b"
    assert HK.pick_of([_rec("x", [0, 0, 0], 1.0, "not_calibratable")]) is None


def test_h09_forecast_only_product_is_picked_on_its_lowest_covered_lead_guard_rows(table_flow):
    p = HK.picks(table_flow.out)["picks"]["toy_outlook"]
    assert p["status"] == "ok"
    assert int(p["pick_lead"]) == 183 and p["pick_set"] == "guard"
    files = [t for t in sorted((table_flow.out / "trials" / "toy_outlook").glob("*.json"))
             if not t.name.endswith(".map.json")]          # integration: trial records only, as the other T-H09 tests
    assert files
    for f in files:
        trials = HK.read_json(f)
        assert int(trials["lead"]) == 183 and trials["fit_set"] == "guardfit" and trials["score_set"] == "guard"


def test_h09_below_the_row_floor_a_map_rival_is_not_calibratable_and_disclosed(table_flow):
    """The engine's table toy has 73 tune rows (< 100, Q2.HQ9): toy_dhw gets no pick, no row, and the reason."""
    p = HK.picks(table_flow.out)["picks"]["toy_dhw"]
    assert p["status"] == "not_calibratable" and "100" in p["reason"], p
    for L in table_flow.h.leads:
        assert not (HK.lead_dir(table_flow.out, L) / "preds_toy_dhw.parquet").is_file()


def test_h09_nowcast_rivals_are_picked_on_inner_rows(grid_flow):
    for rid in ("toy_lag1", "toy_idx", "toy_noise"):
        p = HK.picks(grid_flow.out)["picks"][rid]
        assert int(p["pick_lead"]) == 0 and p["pick_set"] == "inner", rid


def test_h09_the_pick_is_pinned_and_refit_per_lead(grid_flow):
    grid_flow.ok("refit 0", "refit 6", "refit 12")
    out = grid_flow.out
    p = HK.picks(out)["picks"]["toy_idx"]
    maps = {}
    for L in (0, 6, 12):
        m = HK.read_json(HK.lead_dir(out, L) / "map_toy_idx.json")
        assert m["candidate"]["stat"] == p["stat"] and m["candidate"]["family"] == p["family"]
        assert m["candidate"]["link"] == p["link"]
        assert m["refit"]["family"] == p["family"]
        maps[L] = m["refit"]
    assert maps[0] != maps[6] and maps[6] != maps[12], "the pinned candidate was not refit per lead"
    trials = sorted((out / "trials" / "toy_idx").glob("*.json"))
    assert all(int(HK.read_json(t)["lead"]) == 0 for t in trials if not t.name.endswith(".map.json"))


def test_h09_the_pick_is_the_lowest_trial_mae(grid_flow):
    out = grid_flow.out
    for rid in ("toy_lag1", "toy_idx"):
        recs = [HK.read_json(t) for t in sorted((out / "trials" / rid).glob("*.json"))
                if not t.name.endswith(".map.json")]
        ok = [r for r in recs if r["status"] == "ok"]
        best = min(float(r["pick_mae"]) for r in ok)
        p = HK.picks(out)["picks"][rid]
        assert float(p["pick_mae"]) == best
