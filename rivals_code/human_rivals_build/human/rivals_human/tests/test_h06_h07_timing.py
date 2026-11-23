"""T-H06 (T1 from R8) and T-H07 (T2, tiers) (SPEC_HUMAN.txt 1.5; PLAN 3.3, R8).

Grid toy facts (derived.json R8): x1 steps 0, x2 steps 1; R17 start offset 0. T1 boundary = issue - S with S the max
steps of the rival's t1_kind_columns (all R8 entries when it names none). Table toy: boundary = issue +
plan.json max_feature_end_minus_issue_day (= -1). T2: target_obs_end <= latest label step - offset (t - 1 at the
nowcast, t - L at lead L; tables: strictly before the issue day).
"""

import json

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK


def _keys(h, slim_dirs, lead, s="refit", n=200):
    sl = HK.slim_lead(h, slim_dirs[lead])
    return sl.keys(s).iloc[:n].reset_index(drop=True)


def _rival(t1):
    return {"id": "toy_t", "kind": "I", "t1_kind_columns": list(t1)}


def _run_copy_with_r8(h, column: str, steps: int):
    """A copy of the toy run whose derived.json says R8[column].steps = steps (the original is never touched)."""
    from rivals.tests import toy_runs as T
    dest = T.copy_run(h.toy, "r8_%s_%d" % (column, steps))
    dp = dest / "derived.json"
    d = HK.read_json(dp)
    d["R8"]["value"][column]["steps"] = int(steps)
    HK.move_aside(dp, h.base / "_moved_by_tests")
    dp.write_text(json.dumps(d, indent=1), encoding="utf-8")
    LY, H = HK.common_modules(h.config)
    return H.Run(dest)


# ------------------------------------------------------------------------------------------ T-H06
def test_h06_r8_facts_of_the_toy(grid_human):
    r8 = grid_human.toy.derived()["R8"]["value"]
    assert int(r8["x1"]["steps"]) == 0 and int(r8["x2"]["steps"]) == 1


def test_h06_a_target_month_driver_passes_on_steps_0_and_refuses_on_steps_1(grid_human, grid_slim):
    run = grid_human.h_run()
    k = _keys(grid_human, grid_slim, 0)
    info = k["issue"].to_numpy(np.int64)                     # a driver of the issue step itself
    toe = np.full(len(k), np.nan)
    tm = HK.timing(run, _rival(["x1"]), 0)
    HK.check_tier_timing("P", tm, k, info, toe)
    run1 = _run_copy_with_r8(grid_human, "x1", 1)
    tm1 = HK.timing(run1, _rival(["x1"]), 0)
    HK.refuses("T1", HK.check_tier_timing, "P", tm1, k, info, toe)
    HK.check_tier_timing("P", tm1, k, info - 1, toe)          # one step older passes there


def test_h06_the_kind_columns_decide_s(grid_human, grid_slim):
    run = grid_human.h_run()
    k = _keys(grid_human, grid_slim, 0)
    info = k["issue"].to_numpy(np.int64)
    toe = np.full(len(k), np.nan)
    HK.refuses("T1", HK.check_tier_timing, "P", HK.timing(run, _rival(["x2"]), 0), k, info, toe)
    HK.refuses("T1", HK.check_tier_timing, "P", HK.timing(run, _rival([]), 0), k, info, toe)   # S = max of all = 1
    HK.check_tier_timing("P", HK.timing(run, _rival([]), 0), k, info - 1, toe)
    HK.refuses(("not R8", "t1_kind_columns"), HK.timing, run, _rival(["no_such_column"]), 0)


def test_h06_table_boundary_is_issue_minus_1(table_human, table_slim):
    run = table_human.h_run()
    assert int(run.plan["max_feature_end_minus_issue_day"]["0"]) == -1
    for lead in table_human.leads:
        k = _keys(table_human, table_slim, lead, n=50)
        toe = np.full(len(k), np.nan)
        tm = HK.timing(run, _rival([]), lead)
        HK.refuses("T1", HK.check_tier_timing, "P", tm, k, k["issue"].to_numpy(np.int64), toe)
        HK.check_tier_timing("P", tm, k, k["issue"].to_numpy(np.int64) - 2, toe)
        HK.check_tier_timing("P", tm, k, k["issue"].to_numpy(np.int64) - 1, toe)


# ------------------------------------------------------------------------------------------ T-H07
def test_h07_a_p_row_reading_the_target_month_refuses_and_passes_as_tier_a(grid_human, grid_slim):
    run = grid_human.h_run()
    k = _keys(grid_human, grid_slim, 0)
    t = k["time"].to_numpy(np.int64)
    info = k["issue"].to_numpy(np.int64) - 1
    tm = HK.timing(run, _rival(["x1"]), 0)
    HK.refuses("T2", HK.check_tier_timing, "P", tm, k, info, t.astype(float))
    HK.check_tier_timing("P", tm, k, info, (t - 1).astype(float))   # t - 1 is the step hist_last_1 reads
    HK.check_tier_timing("A", tm, k, info, t.astype(float))
    HK.refuses(("tier-A", "neither", "registry"), HK.check_tier_timing, "A", tm, k, info, (t - 1).astype(float))
    HK.refuses("T2", HK.check_tier_timing, "X", tm, k, info, t.astype(float))
    HK.refuses("T2", HK.check_tier_timing, "L", tm, k, info, t.astype(float))


def test_h07_lead_6_t2_step_is_t_minus_6(grid_human, grid_slim):
    run = grid_human.h_run()
    k = _keys(grid_human, grid_slim, 6)
    t = k["time"].to_numpy(np.int64)
    info = k["issue"].to_numpy(np.int64)
    tm = HK.timing(run, _rival(["x1"]), 6)
    HK.check_tier_timing("L", tm, k, info, (t - 6).astype(float))
    HK.refuses("T2", HK.check_tier_timing, "L", tm, k, info, (t - 1).astype(float))


def test_h07_table_t2_is_strictly_before_the_issue_day(table_human, table_slim):
    run = table_human.h_run()
    k = _keys(table_human, table_slim, 0, n=50)
    iss = k["issue"].to_numpy(np.int64)
    tm = HK.timing(run, _rival([]), 0)
    HK.check_tier_timing("P", tm, k, iss - 2, (iss - 1).astype(float))
    HK.refuses("T2", HK.check_tier_timing, "P", tm, k, iss - 2, iss.astype(float))


def test_h07_uncovered_rows_are_not_judged(grid_human, grid_slim):
    run = grid_human.h_run()
    k = _keys(grid_human, grid_slim, 0)
    t = k["time"].to_numpy(np.int64)
    cov = np.zeros(len(k), dtype=bool)
    tm = HK.timing(run, _rival(["x1"]), 0)
    HK.check_tier_timing("P", tm, k, k["issue"].to_numpy(np.int64) + 5, t.astype(float), covered=cov)


def test_h07_a_shifted_label_m_runner_refuses(grid_human, grid_slim):
    """PLAN R8: an M runner reporting that it read the target step is refused (at tune, where its predictions are
    first made)."""
    from rivals_human.tests import toy_products as TP
    v = HK.variant_config(grid_human, "shifted_m", TP.grid_registry(grid_human.package, "shifted_m"))
    out = HK.init(v)
    HK.refuses("T2", HK.tune, v, out)
