"""The decision surface's fold entries (SPEC_TABLE_MODE.md 5.11, 5.12): FitContext.donor_rows_outside and
fit.weights.weight_models_for_folds, on a table run's state built up to its fits (the toy smoke)."""

from pathlib import Path

import numpy as np
import pytest

from table_toy import FAKE_LAUNCH, build_toy_table_package, patch_sklearn, toy_machine


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    from treeroute.pipeline.table_passes import TableRunState
    from treeroute.pipeline.table_run import TablePipeline

    undo = patch_sklearn()
    base = tmp_path_factory.mktemp("fold_gls")
    pkg = build_toy_table_package(base / "pk")
    pipe = TablePipeline(pkg, base / "runs", "smoke", toy_machine(base), lambda s: None, FAKE_LAUNCH)
    state = None
    try:
        pipe._lock()
        pipe._load()
        pipe._groups()
        pipe._preflight_target()
        pipe._read()
        pipe._derive()
        pipe._smoke_bank_plans(pipe._vault(None))
        pipe._open()
        pipe._temp()
        state = TableRunState(pipe).__enter__()
        state.build_pool(need_inner=True)
        state.fit(need_inner=True)
        yield pipe, state
    finally:
        if state is not None:
            state.__exit__(None, None, None)
        pipe._release()
        undo()


def test_donor_rows_outside_is_donor_rows_less_the_listed_groups(fitted):
    pipe, state = fitted
    ctx = state.ctx_inner
    whole = ctx.donor_rows("probe_whole")
    for i, g in enumerate(sorted(set(np.asarray(whole.group_of_row).tolist()))):
        sub = ctx.donor_rows_outside("probe_fold", (g,), i)
        keep = np.asarray(whole.group_of_row, dtype=object) != g
        assert np.array_equal(np.asarray(sub.unit_ids, dtype=object), np.asarray(whole.unit_ids, dtype=object)[keep])
        assert np.array_equal(sub.times, whole.times[keep]) and sub.y.tobytes() == whole.y[keep].tobytes()
        assert np.asarray(sub.X).tobytes() == np.asarray(whole.X)[keep].tobytes()
        assert sub.fold == i and g not in sub.groups
        last = ctx.log()[-1]
        assert last.fold == i and last.fold_purpose.value == "decision_surface" and last.n_rows == int(keep.sum())


def test_each_fold_model_saw_no_row_of_its_block(fitted):
    from treeroute import split as SP

    pipe, state = fitted
    groups = np.asarray(pipe.table.groups, dtype=object)
    for i, (g,) in enumerate(state.derived["R13"].value[1]):
        model = state.fold_weights[g]
        assert model.fold == i
        rows = np.asarray(model.forest.grid_rows, dtype=np.int64)
        assert rows.size and not set(groups[rows].tolist()) & set(SP.block_of_group(pipe.blocks, g))
        assert int(model.cut) <= int(state.cuts.guard_cut)


def test_a_fold_that_leaves_out_nothing_is_the_cut_model(fitted, monkeypatch):
    from treeroute.fit import weights as W

    pipe, state = fitted
    real = state.ctx_guard.donor_rows_outside
    monkeypatch.setattr(state.ctx_guard, "donor_rows_outside", lambda purpose, left, fold: real(purpose, (), fold))
    models = W.weight_models_for_folds(state.ctx_fit, state.ctx_guard, state.store_fit, state.bank_fit.tree_group,
                                       blocks=pipe.blocks, folds=(("g_a",),), echo=lambda s: None)
    m = models["g_a"]
    ref = state.weights
    assert m.forest.oob_sigma.tobytes() == ref.forest.oob_sigma.tobytes()
    assert np.array_equal(m.forest.grid_rows, ref.forest.grid_rows)
    assert (m.sigma_floor, m.clip_low, m.clip_high) == (ref.sigma_floor, ref.clip_low, ref.clip_high)
