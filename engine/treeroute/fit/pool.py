"""The out-of-core feature pool (plan 4.1 step 3, 4.2 fit/ row): the joined, label-free feature
columns on the dense-grid rows of the picked units, held in ONE float32 memory-mapped temp matrix.
Boilerplate: it moves bytes and computes nothing.

Design, as the shipped pool (see the provenance comment):
  - rows are the dense-grid positions of the picked units (R18 picks them by a stride over sorted
    unit ids; that science lives in split.py, not here), kept sorted, so the pool's row order is
    the grid's order: unit by unit, step order;
  - writes go in ROW BLOCKS (whole rows, never column by column), one block of groups in RAM at a
    time, each row written exactly once, flushed after every write call so dirty pages leave RAM;
  - reads are a SORTED GATHER: the requested positions are read in ascending order (one forward
    pass over the disk) and returned in the order asked, as a copy;
  - the file lives in the machine's temp folder, named by runs/tempmem.py, and is released with its
    Windows-safe lifecycle: drop every reference, collect, then a loud delete. A refused delete
    raises; nothing is swallowed.
The pool keeps NaN as NaN: the R30 0-fill is applied by FitContext and the tree-answer store, never
here (FeatureSource contract). It holds no target label.

Usage:
    with open_pool(temp_dir, "pool", grid_rows, tree_columns, context_columns) as pool:
        for block_rows, tree_block, context_block in blocks:     # sorted rows per block
            pool.write(block_rows, tree_block, context_block)
        pool.require_complete()
        X = pool.tree_features(some_grid_rows)
"""
# Provenance for the module: pm25_architecture.py:202-248 (build_pool: stream one region at a time
# into a float32 'w+' memmap, 50,000-row slabs, flush per region, row blocks never columns) and
# :251-260 (gather: idx sorted first, one ascending pass over the HDD); pm25_adaptation.py:531-534
# (stride over sorted cell codes, now split.stride_pick, R18) and :558-567 (rows sorted by unit and
# step before any table is written); plan 5 G-DISK (one temp-matrix lifecycle, row-block writers).

from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence, Tuple

import numpy as np

from treeroute.errors import RefusedError
from treeroute.runs.tempmem import temp_memmap

# Rows per write slab. Memory only: it never changes a stored byte.
# origin: pm25_architecture.py:228-230 (range(0, n, 50000) slabs)
POOL_WRITE_BLOCK_ROWS = 50000
POOL_DTYPE = "float32"


class PoolRefusal(RefusedError):
    """The pool refused a write or a read (G-DISK, G-JOIN). Nothing catches it to carry on."""


def _sorted_unique_rows(grid_rows: Any, what: str) -> np.ndarray:
    rows = np.asarray(grid_rows)
    if rows.ndim != 1 or rows.size == 0:
        raise PoolRefusal("G-DISK", "%s must be a non-empty 1-D array" % what)
    if rows.dtype == np.bool_ or not np.issubdtype(rows.dtype, np.integer):
        raise PoolRefusal("G-DISK", "%s must hold integer grid positions, got %s" % (what, rows.dtype))
    rows = rows.astype(np.int64, copy=False)
    if int(rows.min()) < 0:
        raise PoolRefusal("G-DISK", "%s holds a negative grid position" % what)
    if np.any(np.diff(rows) <= 0):
        raise PoolRefusal("G-DISK", "%s must be sorted ascending without repeats" % what,
                          fix="sort the block's grid rows (the pool keeps the grid's row order)")
    return rows


def _column_names(columns: Sequence[str], what: str) -> Tuple[str, ...]:
    names = tuple(columns)
    if not all(isinstance(c, str) and c for c in names):
        raise PoolRefusal("G-DISK", "%s must be non-empty strings" % what)
    if len(set(names)) != len(names):
        raise PoolRefusal("G-DISK", "%s repeat a name" % what)
    return names


