"""io science against the APPROVED shapes of treeroute/_proposed/common.py.

Engine code may not import the proposed modules (G-IMPORT), so the io bodies read their inputs by
attribute. This test builds the real proposed dataclasses and enums and passes them in. It runs in a
fresh interpreter, so no treeroute._proposed module is ever loaded into the pytest process (a loaded
proposed module makes the manifest refuse, test_fingerprint_manifest.py).
"""

import json

from conftest import run_python

CODE = r"""
import datetime, json
import numpy as np
import pandas as pd
from treeroute._proposed import common as C
from treeroute.io.steps import step_index, step_bounds, build_dense_grid, predecessor_index
from treeroute.io.sentinel import mask_sentinels
from treeroute.io.apply import (apply_lags, apply_verdicts, apply_freezes, history_block,
                                history_column_names, features_at_issue_step)
from treeroute.io.aggregate import aggregate_time
from treeroute.io.joins import join_coarser_column
from treeroute.timing import compute_lag

res = {}
monthly = C.Cadence(C.CadenceKind.REGULAR, 1, C.StepUnit.MONTH)
comp = C.Cadence(C.CadenceKind.COMPOSITE_OF_YEAR, composites_per_year=23, composite_days=16)
steps = step_index({"yr": np.array([2010, 2010]), "mo": np.array([1, 2])},
                   {"yr": C.CalendarPart.YEAR, "mo": C.CalendarPart.MONTH}, monthly)
res["monthly"] = steps.tolist()
res["comp"] = step_index({"yr": np.array([2010]), "doy": np.array([353])},
                         {"yr": C.CalendarPart.YEAR, "doy": C.CalendarPart.DAY_OF_YEAR}, comp).tolist()
first, last = step_bounds(np.array(res["comp"]), comp)
res["comp_days"] = int(last[0] - first[0] + 1)

def facts(name, role, fills=(-32768.0,)):
    return C.ColumnFacts(
        name=name, dtype="float32", units="1", cadence=monthly, scope=C.Scope.UNIT,
        stamp=C.Stamp.PERIOD_END, window=C.Window(1, C.StepUnit.MONTH, C.Align.BACKWARD),
        legal_range=(0.0, float("inf")), fill_values=tuple(fills), near_sentinel_optout=False,
        product_family=None, lineage_assimilates=(), lineage_trained_on=(), sum_group=None,
        content_epoch=None, observed_through=None, release_date=None, snapshot_date=None,
        baseline_period=None, absent_groups={}, derived_from=(), operation=None, reads_target=False,
        fact_status=C.FactStatus.UNVERIFIED, reviewed_by=None, role=role,
        co_measured_with_target=None, co_measured_part=None, data_selected=None)

frame = pd.DataFrame({"u": ["a", "a"], "x": np.array([-32768.0, 2.0], dtype=np.float32),
                      "y": np.array([0.1, 0.2])})
out, rep = mask_sentinels(frame, {"u": facts("u", C.Role.KEY_UNIT), "x": facts("x", C.Role.DRIVER),
                                  "y": facts("y", C.Role.TARGET, fills=())})
res["masked"] = dict(rep.masked)

lagged = apply_lags(out[["x"]], np.array([0, 0]), steps,
                    {"x": C.Lag(column="x", steps=1, column_cadence=monthly, floor_reason=None)}, monthly)
store_comp = C.Cadence(C.CadenceKind.COMPOSITE_OF_YEAR, 16, C.StepUnit.DAY, composites_per_year=23)
comp_lag = apply_lags(pd.DataFrame({"x": [1.0, 2.0]}), np.array([0, 0]), np.array([2010 * 23 + 1, 2010 * 23 + 2]),
                      {"x": C.Lag(column="x", steps=1, column_cadence=store_comp, floor_reason=None)}, comp)
res["comp_lag"] = [None if np.isnan(v) else float(v) for v in comp_lag["x"]]
res["lagged"] = [None if np.isnan(v) else float(v) for v in lagged["x"]]

sets = apply_verdicts(("x", "y"),
                      {"x": C.VerdictDecl("x", C.Verdict.KEEP, "reviewed", None, 1),
                       "y": C.VerdictDecl("y", C.Verdict.BAN, "label", C.BanReason.LABEL, 1)},
                      {"x": C.Role.DRIVER, "y": C.Role.TARGET})
res["tree"] = list(sets.tree_features)

frozen = apply_freezes(pd.DataFrame({"z": [1.0, 2.0]}), np.array([0, 0]),
                       {"z": np.array([C.Day(5), C.Day(6)])}, {"z": C.Day(6)})
res["frozen"] = frozen["z"].tolist()

grid = build_dense_grid(np.array(["a", "a", "b", "b"], dtype=object), np.array(["g"] * 4, dtype=object),
                        np.array([1, 2, 1, 2]), (C.Step(1), C.Step(2)))
res["grid"] = [list(grid.unit_ids), grid.first_step, grid.n_steps]
spec = C.HistorySpec(columns=(), last_values=1, trailing_steps=(2,), trailing_days=(365, 1826),
                     all_history_mean=True, start_offset_steps=0, dropped_duplicates=())
spec = C.HistorySpec(columns=history_column_names(spec), last_values=1, trailing_steps=(2,),
                     trailing_days=(365, 1826), all_history_mean=True, start_offset_steps=0,
                     dropped_duplicates=())

class Vault:
    def asof_rows(self, unit_rows, newest, k):
        lab = np.array([[1.0, 2.0], [3.0, 4.0]])
        j = np.asarray(newest) - k - 1
        out = np.full(len(j), np.nan)
        ok = j >= 0
        out[ok] = lab[np.asarray(unit_rows)[ok], j[ok]]
        return out

from treeroute._proposed.fit_context import UnitHistory
hist = {u: UnitHistory(u, "g", 2, C.CutKind.FIT, 0, np.array([1]), np.array([1]), np.array([9.0]))
        for u in ("a", "b")}
block, filled = history_block(grid, spec, np.array([2, 2]), np.array([0, 1]), 0, Vault(), hist,
                              np.array([1, 1]), 5.0)
res["block"] = block.tolist()
# F1 fallback through the approved UnitHistory: nothing readable at step 0, so the donor mean
lone = {"a": UnitHistory("a", "g", 2, C.CutKind.FIT, 0, np.array([2]), np.array([2]), np.array([9.0]))}
grid1 = build_dense_grid(np.array(["a", "a"], dtype=object), np.array(["g", "g"], dtype=object),
                         np.array([1, 2]), (C.Step(1), C.Step(2)))
b1, _ = history_block(grid1, spec, np.array([1]), np.array([0]), 0, Vault(), lone, np.array([1]), 5.0)
res["donor_block"] = b1.tolist()

# aggregate_time with the approved ColumnFacts, Cadence, Window and AggStat (F5): the ruled
# 1-year lag of a centred 3-month index survives, through compute_lag on an approved TargetFacts
annual = C.Cadence(C.CadenceKind.REGULAR, 1, C.StepUnit.YEAR)
centred = C.ColumnFacts(**{**facts("x", C.Role.DRIVER).__dict__, "stamp": C.Stamp.PERIOD_CENTRE,
                           "window": C.Window(3, C.StepUnit.MONTH, C.Align.CENTRED)})
msteps = np.array([y * 12 + m for y in (2010, 2011) for m in range(1, 13)])
rows, agg_facts = aggregate_time(pd.DataFrame({"x": np.arange(24.0)}), np.zeros(24, dtype=int), msteps,
                                 "x", centred, annual, C.AggStat.MEAN, None)
target = C.TargetFacts(name="y", legal_range=(0.0, 1.0), legal_range_source="doc", cadence=annual,
                       stamp=C.Stamp.PERIOD_END, window=C.Window(1, C.StepUnit.YEAR, C.Align.BACKWARD),
                       time_columns={}, measurement_error_floor=None, calibration_through=None,
                       computed_from=(), product_family=None)
res["agg"] = rows["x"].tolist()
res["agg_type"] = type(agg_facts).__name__
res["agg_lag"] = compute_lag(agg_facts, target, annual, C.ReferenceKind.NOWCAST).steps

# join_coarser_column with an approved Lag (F6)
joined = join_coarser_column(pd.DataFrame({"z": [0.0, 0.0]}), np.array([0, 0]), np.array([2011, 2011]),
                             pd.DataFrame({"a": [3.0, 3.0]}), np.array([0, 0]), np.array([2010, 2010]),
                             "a", annual, monthly, C.Lag(column="a", steps=1, column_cadence=annual,
                                                         floor_reason=None))
res["coarse"] = joined["a"].tolist()
res["issue"] = features_at_issue_step(np.array([[1.0], [2.0]]), np.array([0, 0]), steps, 1)[1].tolist()
res["pred"] = predecessor_index(np.array([0, 0]), steps, 1).tolist()
print("RESULT " + json.dumps(res))
"""


def test_io_bodies_accept_the_approved_proposed_shapes():
    proc = run_python(CODE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")][-1]
    res = json.loads(line[len("RESULT "):])
    assert res["monthly"] == [2010 * 12 + 1, 2010 * 12 + 2]
    assert res["comp"] == [2010 * 23 + 23] and res["comp_days"] == 13  # 19..31 December
    assert res["masked"] == {"x": 1}
    assert res["lagged"] == [None, None]  # row 1 takes row 0's masked value
    assert res["comp_lag"] == [None, 1.0]  # store-form and proposed-form composites are one cadence
    assert res["tree"] == ["x"]
    assert res["frozen"] == [2.0, 2.0]
    assert res["grid"] == [["a", "b"], 1, 2]
    assert res["block"] == [[1.0, 1.0, 1.0], [3.0, 3.0, 3.0]]
    assert res["donor_block"] == [[5.0, 5.0, 5.0]]
    assert res["agg"] == [5.5, 17.5] and res["agg_type"] == "ColumnFacts" and res["agg_lag"] == 1
    assert res["coarse"] == [3.0, 3.0]
    assert res["issue"] == [1.0]
    assert res["pred"] == [-1, 0]
