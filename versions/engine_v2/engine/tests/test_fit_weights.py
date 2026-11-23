"""fit/weights.py: the GLS row-weight model (plan 2.4 R25; owner rulings A: D55-D60; E: L5 c).

  - cross_region_error: |y - float64 mean of the plain answers of the trees outside the row's overlap
    block|; the blocks are REQUIRED (probe: omitted blocks silently meant "each group its own block");
    own-block columns are never read; a single-block bank is refused;
  - fit_weight_model: the engine constants (C13 GLS_*), fitted only with sklearn patched by sklearnex,
    deterministic, keeping its out-of-bag sigma (L5 c); refusals;
  - sigma_floor (1% of s), sigma_clip_bounds (5th / 95th percentiles), row_weights (floor, clip,
    1/sigma^2, ratio cap 100; equal sigma gives equal weights);
  - weight_model_for_cut end to end on a small tree-answer store double: donor rows at the lead's GUARD
    cut, the same error as cross_region_error, the floor (through R36's guard_tolerance) and bounds
    from the donor rows only; with one-group blocks and with a two-group block (the target of g_a's
    and g_b's rows reads only g_c's trees); the R25 record names the blocks, the answers' bank cut and
    the L6 disclosure;
  - sigma served out-of-bag on fitted rows, the whole forest elsewhere;
  - a warning of the forest fit other than the out-of-bag one is re-emitted and recorded, never dropped;
  - RAM (G-DISK): gls_ram_bytes' parts from the P2 and P5 engine constants (the row blocks of the donor matrix
    build and of the target, agent G 2026-10-06); weight_model_for_cut refuses before the donor matrix is built
    when the peak exceeds the RAM available, and FitContext.donor_rows_checked hands out the same rows, X,
    row-key hash and log row as donor_rows. (The blocks' byte identity is tests/test_fit_weights_blocks.py.)
"""

import numpy as np
import pytest

from test_vault_world import FIT_CUT_0, GROUPS, GUARD_CUT_0, make_context, make_world
from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind, Link
from treeroute.fit.weights import (L6_ANSWERS_DISCLOSURE, OobSigmaForest, WeightModel, WeightsRefusal,
                                   cross_region_error, fit_weight_model, gls_ram_bytes, row_weights,
                                   sigma_clip_bounds, sigma_floor, weight_model_for_cut, weight_model_record,
                                   weights_for_rows)
from treeroute.report.metrics import guard_tolerance
from treeroute.split import OverlapBlocks, SplitRefusal

TREES_PER_GROUP = 3


@pytest.fixture(scope="module")
def patched():
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn()
    yield
    if not was:
        sklearnex.unpatch_sklearn()


def tree_group():
    return tuple(g for g in GROUPS for _ in range(TREES_PER_GROUP))


def singles():
    """Every group alone in its overlap block (passed explicitly, never a default)."""
    return OverlapBlocks(block_of_group={g: i for i, g in enumerate(GROUPS)},
                         members=tuple((g,) for g in GROUPS), linked_pairs=(), link_rule="grid_indices")


def pair():
    """g_a and g_b share an overlap block; g_c is alone."""
    return OverlapBlocks(block_of_group={"g_a": 0, "g_b": 0, "g_c": 1},
                         members=(("g_a", "g_b"), ("g_c",)), linked_pairs=(("g_a", "g_b", 1),),
                         link_rule="grid_indices")


def answers_for(donor):
    """A deterministic (rows, trees) float32 answer array; own-group columns hold NaN (never read)."""
    tg = np.asarray(tree_group(), dtype=object)
    k = np.arange(donor.y.size)[:, None]
    j = np.arange(tg.size)[None, :]
    A = (donor.y[:, None] * (1.0 + 0.01 * j) + np.sin(k + j)).astype(np.float32)
    own = np.asarray(donor.group_of_row, dtype=object)[:, None] == tg[None, :]
    A[own] = np.nan
    return A


