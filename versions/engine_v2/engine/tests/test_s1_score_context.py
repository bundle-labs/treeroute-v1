"""Owner ruling S1 (OWNER_RULINGS_2026-10-06.md section S, extends H4): a SCORED row whose router context is missing
or non-finite is LEFT OUT of scoring (never filled), saved with a flag and counted per unit and lead in
run_record.json; a unit left with no scored row is listed as unscored; a pass that leaves nothing out records
nothing (byte for byte the pass before S1); the region kind (no context read) is never filtered."""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from treeroute.pipeline import passes as P
from treeroute.pipeline import record as REC
from treeroute.pipeline import router as PR
from treeroute.pipeline import stages as ST


class _Features(object):
    context_columns = ("c1", "c2")

    def __init__(self, C):
        self.C = np.asarray(C, dtype=np.float32)

    def context(self, keys):
        return self.C[np.asarray(keys, dtype=np.int64)]


class _Log(object):
    def __init__(self):
        self.lines = []

    def __call__(self, line):
        self.lines.append(line)

    def file_only(self, line):
        self.lines.append(line)


def _state(tmp_path, monkeypatch, kind=PR.KIND_PER_UNIT):
    monkeypatch.setattr(P, "_years_of_steps", lambda steps, cadence: np.zeros(len(steps), dtype=np.int64))
    (tmp_path / REC.RUN_RECORD).write_text(json.dumps({"kind": "smoke"}) + "\n", encoding="utf-8")
    s = object.__new__(P.RunState)
    s.kind, s.log = kind, _Log()
    s.unit_group = {"a": "g1", "b": "g1", "c": "g2"}
    s.p = SimpleNamespace(folder=tmp_path, cadence=None)
    return s


def test_s1_leaves_out_scored_rows_flags_counts_and_never_fills(tmp_path, monkeypatch):
    s = _state(tmp_path, monkeypatch)
    C = [[1, 2], [np.nan, 2], [1, 2], [1, np.inf], [1, np.nan]]
    ctx = SimpleNamespace(features=_Features(C))
    units = np.array(["a", "a", "b", "c", "c"], dtype=object)
    steps = np.array([5, 6, 5, 5, 6], dtype=np.int64)
    args = ("lead 6 test pass", ctx, 6, np.arange(5), units, steps, np.arange(5.0))
    keep, rec = s.leave_out_score_context(*args)
    assert keep.tolist() == [True, False, True, False, False]
    assert rec["by_unit"] == {"a": 1, "c": 2} and rec["units_unscored"] == ["c"]
    assert rec["by_column"] == {"c1": 1, "c2": 2} and rec["rows_left_out"] == 3 and rec["lead"] == 6
    saved = pd.read_parquet(tmp_path / rec["rows_file"])
    assert saved[ST.SCORE_CONTEXT_FLAG].all() and saved["unit"].tolist() == ["a", "c", "c"]
    assert saved["issue"].tolist() == [0, -1, 0] and saved["y"].tolist() == [1.0, 3.0, 4.0]
    assert saved[ST.MISSING_PREFIX + "c1"].tolist() == [True, False, False]
    run_rec = json.loads((tmp_path / REC.RUN_RECORD).read_text(encoding="utf-8"))
    held = run_rec[REC.SCORE_CONTEXT_KEY]["by_pass"]["lead 6 test pass"]
    assert held["rows_left_out"] == 3 and held["units_unscored"] == ["c"] and held["by_unit"] == {"a": 1, "c": 2}
    # a resumed pass records the same rows and summary: nothing changes
    before = (tmp_path / REC.RUN_RECORD).read_bytes()
    s.leave_out_score_context(*args)
    assert (tmp_path / REC.RUN_RECORD).read_bytes() == before
    # nothing missing: every row kept, no record, no file, run_record.json untouched
    keep2, rec2 = s.leave_out_score_context("decision surface", SimpleNamespace(features=_Features([C[0], C[2]])), 0,
                                            np.arange(2), units[[0, 2]], steps[[0, 2]])
    assert keep2.tolist() == [True, True] and rec2 is None
    assert (tmp_path / REC.RUN_RECORD).read_bytes() == before
    assert not (tmp_path / P.CONTEXT_MISSING_DIR / "decision_surface_scored.parquet").exists()


def test_s1_region_kind_is_never_filtered(tmp_path, monkeypatch):
    s = _state(tmp_path, monkeypatch, kind=PR.KIND_REGION)
    keep, rec = s.leave_out_score_context("test pass", SimpleNamespace(features=_Features([[np.nan, 1]])), 0,
                                          np.arange(1), np.array(["a"], dtype=object), np.array([5]))
    assert keep.tolist() == [True] and rec is None