def sorted_gather(array: Any, positions: Any) -> np.ndarray:
    """Rows ``positions`` of ``array`` (a memmap or any 2-D array) as a NEW in-RAM array, in the
    order given. The rows are read in ascending order (one forward pass over the file); repeats
    are allowed. No alias to ``array`` escapes."""
    pos = np.asarray(positions, dtype=np.int64)
    if pos.ndim != 1:
        raise PoolRefusal("G-DISK", "gather positions must be 1-D")
    order = np.argsort(pos, kind="stable")
    data = np.asarray(array[pos[order]])       # fancy indexing reads a copy, ascending
    out = np.empty_like(data)
    out[order] = data
    del data
    return out


class FeaturePool(object):
    """Tree features and router context on the pool's grid rows (a FeatureSource).

    Built only by open_pool. Attributes: tree_columns, context_columns, grid_rows (sorted)."""

    def __init__(self, holder: Any, grid_rows: np.ndarray, tree_columns: Tuple[str, ...],
                 context_columns: Tuple[str, ...]) -> None:
        self._holder = holder
        self.grid_rows = grid_rows
        self.tree_columns = tree_columns
        self.context_columns = context_columns
        self._n_tree = len(tree_columns)
        self._written = np.zeros(len(grid_rows), dtype=bool)

    # -- bookkeeping -----------------------------------------------------------------------------
    @property
    def n_rows(self) -> int:
        return int(len(self.grid_rows))

    @property
    def path(self) -> Any:
        return self._holder.path

    def missing_rows(self) -> np.ndarray:
        """Grid rows not written yet."""
        return self.grid_rows[~self._written]

    def require_complete(self) -> None:
        """Refuse unless every pool row has been written."""
        missing = int(np.sum(~self._written))
        if missing:
            raise PoolRefusal("G-DISK", "%d of %d pool rows were never written (first grid row %d)"
                              % (missing, self.n_rows, int(self.missing_rows()[0])))

    def _positions(self, grid_rows: Any, what: str, require_written: bool) -> np.ndarray:
        rows = np.asarray(grid_rows)
        if rows.ndim != 1:
            raise PoolRefusal("G-DISK", "%s must be 1-D" % what)
        if rows.size == 0:
            return np.zeros(0, dtype=np.int64)
        if rows.dtype == np.bool_ or not np.issubdtype(rows.dtype, np.integer):
            raise PoolRefusal("G-DISK", "%s must hold integer grid positions, got %s"
                              % (what, rows.dtype))
        rows = rows.astype(np.int64, copy=False)
        pos = np.searchsorted(self.grid_rows, rows)
        inside = pos < len(self.grid_rows)
        ok = np.zeros(len(rows), dtype=bool)
        ok[inside] = self.grid_rows[pos[inside]] == rows[inside]
        if not ok.all():
            raise PoolRefusal("G-JOIN", "%d %s are not rows of this pool (first %d)"
                              % (int(np.sum(~ok)), what, int(rows[~ok][0])))
        if require_written and not self._written[pos].all():
            raise PoolRefusal("G-DISK", "%d %s were never written"
                              % (int(np.sum(~self._written[pos])), what))
        return pos

    # -- writes ----------------------------------------------------------------------------------
    def write(self, grid_rows: Any, tree_values: Any, context_values: Optional[Any] = None) -> None:
        """Write whole rows: ``tree_values`` (rows x tree columns) and ``context_values`` (rows x
        context columns; None when the pool has no context column), cast to float32, NaN kept.

        ``grid_rows`` must be sorted ascending without repeats, rows of this pool, and not written
        before (each pool row is written exactly once). The block goes to disk in slabs of
        POOL_WRITE_BLOCK_ROWS whole rows and is flushed before this call returns."""
        rows = _sorted_unique_rows(grid_rows, "block grid rows")
        pos = self._positions(rows, "block grid rows", require_written=False)
        if self._written[pos].any():
            raise PoolRefusal("G-DISK", "%d block rows were already written (first grid row %d)"
                              % (int(np.sum(self._written[pos])),
                                 int(rows[self._written[pos]][0])),
                              fix="each pool row is written exactly once")
        m = len(rows)
        tv = np.asarray(tree_values)
        if tv.shape != (m, self._n_tree):
            raise PoolRefusal("G-DISK", "tree values have shape %s, expected (%d, %d)"
                              % (tv.shape, m, self._n_tree))
        n_ctx = len(self.context_columns)
        if n_ctx == 0:
            if context_values is not None and np.asarray(context_values).size != 0:
                raise PoolRefusal("G-DISK", "the pool has no context column; got context values")
            cv = None
        else:
            if context_values is None:
                raise PoolRefusal("G-DISK", "context values are missing for %d context columns"
                                  % n_ctx)
            cv = np.asarray(context_values)
            if cv.shape != (m, n_ctx):
                raise PoolRefusal("G-DISK", "context values have shape %s, expected (%d, %d)"
                                  % (cv.shape, m, n_ctx))
        block = np.empty((m, self._n_tree + n_ctx), dtype=POOL_DTYPE)
        block[:, :self._n_tree] = tv
        if cv is not None:
            block[:, self._n_tree:] = cv
        del tv, cv
        arr = self._holder.array
        try:
            for a0 in range(0, m, POOL_WRITE_BLOCK_ROWS):
                b0 = min(a0 + POOL_WRITE_BLOCK_ROWS, m)
                p = pos[a0:b0]
                if int(p[-1]) - int(p[0]) == len(p) - 1:      # contiguous: one slab
                    arr[int(p[0]):int(p[-1]) + 1] = block[a0:b0]
                else:                                          # whole rows, ascending
                    arr[p] = block[a0:b0]
            arr.flush()
        finally:
            del arr
        self._written[pos] = True

    # -- reads (FeatureSource) -------------------------------------------------------------------
    def _gather(self, grid_rows: Any, what: str) -> np.ndarray:
        pos = self._positions(grid_rows, what, require_written=True)
        arr = self._holder.array
        try:
            return sorted_gather(arr, pos)
        finally:
            del arr

    def tree_features(self, grid_rows: Any) -> np.ndarray:
        """Tree features on the given grid rows, float32, NaN kept, in the order given (a copy)."""
        return np.ascontiguousarray(self._gather(grid_rows, "grid rows")[:, :self._n_tree])

    def context(self, grid_rows: Any) -> np.ndarray:
        """Router context columns on the given grid rows, float32, NaN kept, in the order given."""
        return np.ascontiguousarray(self._gather(grid_rows, "grid rows")[:, self._n_tree:])

    def _close(self) -> None:
        self._holder = _Released()