class StoreDouble(object):
    """The tree-answer store's interface over an answer function (every tree but the rows' group's)."""

    def __init__(self, tg, answer_of):
        self._tg = np.asarray(tg, dtype=object)
        self.n_trees = self._tg.size
        self._answer_of = answer_of
        self.built = []

    def own_columns(self, group):
        return np.flatnonzero(self._tg == group)

    def build(self, group, kind, row_ids, features):
        assert kind == "plain"
        X = features(np.asarray(row_ids))
        assert X.dtype == np.float32 and X.shape[0] == len(row_ids)
        self.built.append((group, len(row_ids)))
        return len(row_ids)

    def unit_view(self, row_keys, kind):
        from types import SimpleNamespace
        values, groups = self._answer_of(np.asarray(row_keys))
        g = set(groups.tolist())
        assert len(g) == 1
        g = g.pop()
        index = np.flatnonzero(self._tg != g)
        return SimpleNamespace(values=values[:, index], tree_index=index, group=g, kind=kind)


# ------------------------------------------------------------------------------------ the target
def test_cross_region_error_leaves_out_the_rows_own_group():
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    A = answers_for(d)
    e = cross_region_error(d, A, tree_group(), blocks=singles())
    tg = np.asarray(tree_group(), dtype=object)
    for i in (0, d.y.size // 2, d.y.size - 1):
        g = d.group_of_row[i]
        cols = np.flatnonzero(tg != g)
        assert e[i] == abs(d.y[i] - A[i, cols].astype(np.float64).mean())
    eb = cross_region_error(d, A, tree_group(), blocks=pair())
    i = int(np.flatnonzero(np.asarray(d.group_of_row) == "g_a")[0])
    cols = np.flatnonzero(tg == "g_c")                         # g_b is in g_a's block: dropped too
    assert eb[i] == abs(d.y[i] - A[i, cols].astype(np.float64).mean())


def test_cross_region_error_refusals():
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls", ("g_a_u0", "g_a_u1"))
    one = tuple(["g_a"] * 4)
    with pytest.raises(WeightsRefusal, match="single-group bank"):
        cross_region_error(d, np.zeros((d.y.size, 4), dtype=np.float32), one, blocks=singles())
    full = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    with pytest.raises(WeightsRefusal, match="shape"):
        cross_region_error(full, answers_for(full)[:, :4], tree_group(), blocks=singles())
    bad = answers_for(full)
    bad[np.isfinite(bad)] = np.inf
    with pytest.raises(WeightsRefusal, match="missing or infinite"):
        cross_region_error(full, bad, tree_group(), blocks=singles())
    with pytest.raises(WeightsRefusal, match="only DonorRows"):
        cross_region_error(w.labels.asof(GUARD_CUT_0), answers_for(full), tree_group(), blocks=singles())


def test_probe_the_blocks_are_required():
    """Probe (review): with blocks omitted each group counted as its own block, silently."""
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    with pytest.raises(TypeError):
        cross_region_error(d, answers_for(d), tree_group())             # no default: a required keyword
    with pytest.raises(WeightsRefusal, match="overlap blocks"):
        cross_region_error(d, answers_for(d), tree_group(), blocks=None)
    partial = OverlapBlocks(block_of_group={"g_a": 0, "g_b": 1}, members=(("g_a",), ("g_b",)),
                            linked_pairs=(), link_rule="grid_indices")
    with pytest.raises(SplitRefusal, match="no overlap block"):
        cross_region_error(d, answers_for(d), tree_group(), blocks=partial)   # g_c is in no block


# ------------------------------------------------------------------------------------ the forest
def test_fit_weight_model_needs_the_sklearnex_patch():
    import sklearnex

    if sklearnex.sklearn_is_patched():
        pytest.skip("sklearn is patched in this process")
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    with pytest.raises(WeightsRefusal, match="not patched"):
        fit_weight_model(d, np.abs(d.y - d.y.mean()))


def test_fit_weight_model_uses_the_engine_constants_and_keeps_oob_sigma(patched):
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    e = cross_region_error(d, answers_for(d), tree_group(), blocks=singles())
    f = fit_weight_model(d, e)
    assert isinstance(f, OobSigmaForest)
    params = f._forest.get_params()
    assert params["n_estimators"] == K.GLS_TREES and params["max_depth"] == K.GLS_MAX_DEPTH
    assert params["min_samples_leaf"] == K.GLS_MIN_LEAF and params["max_features"] == K.GLS_MAX_FEATURES
    assert params["bootstrap"] is K.GLS_BOOTSTRAP and params["random_state"] == K.GLS_RANDOM_STATE
    assert params["n_jobs"] == K.GLS_THREADS and params["oob_score"] is True
    assert "sklearnex" in f.implementation
    assert np.array_equal(f.oob_sigma, f._forest.oob_prediction_)
    assert np.array_equal(f.grid_rows, d.grid_rows) and f.row_key_hash == d.row_key_hash
    again = fit_weight_model(d, e)                              # fixed random_state: the same forest
    assert np.array_equal(again.oob_sigma, f.oob_sigma)
    assert np.array_equal(again.predict(d.X), f.predict(d.X))
    # served sigma: out-of-bag on fitted rows, the forest elsewhere
    s = f.sigma(d.grid_rows, d.X)
    assert np.array_equal(s, f.oob_sigma)
    other = np.array([10 ** 7, 10 ** 7 + 1])
    assert np.array_equal(f.sigma(other, d.X[:2]), f.predict(d.X[:2]))
    assert not np.array_equal(f.predict(d.X), f.oob_sigma)      # in-bag and out-of-bag differ


def test_fit_weight_model_refusals(patched, monkeypatch):
    import warnings

    import sklearn.ensemble

    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    with pytest.raises(WeightsRefusal, match="non-negative"):
        fit_weight_model(d, -np.ones(d.y.size))
    with pytest.raises(WeightsRefusal, match="values for"):
        fit_weight_model(d, np.ones(d.y.size - 1))
    with pytest.raises(WeightsRefusal, match="only DonorRows"):
        fit_weight_model(w.labels.asof(GUARD_CUT_0), np.ones(3))
    # planted: a row with no out-of-bag tree (the library warns and answers 0; the engine refuses)
    cls = sklearn.ensemble.RandomForestRegressor
    real_fit = cls.fit

    def fit_without_oob(self, X, y, sample_weight=None):
        out = real_fit(self, X, y, sample_weight=sample_weight)
        warnings.warn("Some inputs do not have OOB scores. This probably means too few trees")
        return out

    monkeypatch.setattr(cls, "fit", fit_without_oob)
    with pytest.raises(WeightsRefusal, match="out-of-bag"):
        fit_weight_model(d, np.abs(d.y - d.y.mean()))


def test_other_fit_warnings_are_reemitted_and_recorded(patched, monkeypatch):
    """Review: catch_warnings kept only the OOB warnings; any other library warning was dropped."""
    import warnings

    import sklearn.ensemble

    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    cls = sklearn.ensemble.RandomForestRegressor
    real_fit = cls.fit

    def fit_with_a_fallback_note(self, X, y, sample_weight=None):
        out = real_fit(self, X, y, sample_weight=sample_weight)
        warnings.warn("planted: a oneDAL fallback note", RuntimeWarning)
        return out

    monkeypatch.setattr(cls, "fit", fit_with_a_fallback_note)
    with pytest.warns(RuntimeWarning, match="planted: a oneDAL fallback note"):
        f = fit_weight_model(d, np.abs(d.y - d.y.mean()))
    assert f.fit_warnings == ("RuntimeWarning: planted: a oneDAL fallback note",)


# ------------------------------------------------------------------------------------ floor, bounds, weights
def test_floor_and_clip_bounds():
    assert sigma_floor(20.0) == 0.2
    with pytest.raises(WeightsRefusal):
        sigma_floor(0.0)
    s = np.arange(1.0, 101.0)
    assert sigma_clip_bounds(s) == tuple(float(v) for v in np.percentile(s, [5.0, 95.0]))
    with pytest.raises(WeightsRefusal, match="at least 2"):
        sigma_clip_bounds(np.array([1.0, np.nan]))


def test_row_weights_floor_clip_invert_cap():
    sigma = np.array([0.001, 0.5, 1.0, 2.0, 50.0])
    w = row_weights(sigma, floor=0.1, clip_low=0.2, clip_high=10.0)
    s = np.clip(np.maximum(sigma, 0.1), 0.2, 10.0)
    raw = 1.0 / s ** 2
    assert np.array_equal(w, np.maximum(raw, raw.max() / K.GLS_WEIGHT_RATIO_CAP))
    assert w.max() / w.min() <= K.GLS_WEIGHT_RATIO_CAP + 1e-9
    equal = row_weights(np.full(7, 3.0), 0.1, 0.2, 10.0)
    assert len(set(equal.tolist())) == 1                        # G-PLUMB: equal sigma, equal weights
    with pytest.raises(WeightsRefusal, match="missing or infinite"):
        row_weights(np.array([1.0, np.nan]), 0.1, 0.2, 10.0)
    with pytest.raises(WeightsRefusal, match="reversed"):
        row_weights(np.array([1.0]), 0.1, 2.0, 1.0)
    with pytest.raises(WeightsRefusal, match="positive"):
        row_weights(np.array([1.0]), 0.0, 0.2, 1.0)


# ------------------------------------------------------------------------------------ end to end
def _store_for(world):
    guard = make_context(world, 0, CutKind.GUARD)
    d = guard.donor_rows("probe")
    A = answers_for(d)
    index = {int(k): i for i, k in enumerate(d.grid_rows.tolist())}

    def answer_of(keys):
        rows = np.asarray([index[int(k)] for k in keys])
        return A[rows], np.asarray(d.group_of_row, dtype=object)[rows]

    return StoreDouble(tree_group(), answer_of), d, A


def test_weight_model_for_cut_end_to_end(patched):
    w = make_world()
    store, d, A = _store_for(w)
    fit_ctx, guard_ctx = make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD)
    model = weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=singles())
    assert isinstance(model, WeightModel) and model.cut == GUARD_CUT_0 and model.lead == 0
    assert model.fold == -1
    assert sorted(g for g, _ in store.built) == list(GROUPS)
    assert guard_ctx.log()[-1].purpose == "gls"
    ref = fit_weight_model(d, cross_region_error(d, A, tree_group(), blocks=singles()))
    assert np.array_equal(model.forest.oob_sigma, ref.oob_sigma)  # the same target, the same forest
    # the floor's s is R36's (guard_tolerance with k = 1), bit-equal to the ddof-0 standard deviation
    assert model.sigma_floor == K.GLS_SIGMA_FLOOR_SHARE * guard_tolerance(d, Link.IDENTITY, None, None, 1.0)
    assert model.sigma_floor == K.GLS_SIGMA_FLOOR_SHARE * float(np.std(d.y))
    lo, hi = sigma_clip_bounds(np.maximum(ref.oob_sigma, model.sigma_floor))
    assert (model.clip_low, model.clip_high) == (lo, hi)
    fit_rows = fit_ctx.router_rows(("g_a_u0", "g_b_u1"), "router")
    X = w.features.tree_features(fit_rows.row_positions)
    X = np.where(np.isnan(X), 0.0, X).astype(np.float32)
    wts = weights_for_rows(model, fit_rows.row_positions, X)
    assert wts.shape == (fit_rows.y.size,) and np.isfinite(wts).all() and (wts > 0).all()
    rec = weight_model_record(model)
    assert rec.rule_id == "R25" and rec.input_hashes["donor_row_key_hash"] == d.row_key_hash
    assert rec.inputs["blocks"] == [["g_a"], ["g_b"], ["g_c"]]
    assert rec.inputs["answers_bank_cut"] == FIT_CUT_0 and rec.inputs["answers_bank"] == L6_ANSWERS_DISCLOSURE
    assert rec.inputs["fit_warnings"] == []
    with pytest.raises(WeightsRefusal, match="weight_model_for_cut"):
        weight_model_record(WeightModel(forest=ref, cut=model.cut, lead=0, sigma_floor=model.sigma_floor,
                                        clip_low=lo, clip_high=hi, fold=-1))   # fit_weight_model alone


