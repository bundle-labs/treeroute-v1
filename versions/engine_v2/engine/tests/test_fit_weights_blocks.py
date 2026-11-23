"""Row blocks of the GLS weight model's donor matrix and of its target (agent G, 2026-10-06): the same bytes, less RAM.

The donor matrix (FitContext's eager DonorRows.X) is read in row blocks of P5.donor_block_values values straight into
one preallocated float32 array, and each group's GLS target is computed in row blocks of its one store read
(fit.weights._blocked_group_error). Neither may change a single number:

  - _row_blocks covers every row once, in order, P5.donor_block_values values a block, and never leaves a block of one
    row unless the read has one row;
  - _blocked_group_error equals _group_error over the whole group's column selection BYTE FOR BYTE, on float32 answers
    with a wide dynamic range (where the float64 summation order shows), over many shapes and block sizes, with and
    without a trailing single row; a PLANTED one-row block differs from the whole group, so these values can see an
    order change (the reason _row_blocks merges a trailing single row);
  - the eager donor X built in many blocks equals the one-block build byte for byte (the float32 cast, the R30 0-fill,
    the C order), with one feature-source read a block; an infinite value is refused with the count over every block;
  - weight_model_for_cut with tiny blocks gives the default blocks' model (out-of-bag sigma, floor, clip bounds, the
    R25 record), with one-group and two-group overlap blocks;
  - RAM (tracemalloc, numpy's buffers): the blocked build holds the matrix plus about one block where the one-block
    build holds the matrix about twice, and over a real FeaturePool (fit.pool: a gather and its reordered copy) it
    stays under P2.gls_matrix_build_bytes_per_value a block value; a lazy hand-out's read makes its float32 copy only
    after the source's read returns (never beside the source's own copies); the blocked target holds about one block
    where the whole group's target holds three copies of its selection; one real tree-answer store read of a group's
    rows (through the per-group DropAfterRead view, as the donor-row pass reads it) peaks at its float32 output beside
    the table's gathered rows and its row-index arrays, P2.gls_answer_read_bytes_per_cell a cell and
    P2.gls_answer_read_bytes_per_row a row (gls_ram_bytes' answer read in flight);
  - a feature source that returns the wrong shape is refused (R30), naming the row block in the eager build.
"""

import gc
import tracemalloc

import numpy as np
import pytest

from test_fit_tables import GROUPS as STORE_GROUPS
from test_fit_tables import REGISTRY_DIR, Features, _fit_bank, _group_ids, _rows, build_dir, true_group  # noqa: F401
from test_fit_weights import _store_for, pair, singles, tree_group
from test_vault_world import GUARD_CUT_0, make_context, make_world
from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind
from treeroute.fit import context as FC
from treeroute.fit import weights as FW


@pytest.fixture(scope="module")
def patched():
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn()
    yield
    if not was:
        sklearnex.unpatch_sklearn()


def wide_answers(rows, cols, seed):
    """float32 answers spread over many orders of magnitude, both signs: their float64 sums depend on the order."""
    rng = np.random.default_rng(seed)
    mag = np.exp(rng.standard_normal((rows, cols)) * 12.0)
    return (np.sign(rng.standard_normal((rows, cols))) * mag).astype(np.float32)


def bits(a):
    return np.ascontiguousarray(a, dtype=np.float64).view(np.uint64)


# ------------------------------------------------------------------------------------ the blocks
def test_row_blocks_cover_every_row_and_never_leave_one_row(monkeypatch):
    for block_values in (1, 7, 64, 1000, K.get("P5.donor_block_values")):
        monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", block_values)
        for n in (0, 1, 2, 3, 4, 5, 9, 10, 11, 101, 1001):
            for c in (1, 2, 3, 13, 200):
                blocks = FW._row_blocks(n, c)
                step = max(block_values // c, 2)
                flat = [r for a, b in blocks for r in range(a, b)]
                assert flat == list(range(n)), (block_values, n, c)
                for a, b in blocks:
                    assert b - a >= 2 or n == 1, (block_values, n, c, blocks)
                    assert b - a <= step + 1
                assert all(b - a == step for a, b in blocks[:-1])


def test_feature_block_rows_reads_the_engine_constant(monkeypatch):
    assert FC.feature_block_rows(563) == K.get("P5.donor_block_values") // 563 == 7449
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 10)
    assert FC.feature_block_rows(3) == 3 and FC.feature_block_rows(50) == 1 and FC.feature_block_rows(0) == 10