class _Released(object):
    """Stands in for the temp matrix after the pool is released: every use refuses."""

    @property
    def array(self):
        raise PoolRefusal("G-DISK", "the pool was released")

    @property
    def path(self):
        raise PoolRefusal("G-DISK", "the pool was released")


@contextmanager
def open_pool(temp_dir: Any, tag: str, grid_rows: Any, tree_columns: Sequence[str],
              context_columns: Sequence[str] = ()) -> Iterator[FeaturePool]:
    """Create the pool's temp matrix (a NEW file in ``temp_dir``), yield the FeaturePool, and always
    release it: references dropped, collected, then a loud delete (runs/tempmem.py). A caller that
    kept an alias of pool internals makes the release refuse, leaving the file for preflight."""
    rows = np.array(_sorted_unique_rows(grid_rows, "pool grid rows"), dtype=np.int64, copy=True)
    rows.setflags(write=False)          # the pool's own read-only copy of its row keys
    tcols = _column_names(tree_columns, "tree columns")
    ccols = _column_names(context_columns, "context columns")
    if not tcols:
        raise PoolRefusal("G-DISK", "the pool needs at least one tree column")
    with temp_memmap(temp_dir, tag, (len(rows), len(tcols) + len(ccols)), POOL_DTYPE) as holder:
        pool = FeaturePool(holder, rows, tcols, ccols)
        try:
            yield pool
        finally:
            pool._close()
            del pool