def test_weight_model_for_cut_with_a_two_group_block(patched):
    """LORO L2(4) end to end: g_a and g_b share a block, so their rows' target reads only g_c's trees and
    g_c's rows read g_a's and g_b's."""
    w = make_world()
    store, d, A = _store_for(w)
    fit_ctx, guard_ctx = make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD)
    model = weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=pair())
    e = cross_region_error(d, A, tree_group(), blocks=pair())
    tg = np.asarray(tree_group(), dtype=object)
    for g, allowed in (("g_a", ("g_c",)), ("g_b", ("g_c",)), ("g_c", ("g_a", "g_b"))):
        i = int(np.flatnonzero(np.asarray(d.group_of_row) == g)[0])
        cols = np.flatnonzero(np.isin(tg, allowed))
        assert e[i] == abs(d.y[i] - A[i, cols].astype(np.float64).mean())
    ref = fit_weight_model(d, e)
    assert np.array_equal(model.forest.oob_sigma, ref.oob_sigma)
    single = weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=singles())
    assert not np.array_equal(single.forest.oob_sigma, model.forest.oob_sigma)   # the block changes it
    rec = weight_model_record(model)
    assert rec.inputs["blocks"] == [["g_a", "g_b"], ["g_a", "g_b"], ["g_c"]]
    with pytest.raises(TypeError):
        weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group())             # blocks required
    with pytest.raises(WeightsRefusal, match="overlap blocks"):
        weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=None)