# ------------------------------------------------------------------------------------ the target, byte for byte
def test_blocked_target_is_the_whole_group_target_byte_for_byte(monkeypatch):
    merged = 0
    cases = 0
    for r in (1, 2, 3, 5, 17, 101, 1001):
        for c in (1, 2, 9, 33, 257):
            values = wide_answers(r, c, seed=r * 1000 + c)                    # C-ordered, as the store's read
            where = np.flatnonzero(np.arange(c) % 4 != 1) if c > 2 else np.arange(c)
            y = np.random.default_rng(r + c).standard_normal(r) * 1e3
            whole = FW._group_error(y, values[:, where])                        # the formula on the whole group
            for block_values in (2 * c, 3 * c, 4 * c, 7 * c + 1, 64 * c, 10 ** 9):
                monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", block_values)
                step = max(block_values // c, 2)
                if r > step and r % step == 1:
                    merged += 1
                got = FW._blocked_group_error(y, values, where)
                cases += 1
                assert got.dtype == np.float64 and got.shape == (r,)
                assert np.array_equal(bits(got), bits(whole)), (r, c, block_values)
    assert cases == 7 * 5 * 6 and merged > 0           # trailing single rows were merged in some cases


def test_a_planted_one_row_block_differs_from_the_whole_group():
    """The values above can see a change of summation order: the target of ONE row alone (numpy sums a 1-row
    selection pairwise) differs from the same row inside the whole group (summed column by column)."""
    r, c = 64, 257
    values = wide_answers(r, c, seed=3)
    where = np.flatnonzero(np.arange(c) % 4 != 1)
    y = np.zeros(r)
    whole = FW._group_error(y, values[:, where])
    single = np.concatenate([FW._group_error(y[i:i + 1], values[i:i + 1][:, where]) for i in range(r)])
    assert not np.array_equal(bits(single), bits(whole))
    assert values[:, where].flags.f_contiguous and not values[:, where].flags.c_contiguous


def test_blocked_target_refuses_a_missing_answer_like_the_whole(monkeypatch):
    values = wide_answers(40, 9, seed=11)
    values[37, 4] = np.nan
    where = np.arange(9)
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 9 * 4)
    with pytest.raises(FW.WeightsRefusal, match="missing or infinite"):
        FW._blocked_group_error(np.zeros(40), values, where)
    values[37, 4] = np.inf
    with pytest.raises(FW.WeightsRefusal, match="missing or infinite"):
        FW._blocked_group_error(np.zeros(40), values, where)
    keep = np.asarray([0, 1, 2, 3, 5, 6, 7, 8])                     # a column never read may hold anything
    whole = FW._group_error(np.zeros(40), values[:, keep])
    assert np.array_equal(bits(FW._blocked_group_error(np.zeros(40), values, keep)), bits(whole))


# ------------------------------------------------------------------------------------ the donor matrix
def test_eager_donor_x_is_the_same_in_many_blocks(monkeypatch):
    w = make_world()
    one = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    reads_one = [n for kind, n in w.features.calls if kind == "tree"]
    assert reads_one == [one.y.size]                                     # one block at the default size
    assert one.X.dtype == np.float32 and one.X.flags.c_contiguous and one.X.flags.owndata
    assert (one.X == 0).any() and np.isfinite(one.X).all()               # R30: the planted NaN are 0-filled
    for block_values in (3, 7, 100, 3 * (one.y.size - 1)):
        monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", block_values)
        w.features.calls.clear()
        many = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
        step = FC.feature_block_rows(3)
        reads = [n for kind, n in w.features.calls if kind == "tree"]
        assert reads == [min(step, one.y.size - a) for a in range(0, one.y.size, step)]
        assert many.X.dtype == one.X.dtype and many.X.shape == one.X.shape
        assert many.X.flags.c_contiguous and many.X.flags.owndata
        assert many.X.tobytes() == one.X.tobytes(), block_values
        assert many.row_key_hash == one.row_key_hash and np.array_equal(many.grid_rows, one.grid_rows)
        checked = make_context(w, 0, CutKind.GUARD).donor_rows_checked("gls", lambda g, n: None)
        assert checked.X.tobytes() == one.X.tobytes()


