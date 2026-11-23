"""The out-of-core feature pool: row-block writes, sorted gather, write-once, NaN kept, and the
Windows-safe release (drop refs, collect, loud delete) of runs/tempmem.py."""

import numpy as np
import pytest

from treeroute.errors import TempMatrixError
from treeroute.fit import pool as PL
from treeroute.fit.pool import PoolRefusal, open_pool, sorted_gather

TREE_COLS = ("a", "b", "c")
CTX_COLS = ("s", "t")


def _values(rows):
    rows = np.asarray(rows, dtype=np.float64)
    tree = np.stack([rows * 1.5, rows + 0.25, -rows], axis=1)
    ctx = np.stack([rows / 7.0, np.full(len(rows), 3.0)], axis=1)
    return tree, ctx


def test_write_blocks_then_gather_in_any_order(tmp_path):
    grid_rows = np.array([3, 4, 5, 10, 11, 40, 41, 42, 99])
    with open_pool(tmp_path, "pool", grid_rows, TREE_COLS, CTX_COLS) as pool:
        assert pool.path.exists() and pool.path.parent == tmp_path
        first, second = grid_rows[:5], grid_rows[5:]
        pool.write(first, *_values(first))
        assert pool.missing_rows().tolist() == [40, 41, 42, 99]
        with pytest.raises(PoolRefusal):
            pool.require_complete()
        pool.write(second, *_values(second))
        pool.require_complete()
        ask = np.array([99, 3, 41, 3, 10])
        tree, ctx = _values(ask)
        got_tree, got_ctx = pool.tree_features(ask), pool.context(ask)
        path = pool.path
    assert got_tree.dtype == np.float32 and got_tree.flags["C_CONTIGUOUS"]
    assert np.array_equal(got_tree, tree.astype(np.float32))
    assert np.array_equal(got_ctx, ctx.astype(np.float32))
    assert not path.exists()                     # released and deleted


def test_nan_is_kept_and_values_are_cast_to_float32(tmp_path):
    rows = np.array([0, 1, 2])
    tree = np.array([[np.nan, 1.0, 2.0], [0.1, np.nan, 3.0], [1e-45, 2.0, 1 / 3]])
    with open_pool(tmp_path, "nan", rows, TREE_COLS) as pool:
        pool.write(rows, tree)
        got = pool.tree_features(rows)
        assert pool.context(rows).shape == (3, 0)
    assert np.array_equal(np.isnan(got), np.isnan(tree))
    assert np.array_equal(got[~np.isnan(got)], tree.astype(np.float32)[~np.isnan(tree)])


def test_large_blocks_are_written_in_slabs_contiguous_or_not(tmp_path, monkeypatch):
    monkeypatch.setattr(PL, "POOL_WRITE_BLOCK_ROWS", 4)
    rows = np.concatenate([np.arange(0, 10), np.arange(20, 40, 2)])   # a run, then gaps
    with open_pool(tmp_path, "slabs", rows, TREE_COLS, CTX_COLS) as pool:
        pool.write(rows, *_values(rows))
        tree, ctx = _values(rows[::-1])
        assert np.array_equal(pool.tree_features(rows[::-1]), tree.astype(np.float32))
        assert np.array_equal(pool.context(rows[::-1]), ctx.astype(np.float32))


def test_write_refusals(tmp_path):
    rows = np.array([1, 2, 3, 4])
    with open_pool(tmp_path, "refuse", rows, TREE_COLS, CTX_COLS) as pool:
        with pytest.raises(PoolRefusal):
            pool.write(np.array([2, 1]), *_values([2, 1]))                # not sorted
        with pytest.raises(PoolRefusal):
            pool.write(np.array([1, 1]), *_values([1, 1]))                # repeats
        with pytest.raises(PoolRefusal):
            pool.write(np.array([1, 7]), *_values([1, 7]))                # not a pool row
        with pytest.raises(PoolRefusal):
            pool.write(np.array([1, 2]), np.zeros((2, 2)), np.zeros((2, 2)))   # wrong width
        with pytest.raises(PoolRefusal):
            pool.write(np.array([1, 2]), np.zeros((2, 3)))                # context missing
        pool.write(np.array([1, 2]), *_values([1, 2]))
        with pytest.raises(PoolRefusal) as info:
            pool.write(np.array([2, 3]), *_values([2, 3]))                # written twice
        assert "exactly once" in str(info.value)
        with pytest.raises(PoolRefusal):
            pool.tree_features(np.array([3]))                             # never written
        with pytest.raises(PoolRefusal):
            pool.tree_features(np.array([9]))                             # not a pool row
        assert pool.tree_features(np.array([], dtype=np.int64)).shape == (0, 3)


def test_open_refusals(tmp_path):
    for rows in (np.array([]), np.array([2, 1]), np.array([1.0, 2.0]), np.array([-1, 0])):
        with pytest.raises(PoolRefusal):
            with open_pool(tmp_path, "bad", rows, TREE_COLS):
                pass
    with pytest.raises(PoolRefusal):
        with open_pool(tmp_path, "bad", np.array([1]), ("a", "a")):
            pass
    with pytest.raises(PoolRefusal):
        with open_pool(tmp_path, "bad", np.array([1]), ()):
            pass
    with pytest.raises(TempMatrixError):
        with open_pool(tmp_path / "missing", "bad", np.array([1]), TREE_COLS):
            pass
    assert list(tmp_path.iterdir()) == []        # nothing left behind


def test_pool_rows_are_a_private_read_only_copy(tmp_path):
    rows = np.array([5, 6, 7])
    with open_pool(tmp_path, "copy", rows, TREE_COLS) as pool:
        rows[0] = 99                              # the caller's array is not the pool's key
        assert pool.grid_rows.tolist() == [5, 6, 7]
        with pytest.raises(ValueError):
            pool.grid_rows[0] = 1


def test_released_pool_refuses_every_use_and_the_file_is_gone(tmp_path):
    rows = np.array([0, 1])
    with open_pool(tmp_path, "gone", rows, TREE_COLS) as pool:
        pool.write(rows, np.ones((2, 3)))
        path = pool.path
    assert not path.exists()
    with pytest.raises(PoolRefusal):
        pool.tree_features(rows)
    with pytest.raises(PoolRefusal):
        pool.write(rows, np.ones((2, 3)))


def test_body_exception_still_deletes_the_file(tmp_path):
    with pytest.raises(RuntimeError):
        with open_pool(tmp_path, "boom", np.array([0, 1]), TREE_COLS) as pool:
            path = pool.path
            raise RuntimeError("body failed")
    assert not path.exists()


def test_sorted_gather_reads_ascending_and_returns_in_the_order_asked():
    class Recorder(object):
        def __init__(self, a):
            self.a, self.seen = a, []

        def __getitem__(self, idx):
            self.seen.append(np.array(idx))
            return self.a[idx]

    base = np.arange(20, dtype=np.float32).reshape(10, 2)
    rec = Recorder(base)
    got = sorted_gather(rec, [7, 2, 9, 2])
    assert np.array_equal(got, base[[7, 2, 9, 2]])
    assert rec.seen[0].tolist() == [2, 2, 7, 9]
    got[0, 0] = -1.0
    assert base[7, 0] == 14.0                    # a copy, never an alias