def test_weight_model_for_cut_refusals(patched):
    w = make_world()
    store, d, A = _store_for(w)
    fit0, guard0 = make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD)
    b = singles()
    with pytest.raises(WeightsRefusal, match="lead"):
        weight_model_for_cut(make_context(w, 3, CutKind.FIT), guard0, store, tree_group(), blocks=b)
    with pytest.raises(WeightsRefusal, match="FIT context"):
        weight_model_for_cut(guard0, guard0, store, tree_group(), blocks=b)
    with pytest.raises(WeightsRefusal, match="trees"):
        weight_model_for_cut(fit0, guard0, store, tree_group()[:-1], blocks=b)
    swapped = tuple(reversed(tree_group()))
    with pytest.raises(WeightsRefusal, match="physical keys"):
        weight_model_for_cut(fit0, guard0, store, swapped, blocks=b)
    with pytest.raises(WeightsRefusal, match="FitContext"):
        weight_model_for_cut(object(), guard0, store, tree_group(), blocks=b)


# ------------------------------------------------------------------------------------------ RAM (G-DISK)
def test_gls_ram_bytes_parts_come_from_the_engine_constants(monkeypatch):
    rows = {"g_a": 1000, "g_b": 3000}
    reads = {"g_a": 200, "g_b": 100}
    parts = gls_ram_bytes(rows, 50, reads)
    values = 4000 * 50
    assert parts["matrix"] == values * 4
    # one block holds every row at this size (P5: 2^22 values a block), so the build holds the matrix beside them all
    assert parts["build_block_rows"] == 4000
    assert parts["build"] == values * 4 + values * K.GLS_MATRIX_BUILD_BYTES_PER_VALUE
    # the largest group's read: g_b has 3000 x 100 = 300,000 cells, g_a 200,000; one target block holds the group, so
    # its float32 read (4 bytes a cell) beside the block's copies outweighs the store's read in flight
    assert parts["answer_read_group"] == "g_b" and parts["answer_block_rows"] == 3000
    in_flight = 3000 * 100 * K.GLS_ANSWER_READ_BYTES_PER_CELL + 3000 * K.GLS_ANSWER_READ_BYTES_PER_ROW
    assert parts["answer_read"] == values * 4 + max(in_flight, 3000 * 100 * (4 + K.GLS_ANSWER_BLOCK_BYTES_PER_CELL))
    assert parts["answer_read"] == values * 4 + 3000 * 100 * 16
    assert parts["forest"] == values * 4 + values * K.GLS_FOREST_BYTES_PER_VALUE + 4000 * K.GLS_FOREST_BYTES_PER_ROW
    assert parts["peak"] == max(parts["build"], parts["answer_read"], parts["forest"])
    assert (K.get("P2.gls_matrix_build_bytes_per_value"), K.get("P2.gls_answer_read_bytes_per_cell"),
            K.get("P2.gls_answer_read_bytes_per_row"), K.get("P2.gls_answer_block_bytes_per_cell"),
            K.get("P5.donor_block_values")) == (9, 8, 64, 12, 4194304)
    assert K.DONOR_BLOCK_VALUES == K.get("P5.donor_block_values")
    # smaller blocks: the build holds the matrix beside ONE block (1000 values: 20 rows of 50 columns); the target
    # holds the group's whole float32 read beside one row block (g_a: 5 rows of 200 columns, g_b: 10 rows of 100),
    # which is now below the store's read in flight (its float32 output beside the table's gathered rows, and its
    # row-index arrays a row)
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 1000)
    small = gls_ram_bytes(rows, 50, reads)
    assert small["build_block_rows"] == 20 and small["build"] == values * 4 + 20 * 50 * K.GLS_MATRIX_BUILD_BYTES_PER_VALUE
    assert small["answer_read_group"] == "g_b" and small["answer_block_rows"] == 10
    assert 3000 * 100 * 4 + 10 * 100 * K.GLS_ANSWER_BLOCK_BYTES_PER_CELL < in_flight
    assert small["answer_read"] == values * 4 + in_flight
    assert small["answer_read"] == values * 4 + 3000 * 100 * 8 + 3000 * 64
    assert small["forest"] == parts["forest"]
    assert small["peak"] == max(small["build"], small["answer_read"], small["forest"])
    # a trailing single row joins the block before it (fit.weights._row_blocks): 1001 rows in blocks of 5 -> 6 at most
    tail = gls_ram_bytes({"g_a": 1001}, 50, {"g_a": 200})
    assert tail["answer_block_rows"] == 6