def test_a_float64_source_is_cast_per_value_as_before(monkeypatch):
    """A feature source that returns float64: the block's float32 values are np.array(read, dtype=float32)'s."""
    w = make_world()
    ref_src = w.features._tree.copy()
    w.features._tree = (ref_src.astype(np.float64) * (1.0 + 1e-9)).astype(np.float64)
    one = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    expect = np.array(w.features._tree[one.grid_rows], dtype=np.float32, copy=True)
    expect[np.isnan(expect)] = 0.0
    assert one.X.tobytes() == expect.tobytes()
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 5)
    assert make_context(w, 0, CutKind.GUARD).donor_rows("gls").X.tobytes() == expect.tobytes()


def test_infinite_features_are_refused_with_the_count_over_every_block(monkeypatch):
    w = make_world()
    d = make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    rows = d.grid_rows[[0, 1, d.y.size // 2, d.y.size - 1]]
    w.features._tree[rows, 0] = np.inf
    w.features._tree[rows[2], 2] = -np.inf
    for block_values in (K.get("P5.donor_block_values"), 6):
        monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", block_values)
        with pytest.raises(FC.FitContextRefusal, match=r"^.*\b5 tree feature values are infinite"):
            make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    lazy = make_context(w, 0, CutKind.GUARD).donor_rows_lazy("gls")         # the lazy hand-out: per read, as before
    with pytest.raises(FC.FitContextRefusal, match="2 tree feature values are infinite"):
        lazy.X[np.asarray([0, 1])]
    assert lazy.X[np.asarray([2, 3])].dtype == np.float32


def test_a_wrong_shape_from_the_source_is_refused_naming_the_block(monkeypatch):
    w = make_world()
    n = make_context(w, 0, CutKind.GUARD).donor_rows_lazy("gls").y.size
    orig = w.features.tree_features
    monkeypatch.setattr(w.features, "tree_features", lambda rows: orig(rows)[:, :-1])   # one column short
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 30)                                    # blocks of 10 rows x 3 columns
    first = min(10, n)
    with pytest.raises(FC.FitContextRefusal, match=r"R30.*returned shape \(%d, 2\) for %d rows \(one row block of the "
                                                   r"%d rows handed out\) of 3 tree columns" % (first, first, n)):
        make_context(w, 0, CutKind.GUARD).donor_rows("gls")
    lazy = make_context(w, 0, CutKind.GUARD).donor_rows_lazy("gls")           # a lazy read: its rows, as before
    with pytest.raises(FC.FitContextRefusal, match=r"R30.*returned shape \(4, 2\) for 4 rows of 3 tree columns"):
        lazy.X[np.arange(4)]


# ------------------------------------------------------------------------------------ end to end
def _model_bytes(model):
    rec = FW.weight_model_record(model)
    return (bits(model.forest.oob_sigma).tobytes(), model.forest.grid_rows.tobytes(), model.sigma_floor,
            model.clip_low, model.clip_high, model.cut, rec.value, rec.inputs, rec.input_hashes)


@pytest.mark.parametrize("blocks", [singles, pair])
def test_weight_model_for_cut_is_the_same_with_tiny_blocks(patched, monkeypatch, blocks):
    w = make_world()
    store, d, A = _store_for(w)
    fit_ctx, guard_ctx = make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD)
    ref = FW.weight_model_for_cut(fit_ctx, guard_ctx, store, tree_group(), blocks=blocks())
    seen = []
    orig = FW._blocked_group_error

    def spy(y, values, where):
        seen.append(len(FW._row_blocks(values.shape[0], values.shape[1])))
        return orig(y, values, where)
    monkeypatch.setattr(FW, "_blocked_group_error", spy)
    for block_values in (2, 9, 25):
        monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", block_values)
        seen.clear()
        got = FW.weight_model_for_cut(fit_ctx, make_context(w, 0, CutKind.GUARD), store, tree_group(),
                                      blocks=blocks())
        assert len(seen) == 3 and min(seen) > 1                              # every group's target in many blocks
        assert _model_bytes(got) == _model_bytes(ref), block_values
        assert got.cut == GUARD_CUT_0


# ------------------------------------------------------------------------------------ RAM
class _WideSource(object):
    """A FeatureSource of many float32 rows (NaN kept), as the pool hands them: a fresh copy a read."""

    def __init__(self, rows, cols):
        self._x = wide_answers(rows, cols, seed=5)
        self._x[::13, 3] = np.nan
        self.tree_columns = tuple("f%d" % i for i in range(cols))
        self.context_columns = ()

    def tree_features(self, grid_rows):
        return self._x[np.asarray(grid_rows, dtype=np.int64)]


def _peak(fn):
    tracemalloc.start()
    try:
        out = fn()
        return out, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_ram_the_blocked_build_holds_the_matrix_and_one_block(monkeypatch):
    rows, cols = 40000, 64
    ctx = FC.FitContext.__new__(FC.FitContext)          # only _features is read by the matrix build
    ctx._features = _WideSource(rows, cols)
    pos = np.arange(rows, dtype=np.int64)
    matrix = rows * cols * 4
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", rows * cols)                # one block: the old shape of the build
    one, peak_one = _peak(lambda: ctx._tree_feature_matrix(pos))
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 1000 * cols)                # 1000-row blocks
    many, peak_many = _peak(lambda: ctx._tree_feature_matrix(pos))
    assert many.tobytes() == one.tobytes()
    block = 1000 * cols
    assert peak_one >= 2 * matrix                                            # matrix + the read + a mask
    assert peak_many <= matrix + block * K.GLS_MATRIX_BUILD_BYTES_PER_VALUE + (1 << 16)
    est = FW.gls_ram_bytes({"g": rows}, cols, {"g": 1})
    assert est["build"] == matrix + 1000 * cols * K.GLS_MATRIX_BUILD_BYTES_PER_VALUE


def _real_pool_context(tmp_path, rows, tree_cols, context_cols, stack):
    """A FitContext whose feature source is a REAL FeaturePool (fit.pool: a float32 memmap of tree + context columns,
    read by sorted_gather: a gather and its reordered copy), NaN planted; only _features is read by the feature
    reads."""
    from treeroute.fit.pool import open_pool

    pool = stack.enter_context(open_pool(str(tmp_path), "blocks_probe", np.arange(rows, dtype=np.int64),
                                         ["t%d" % i for i in range(tree_cols)],
                                         ["c%d" % i for i in range(context_cols)]))
    tv = wide_answers(rows, tree_cols, seed=21)
    tv[::11, 2] = np.nan
    cv = wide_answers(rows, context_cols, seed=22) if context_cols else None
    pool.write(np.arange(rows, dtype=np.int64), tv, cv)
    del tv, cv
    ctx = FC.FitContext.__new__(FC.FitContext)
    ctx._features = pool
    return ctx


def test_ram_the_blocked_build_over_a_real_pool_is_under_the_build_constant(tmp_path, monkeypatch):
    """P2.gls_matrix_build_bytes_per_value against the engine's own feature source: the pool's gather and its
    reordered copy over tree + context columns (here 4 context columns for 64 tree columns), beside the matrix."""
    from contextlib import ExitStack

    rows, cols, ctx_cols = 30000, 64, 4
    with ExitStack() as stack:
        ctx = _real_pool_context(tmp_path, rows, cols, ctx_cols, stack)
        pos = np.arange(0, rows, 2, dtype=np.int64)                          # every other pool row, ascending
        matrix = pos.size * cols * 4
        monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 1000 * cols)            # 1000-row blocks
        gc.collect()
        many, peak = _peak(lambda: ctx._tree_feature_matrix(pos))
        ref = np.array(ctx._features.tree_features(pos), dtype=np.float32, copy=True)
        ref[np.isnan(ref)] = 0.0
        assert many.tobytes() == ref.tobytes()
        block = 1000 * cols
        assert peak >= matrix + block * 8                                     # the gather and its copy are seen
        assert peak <= matrix + block * K.GLS_MATRIX_BUILD_BYTES_PER_VALUE + (1 << 16)
        del ctx, many, ref
        gc.collect()