def test_donor_rows_checked_hands_out_the_donor_rows_after_the_check():
    w = make_world()
    seen = []

    def check(group_of_row, n_columns):
        seen.append((np.asarray(group_of_row).copy(), int(n_columns)))

    a = make_context(w, 0, CutKind.GUARD)
    b = make_context(w, 0, CutKind.GUARD)
    d = a.donor_rows("gls")
    e = b.donor_rows_checked("gls", check)
    assert len(seen) == 1
    assert np.array_equal(seen[0][0], np.asarray(d.group_of_row)) and seen[0][1] == d.X.shape[1]
    assert d.X.tobytes() == e.X.tobytes() and d.row_key_hash == e.row_key_hash
    assert np.array_equal(d.grid_rows, e.grid_rows) and np.array_equal(d.y, e.y)
    assert a.log() == b.log()                                        # one donor_rows log row, the same


def test_weight_model_for_cut_refuses_before_the_donor_matrix_when_ram_is_short(patched, monkeypatch):
    from treeroute.fit import context as FC
    from treeroute.runs import preflight

    w = make_world()
    store, d, A = _store_for(w)
    fit_ctx, guard_ctx = make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD)
    built = []
    orig = FC.FitContext._tree_feature_matrix                  # the eager donor matrix (built in row blocks)

    def spy(self, pos):
        built.append(int(np.asarray(pos).size))
        return orig(self, pos)
    monkeypatch.setattr(FC.FitContext, "_tree_feature_matrix", spy)
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)          # owner ruling Q1: no wait, so it refuses as before
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 1000)
    with pytest.raises(WeightsRefusal, match="G-DISK") as info:
        weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=singles())
    assert "GiB of RAM at its peak" in str(info.value) and "donor matrix" in str(info.value)
    assert built == [] and store.built == []                   # refused before the matrix and any table
    # with the RAM there, the same call goes through and its rows are the donor rows'
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 1 << 40)
    model = weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=singles())
    assert built == [d.y.size] and model.forest.row_key_hash == d.row_key_hash