def test_ram_the_lazy_read_copies_after_the_source_returns(tmp_path):
    """A lazy hand-out's read (FitContext._tree_features) makes its float32 copy once the source's read has
    returned: its peak is the source's own (a pool's gather and its reordered copy, 8 bytes a value), not the copy
    beside it (12 bytes a value if the output were allocated before the read)."""
    from contextlib import ExitStack

    rows, cols = 20000, 64
    with ExitStack() as stack:
        ctx = _real_pool_context(tmp_path, rows, cols, 0, stack)
        pos = np.arange(rows, dtype=np.int64)
        gc.collect()
        X, peak = _peak(lambda: ctx._tree_features(pos))
        values = rows * cols
        assert X.dtype == np.float32 and X.shape == (rows, cols) and np.isfinite(X).all()
        assert peak >= values * 8                                             # the source's two copies are seen
        assert peak <= values * 9
        del ctx, X
        gc.collect()


def test_ram_the_blocked_target_holds_one_block_beside_the_read(monkeypatch):
    r, c = 6000, 300
    values = wide_answers(r, c, seed=9)
    where = np.flatnonzero(np.arange(c) % 5 != 0)
    y = np.zeros(r)
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 10 ** 9)                    # one block: the old whole-group target
    whole, peak_whole = _peak(lambda: FW._blocked_group_error(y, values, where))
    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 100 * c)                    # 100-row blocks
    blocked, peak_blocked = _peak(lambda: FW._blocked_group_error(y, values, where))
    assert np.array_equal(bits(blocked), bits(whole))
    sel = r * where.size
    assert peak_whole >= sel * (4 + 8)                                       # the column copy and its float64 copy
    assert peak_blocked <= 100 * c * K.GLS_ANSWER_BLOCK_BYTES_PER_CELL + r * 8 * 4 + (1 << 16)


@pytest.mark.parametrize("trees", [20, 150])
def test_ram_the_store_read_in_flight_is_the_answer_read_constant(patched, build_dir, trees):
    """P2.gls_answer_read_bytes_per_cell and P2.gls_answer_read_bytes_per_row: the donor-row pass reads a group's rows
    ONCE from the tree-answer store (fit.tables.TreeAnswerStore._read, through the per-group DropAfterRead view).
    While that read is in flight its float32 output and the table's gathered rows coexist (8 bytes a cell) beside its
    row-index arrays (at most 8 int64 a row; about 57-59 bytes a row measured at 40-800 columns). After the read only
    the output is held, which _blocked_group_error then reads in row blocks."""
    from treeroute.fit.tables import DropAfterRead, TreeAnswerStore
    from treeroute.runs.registry import Registry

    data = _rows()
    bank = _fit_bank(data, trees_per_group=trees)
    store = TreeAnswerStore(bank.trees, bank.tree_group, bank.correctors, bank.placebo_correctors,
                            bank.manifest.bank_fingerprint, true_group, build_dir, Registry(REGISTRY_DIR))
    try:
        per_group = DropAfterRead(store)
        ids = _group_ids(data, STORE_GROUPS[0])
        per_group.build(STORE_GROUPS[0], "plain", ids, Features(data["X"]))
        gc.collect()
        view, peak = _peak(lambda: per_group.unit_view(ids, "plain"))
        rows, cols = view.values.shape
        cells = rows * cols
        assert view.values.dtype == np.float32 and rows == ids.size and cols == 2 * trees
        assert peak >= 2 * view.values.nbytes                              # the output beside the gathered rows
        in_flight = cells * K.GLS_ANSWER_READ_BYTES_PER_CELL + rows * K.GLS_ANSWER_READ_BYTES_PER_ROW
        assert peak <= in_flight
        # gls_ram_bytes' in-flight term for this read (one block of the target holds the group here, so the larger
        # term is the held output beside its block; the in-flight term is checked on its own)
        est = FW.gls_ram_bytes({"g": rows}, 1, {"g": cols})
        assert est["answer_read"] - est["matrix"] >= in_flight
        del view
    finally:
        store.close()
        gc.collect()
