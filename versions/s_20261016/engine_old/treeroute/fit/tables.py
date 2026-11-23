"""treeroute.fit.tables: the row-keyed tree-answer store and its parallel row-block writer.

Plan 2.3 R20 and 4.5 (speedups 1 and 2), with the owner rulings on speed, on sklearnex and on the
leave-one-region-out split (OWNER_RULINGS section C and section D). Boilerplate gated by byte
identity: nothing here may change a number.

What the store does
  - Every tree's answer on a requested row is computed ONCE, keyed by the row id, and read back by
    every later pass (speedup 1). A build that names rows already in the table computes only the
    new ones. The row id is the caller's unique integer key of a row: for grids it stands for
    unit + step, for events for unit + event date + issue date (R20).
  - Tables are built per group, in row blocks of ROW_BLOCK_ROWS rows, and kept on disk as Windows-
    safe temp memmaps (runs/tempmem.py) in the temp dir the caller gives. A table is keyed by
    (group, kind); kinds are 'plain', 'corrector' and 'placebo_corrector' (the tool values of R24;
    trees-off has no table).
  - Leave-one-region-out: a group's table holds the columns of every tree EXCEPT that group's own
    trees. The own-group columns are never computed, so they cannot be read; every view asserts it.
    Columns keep the bank's tree order.
  - A row id belongs to one group only, and the store checks WHICH group from the caller's row-group
    source (row_group(ids) -> the group name of each row; for grids it reads the grid's unit ->
    group key). A build is refused, before anything is computed, when any requested row belongs to
    a group other than the build group by that source, or was already built under another group:
    such a row would be answered by its own group's trees.

The parallel writer (plan 4.5, speedup 2; the speed proof's changes (a) and (e))
  - For each row block, the table's columns are cut into contiguous ranges, one per tree worker
    (engine constant TREE_PREDICT_WORKERS). Each worker runs the shipped per-tree lines into its own
    columns of one block buffer; the block then goes to disk as one slab and is flushed.
  - The finiteness scan runs ONCE per block, in the calling thread: the same function a tree's
    predict() calls (sklearn.utils.validation._assert_all_finite, looked up at call time, so it is
    the sklearnex version when sklearn is patched), with the allow_nan that predict() would pass.
    The workers then predict under sklearn's thread-local assume_finite. Bad input still stops the
    run: the scan raises, as predict() would.
  - A tree's answer depends only on the tree and the row, so the bytes are the same for any worker
    count, any block size and with the scan once per block or once per tree. The tests prove it.

Runtime guards (fail loudly; ScanOnceGuardError)
  - sklearn must be patched by sklearnex (owner ruling: patched globally at start-up by the
    launcher). An unpatched process is refused.
  - Once per process: sklearn's assume_finite set in one thread is not seen by another, and the
    scan still refuses an inf in the calling thread meanwhile, on a small and on a large block
    (sklearnex scans the two sizes with different code).
  - Every block: the calling thread's assume_finite must be off before the scan runs.
  - First block of every build: the first and last columns are recomputed with the ordinary
    per-tree predict() (full input checks) and must match the written bytes.
  - The library versions the scan-once path relies on are recorded (record()); the pins and the
    checks of the private internals live in tests/test_fit_tables_guard.py.

Temp files
  Every table segment is a NEW temp memmap made by runs/tempmem.temp_memmap (named with the pid, so
  preflight sees an orphan). No alias to a memmap ever leaves this module: reads return copies.
  drop() and close() release the files loudly: references dropped, gc run, then the delete, and any
  failure raises. The temp dir must pass the shipped-results registry (G-NOOVERWRITE) and hold no
  orphan engine temp file (G-DISK). Disk and RAM decide go or refuse only, per segment.

Threads: build(), drop() and close() run one at a time (a lock enforces it). Reads may run from
several threads, also while a build is running: a table's row lookup (keys, segment and position
of every row, and the segment list) is ONE immutable snapshot that a build replaces in a single
assignment, and a read takes it once, so a read sees the table as it was before the build or after
it, never half-indexed. drop() and close() hold new reads back, wait for the reads in flight to
finish, and only then release the files.
"""
# Provenance: pm25_adaptation.py:655-693 (the shipped row-block writer: float32, ROW_BLOCK rows per
# block, one slab write and flush per block, corrector column = tree + ETA x corrector with ETA 1.0
# at :202); engine/speedproof/pm25_adaptation_fast.py:783-857 (the proven parallel writer, changes
# (a) and (e)); engine/speedproof/probe_finite_scan.py (guards G-a to G-c); SPEEDPROOF_REPORT.md
# open item 1 option (a); OWNER_RULINGS_2026-09-28.md C (speed, sklearnex) and D (leave one region
# out). Temp dir for the build agents' tests and smokes: D:/treeroute/fit_build/.

import itertools
import threading
import time
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from treeroute import engine_constants as K
from treeroute.errors import RefusedError, TreerouteError
from treeroute.runs import preflight
from treeroute.runs.room import wait_for_room
from treeroute.runs.tempmem import temp_memmap

PLAIN = "plain"
CORRECTOR = "corrector"
PLACEBO_CORRECTOR = "placebo_corrector"
TABLE_KINDS = (PLAIN, CORRECTOR, PLACEBO_CORRECTOR)
_KIND_TAG = {PLAIN: "plain", CORRECTOR: "corr", PLACEBO_CORRECTOR: "plac"}

ANSWER_DTYPE = np.dtype(K.TREE_DTYPE)
ROW_ID_DTYPE = np.dtype(np.int64)
# origin: pm25_adaptation.py:448 (ROW_BLOCK = 12288, ruling R2: about 0.53 GB of block buffer at
# 10,700 trees). The block size cannot change a number (a tree answers each row on its own; the
# tests build with other sizes and compare bytes). A store reads it once, when it is made.
# OWNER CONFIRMS whether it moves to C14.
ROW_BLOCK_ROWS = 12288

# sklearnex scans a block of fewer than this many values with sklearn's own code and a larger one
# with oneDAL's (daal4py.sklearn.utils.validation._assert_all_finite, scikit-learn-intelex
# 2025.10.0). The self-check probes one block of each kind.
_LARGE_PROBE_SHAPE = (512, 64)
_SMALL_PROBE_SHAPE = (4, 4)
_SELF_CHECK_WAIT_SECONDS = 60.0

# TEST ONLY. The engine always writes with TREE_PREDICT_WORKERS workers and the scan once per block
# (plan 4.5: the 'off' path exists only inside tests, never as a flag). Tests set a pair
# (workers, scan_once) here BEFORE making a store to prove the bytes do not move. A store reads the
# mode once, when it is made, and uses it for every build; record() shows that mode, whether it
# came from here, and the mode of every build.
_TEST_ONLY_WRITER = None

_STORE_SERIAL = itertools.count()
_SELF_CHECK = {"passed": False}
_SELF_CHECK_LOCK = threading.Lock()


class TableRefusal(RefusedError):
    """The tree-answer store refused a request. The rule id names the door (R20, C14, G-DISK, D)."""


class ScanOnceGuardError(TreerouteError):
    """A runtime guard of the once-per-block finiteness scan, or of the leave-one-region-out
    columns, failed. The run stops; no answer from that build is kept."""


@dataclass(frozen=True)
class AnswerView(object):
    """Tree answers for one group's rows (a unit's view).

    values      float32 (rows, columns), rows in the order asked; a copy the caller owns
    tree_index  int64 (columns,), the bank position of each column, ascending; the group's own
                trees are never among them
    group       the group the rows belong to (its trees are the excluded columns)
    kind        the table kind
    """
    values: np.ndarray
    tree_index: np.ndarray
    group: str
    kind: str


# ---------------------------------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------------------------------
def row_key_hash(row_ids):
    """SHA-256 of the row ids as little-endian int64, in the order given (for manifests and logs)."""
    import hashlib

    ids = np.ascontiguousarray(np.asarray(row_ids), dtype="<i8")
    return hashlib.sha256(ids.tobytes()).hexdigest()


def _kind_value(kind):
    value = getattr(kind, "value", kind)
    if value not in TABLE_KINDS:
        raise TableRefusal("R20", "unknown table kind %r" % (kind,),
                           fix="ask for one of %s; trees-off has no tree table" % ", ".join(TABLE_KINDS))
    return value


def _group_name(group):
    if not isinstance(group, str) or not group:
        raise TableRefusal("R20", "a group must be a non-empty string, got %r" % (group,))
    return group


def _as_row_ids(row_ids, what, unique):
    arr = np.asarray(row_ids)
    if arr.ndim != 1:
        raise TableRefusal("R20", "%s must be one-dimensional, got shape %s" % (what, arr.shape))
    if arr.size == 0:
        raise TableRefusal("R20", "%s is empty" % what,
                           fix="ask only for rows that exist; an empty request is a caller bug")
    if arr.dtype.kind not in "iu":
        raise TableRefusal("R20", "%s must hold integer row ids, got dtype %s" % (what, arr.dtype))
    if arr.dtype.kind == "u" and int(arr.max()) > np.iinfo(ROW_ID_DTYPE).max:
        raise TableRefusal("R20", "%s holds a row id above the int64 range" % what)
    ids = arr.astype(ROW_ID_DTYPE, copy=True)
    if int(ids.min()) < 0:
        raise TableRefusal("R20", "%s holds a negative row id (%d)" % (what, int(ids.min())))
    if unique:
        uniq = np.unique(ids)
        if uniq.size != ids.size:
            raise TableRefusal("R20", "%s repeats %d row id(s); each row is built once"
                               % (what, ids.size - uniq.size))
    return ids


def _member(sorted_keys, ids):
    """Boolean mask: which ids are in the sorted unique array ``sorted_keys``."""
    if sorted_keys.size == 0:
        return np.zeros(ids.shape, dtype=bool)
    pos = np.searchsorted(sorted_keys, ids)
    pos_c = np.minimum(pos, sorted_keys.size - 1)
    return sorted_keys[pos_c] == ids


def _column_chunks(n_columns, workers):
    """Contiguous column ranges, one per worker (the speed proof's cuts)."""
    nw = max(1, min(int(workers), int(n_columns)))
    cuts = [n_columns * i // nw for i in range(nw + 1)]
    return [(cuts[i], cuts[i + 1]) for i in range(nw) if cuts[i + 1] > cuts[i]]


def _writer_mode():
    """(workers, scan_once) the writer uses: the engine constant and the scan once per block."""
    if _TEST_ONLY_WRITER is None:
        return int(K.TREE_PREDICT_WORKERS), True
    workers, scan_once = _TEST_ONLY_WRITER
    if int(workers) < 1:
        raise ValueError("test writer mode needs at least one worker, got %r" % (workers,))
    return int(workers), bool(scan_once)


def _uint_view(values):
    return values.view(np.uint32)


# ---------------------------------------------------------------------------------------------------
# backend: sklearnex patch, versions, the once-per-process self-check
# ---------------------------------------------------------------------------------------------------
def _require_patched():
    """Refuse unless sklearn is patched by sklearnex (owner ruling: patched globally at start-up)."""
    try:
        import sklearnex
    except Exception as exc:  # no silent fallback to plain sklearn
        raise TableRefusal("C14", "sklearnex could not be imported: %s: %s" % (type(exc).__name__, exc),
                           fix="install the pinned scikit-learn-intelex") from exc
    if not sklearnex.sklearn_is_patched():
        raise TableRefusal(
            "C14", "sklearn is not patched by sklearnex. The owner ruled that sklearnex patches sklearn "
            "globally at start-up, as the shipped runs did; tree answers are only written in that "
            "state, so the finiteness scan is the one the shipped runs used.",
            fix="start the engine through its launcher (py -3.9 -m treeroute), which patches sklearn "
                "after pinning the thread pools")


def backend_versions():
    """The library versions and functions the scan-once path relies on (recorded, never compared
    here; the pins are in tests/test_fit_tables_guard.py)."""
    from importlib import metadata

    import sklearn
    import sklearn.utils.validation as skval

    try:
        sklearnex_version = metadata.version("scikit-learn-intelex")
    except Exception:  # recorded as missing; _require_patched refuses the run anyway
        sklearnex_version = None
    try:
        import sklearnex

        patched = bool(sklearnex.sklearn_is_patched())
    except Exception:
        patched = False
    scan = skval._assert_all_finite
    ctx = sklearn.config_context
    return {
        "scikit-learn": sklearn.__version__,
        "scikit-learn-intelex": sklearnex_version,
        "numpy": np.__version__,
        "sklearn_patched": patched,
        "finite_scan": "%s.%s" % (scan.__module__, scan.__qualname__),
        "config_context": "%s.%s" % (ctx.__module__, ctx.__qualname__),
    }


def _self_check_scan_once():
    """Once per process: the behaviour the scan-once path relies on (see the module docstring)."""
    with _SELF_CHECK_LOCK:
        if _SELF_CHECK["passed"]:
            return
        import sklearn
        import sklearn.utils.validation as skval

        small = np.zeros(_SMALL_PROBE_SHAPE, dtype=np.float32)
        small[1, 2] = np.inf
        large = np.zeros(_LARGE_PROBE_SHAPE, dtype=np.float32)
        large[-1, -1] = np.inf
        seen = {}
        entered = threading.Event()
        release = threading.Event()

        def other_thread():
            try:
                with sklearn.config_context(assume_finite=True):
                    seen["inside"] = bool(sklearn.get_config()["assume_finite"])
                    entered.set()
                    release.wait(_SELF_CHECK_WAIT_SECONDS)
            except BaseException as exc:  # reported below, never swallowed
                seen["error"] = "%s: %s" % (type(exc).__name__, exc)
                entered.set()

        probe = threading.Thread(target=other_thread, name="treeroute-scan-self-check", daemon=True)
        probe.start()
        problems = []
        try:
            if not entered.wait(_SELF_CHECK_WAIT_SECONDS):
                problems.append("the probe thread did not enter sklearn.config_context")
            elif "error" in seen:
                problems.append("the probe thread failed: %s" % seen["error"])
            else:
                if seen.get("inside") is not True:
                    problems.append("config_context(assume_finite=True) did not set the flag in its "
                                    "own thread")
                if sklearn.get_config()["assume_finite"]:
                    problems.append("assume_finite set in another thread is seen by this thread "
                                    "(sklearn's config is not thread-local any more)")
                for label, block in (("small", small), ("large", large)):
                    try:
                        skval._assert_all_finite(block, allow_nan=True, input_name="X")
                    except ValueError:
                        continue
                    problems.append("the finiteness scan let an inf through in a %s block while "
                                    "another thread held assume_finite" % label)
        finally:
            release.set()
            probe.join(_SELF_CHECK_WAIT_SECONDS)
        if probe.is_alive():
            problems.append("the probe thread did not finish")
        if problems:
            raise ScanOnceGuardError(
                "the once-per-block finiteness scan cannot be trusted in this process: %s. The "
                "sklearn or sklearnex internals it relies on have changed; run "
                "tests/test_fit_tables_guard.py and do not write tree answers until it passes."
                % "; ".join(problems))
        _SELF_CHECK["passed"] = True


# ---------------------------------------------------------------------------------------------------
# the parallel row-block writer
# ---------------------------------------------------------------------------------------------------
def _fill_body(pairs, V, buf, m, lo, hi):
    """The shipped per-tree lines for columns lo..hi-1 of one block (corrector: tree + corrector)."""
    for c in range(lo, hi):
        tree, extra = pairs[c]
        p = tree.predict(V).astype(np.float32)
        if extra is not None:
            # the shipped line is p + ETA x corrector with ETA 1.0; 1.0 x c equals c bit for bit
            p = p + extra.predict(V).astype(np.float32)
        buf[:m, c] = p


def _fill_columns(pairs, V, buf, m, lo, hi, assume_finite):
    if assume_finite:
        import sklearn

        # sklearn's config is THREAD-LOCAL: this affects only the thread running these columns
        with sklearn.config_context(assume_finite=True):
            _fill_body(pairs, V, buf, m, lo, hi)
    else:
        _fill_body(pairs, V, buf, m, lo, hi)


def _scan_block(V, allow_nan, estimator_name):
    """The finiteness check every predict() would run on V, once, in the calling thread."""
    import sklearn
    import sklearn.utils.validation as skval

    if sklearn.get_config()["assume_finite"]:
        raise ScanOnceGuardError(
            "sklearn's assume_finite is on in the thread that scans the row block, so the scan "
            "would return without checking and bad input would reach the trees unchecked")
    skval._assert_all_finite(V, input_name="X", estimator_name=estimator_name, allow_nan=allow_nan)


def _answer_block(pairs, V, buf, allow_nan, estimator_name, chunks, scan_once, executor):
    """Fill buf[:len(V), :] with every column's answer on the block V."""
    m = V.shape[0]
    if scan_once:
        _scan_block(V, allow_nan, estimator_name)
    if executor is None or len(chunks) == 1:
        _fill_columns(pairs, V, buf, m, 0, len(pairs), scan_once)
        return
    futures = [executor.submit(_fill_columns, pairs, V, buf, m, lo, hi, scan_once)
               for lo, hi in chunks]
    for future in futures:
        future.result()  # re-raises a worker's error here; the caller shuts the pool down


def _spot_check(pairs, V, buf, m):
    """Runtime guard: the first and last columns again, by the ordinary per-tree predict()."""
    for c in sorted({0, len(pairs) - 1}):
        tree, extra = pairs[c]
        p = tree.predict(V).astype(np.float32)
        if extra is not None:
            p = p + extra.predict(V).astype(np.float32)
        if not np.array_equal(_uint_view(p), _uint_view(buf[:m, c])):
            raise ScanOnceGuardError(
                "column %d of the first row block differs from the ordinary per-tree predict(); the "
                "parallel writer or the once-per-block scan changed a number, so nothing from this "
                "build is kept" % c)


def _write_slab(tm, start, block):
    """One contiguous slab of whole rows into the memmap, then flush (no alias survives)."""
    arr = tm.array
    try:
        arr[start:start + block.shape[0], :] = block
        arr.flush()  # hand the dirty pages back per block, or RSS grows to the whole file
    finally:
        del arr


def _read_rows(tm, rows):
    """A copy of the given (sorted) rows of a segment (no alias survives)."""
    arr = tm.array
    try:
        part = arr[rows]
    finally:
        del arr
    if type(part) is not np.ndarray:
        part = np.array(part, copy=True)
    return part


# ---------------------------------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------------------------------
class _Segment(object):
    def __init__(self, row_ids, tm, owner):
        self.row_ids = row_ids
        self.tm = tm
        self.owner = owner  # ExitStack whose close() releases tm loudly


# One table's row lookup, as ONE immutable snapshot: keys (sorted row ids), seg and pos (the segment
# and the row inside it of each key) and segments (a tuple). A build makes a new snapshot and swaps
# it in with a single assignment; a read takes the snapshot once and uses nothing else, so it never
# sees new keys with old positions (the race of three separate assignments).
_Index = namedtuple("_Index", ("keys", "seg", "pos", "segments"))


def _frozen(arr):
    arr.flags.writeable = False
    return arr


def _empty_index():
    return _Index(_frozen(np.empty(0, dtype=ROW_ID_DTYPE)), _frozen(np.empty(0, dtype=np.int64)),
                  _frozen(np.empty(0, dtype=np.int64)), ())


class _Table(object):
    def __init__(self, group, kind, code, tree_index, own_index, allow_nan):
        self.group = group
        self.kind = kind
        self.code = code
        self.tree_index = tree_index
        self.own_index = own_index
        self.allow_nan = allow_nan
        self.index = _empty_index()
        self.builds: List[Dict[str, Any]] = []
        self.dropped = False

    @property
    def n_columns(self):
        return int(self.tree_index.size)

    @property
    def n_rows(self):
        return int(self.index.keys.size)

    def contains(self, ids):
        return _member(self.index.keys, ids)

    def add_segment(self, segment):
        """Index the new segment's rows. The new lookup is built aside and swapped in with ONE
        assignment, only when every check passed; a read in flight keeps the snapshot it took."""
        old = self.index
        s = len(old.segments)
        keys = np.concatenate([old.keys, segment.row_ids])
        segs = np.concatenate([old.seg, np.full(segment.row_ids.size, s, np.int64)])
        poss = np.concatenate([old.pos, np.arange(segment.row_ids.size, dtype=np.int64)])
        order = np.argsort(keys, kind="stable")
        keys = keys[order]
        if keys.size > 1 and not (np.diff(keys) > 0).all():
            raise ScanOnceGuardError("table (%s, %s) would hold a row twice" % (self.group, self.kind))
        self.index = _Index(_frozen(keys), _frozen(segs[order]), _frozen(poss[order]),
                            old.segments + (segment,))

    def clear_index(self):
        """Empty the lookup (one assignment) and return the segments it held, for release."""
        old = self.index
        self.index = _empty_index()
        return old.segments


def _locate(table, index, ids):
    """(segment, position) of every requested row in one lookup snapshot; refuses rows not built."""
    found = _member(index.keys, ids)
    if not found.all():
        missing = ids[~found]
        raise TableRefusal(
            "R20", "%d requested row(s) are not built in the %s table of group %s (first: %s)"
            % (missing.size, table.kind, table.group, ", ".join(str(int(v)) for v in missing[:5])),
            fix="build the rows first (build) with the group they belong to")
    pos = np.searchsorted(index.keys, ids)
    return index.seg[pos], index.pos[pos]


def _table_order_ids(index):
    if not index.segments:
        return np.empty(0, dtype=ROW_ID_DTYPE)
    return np.concatenate([seg.row_ids for seg in index.segments])


class TreeAnswerStore(object):
    """The row-keyed tree-answer store of one bank (plan R20, 4.5; see the module docstring).

    Construction takes the bank as plain sequences, so any bank object can feed it:
        trees               fitted sklearn decision trees, in bank order (the column order)
        tree_group          the donor group that owns each tree (same length)
        correctors          per tree a fitted corrector or None, or None when the bank has none
        placebo_correctors  the same for the placebo correctors
        bank_fingerprint    the bank's fingerprint (the store's key; recorded)
        row_group           a callable: row_group(ids) -> the group name of each row id, in the
                            order given (a 1-D array or list of strings, one per id). It must come
                            from the rows' own keys (for grids: the grid's unit -> group key), not
                            from the label a build is called with: every build checks each
                            requested row against it (leave-one-region-out, ruling D).
        temp_dir            an existing folder for the temp memmaps (the machine file's temp dir)
        registry            the shipped-results registry (runs/registry.Registry); the temp dir
                            must pass its G-NOOVERWRITE check
    ``from_bank`` reads the same bank fields from a bank object (trees, tree_group, correctors,
    placebo_correctors, manifest.bank_fingerprint).

    Use it as a context manager, or call close(): every temp file is released loudly.
    """

    def __init__(self, trees, tree_group, correctors, placebo_correctors, bank_fingerprint,
                 row_group, temp_dir, registry, echo=None):
        _require_patched()
        # where the in-run room check's notes go (runs.room.wait_for_room): the run's echo (its run.log and console);
        # None: runs.room.stamped_print. It changes no byte of any table.
        self._echo = echo
        _self_check_scan_once()
        self._lock = threading.RLock()
        self._read_gate = threading.Condition(threading.Lock())
        self._active_reads = 0
        self._draining = False
        self._closed = True  # until construction finishes: close() then has nothing to release
        self._serial = next(_STORE_SERIAL)
        # the writer settings are read once and fixed for the store's life; record() shows them
        self._writer = _writer_mode()
        self._writer_from_test = _TEST_ONLY_WRITER is not None
        self._row_block = int(ROW_BLOCK_ROWS)
        if not callable(row_group):
            raise TableRefusal("D", "row_group must be a callable returning each row's group",
                               fix="pass the rows' own unit -> group lookup (for grids, the grid's "
                                   "group key), so every build can check the rows' real group")
        self._row_group = row_group
        self._trees = self._check_models(trees, "trees", allow_none=False)
        n = len(self._trees)
        groups = list(tree_group)
        if len(groups) != n:
            raise TableRefusal("R20", "tree_group has %d entries for %d trees" % (len(groups), n))
        for g in groups:
            _group_name(g)
        self._tree_group = np.array(groups, dtype=object)
        self._correctors = self._check_extra(correctors, "correctors", n)
        self._placebo = self._check_extra(placebo_correctors, "placebo_correctors", n)
        if not isinstance(bank_fingerprint, str) or not bank_fingerprint:
            raise TableRefusal("R20", "bank_fingerprint must be a non-empty string")
        self.bank_fingerprint = bank_fingerprint
        n_features = {int(m.n_features_in_) for m in self._all_models()}
        if len(n_features) != 1:
            raise TableRefusal("R20", "the bank's trees and correctors expect different feature "
                                      "counts: %s" % sorted(n_features))
        self.n_features = n_features.pop()
        probe = np.zeros((1, self.n_features), dtype=np.float32)
        self._allow_nan = {id(m): bool(m._support_missing_values(probe)) for m in self._all_models()}
        self._temp_dir = self._check_temp_dir(temp_dir, registry)
        self._tables: Dict[Tuple[str, str], _Table] = {}
        self._group_codes: Dict[str, int] = {}
        # group -> its built row ids (sorted, read-only). Copy on write: a build swaps in a whole
        # new dict, so a read iterating it never sees it change.
        self._group_rows: Dict[str, np.ndarray] = {}
        self._history: List[Dict[str, Any]] = []
        self._dropped: List[Dict[str, Any]] = []      # what drop() released (plan 4.5's disk schedule)
        self._closed = False

    @classmethod
    def from_bank(cls, bank, row_group, temp_dir, registry, echo=None):
        """A store for a bank object with the fields of the approved Bank shape. echo: the run's echo for the room
        check's notes (None: runs.room.stamped_print)."""
        try:
            fields = (bank.trees, bank.tree_group, bank.correctors, bank.placebo_correctors,
                      bank.manifest.bank_fingerprint)
        except AttributeError as exc:
            raise TableRefusal("R20", "the bank object lacks a field the store reads: %s" % exc) from exc
        return cls(fields[0], fields[1], fields[2], fields[3], fields[4], row_group, temp_dir,
                   registry, echo=echo)

    # ---------------------------------------------------------------- construction checks
    @staticmethod
    def _check_models(models, what, allow_none):
        from sklearn.tree import BaseDecisionTree

        out = list(models)
        if not out:
            raise TableRefusal("R20", "%s is empty" % what)
        for i, m in enumerate(out):
            if m is None and allow_none:
                continue
            if not isinstance(m, BaseDecisionTree):
                raise TableRefusal(
                    "R20", "%s[%d] is a %s, not a fitted sklearn decision tree; the once-per-block "
                    "scan is proven for sklearn trees only" % (what, i, type(m).__name__))
            if not hasattr(m, "tree_") or not hasattr(m, "n_features_in_"):
                raise TableRefusal("R20", "%s[%d] is not fitted" % (what, i))
            if int(getattr(m, "n_outputs_", 1)) != 1:
                raise TableRefusal("R20", "%s[%d] has %d outputs; a tree answer is one number"
                                   % (what, i, int(m.n_outputs_)))
        return out

    def _check_extra(self, models, what, n):
        if models is None:
            return None
        out = self._check_models(models, what, allow_none=True)
        if len(out) != n:
            raise TableRefusal("R20", "%s has %d entries for %d trees" % (what, len(out), n))
        return out

    def _all_models(self):
        models = list(self._trees)
        for extra in (self._correctors, self._placebo):
            if extra is not None:
                models.extend(m for m in extra if m is not None)
        return models

    @staticmethod
    def _check_temp_dir(temp_dir, registry):
        if registry is None or not hasattr(registry, "assert_writable"):
            raise TableRefusal("G-NOOVERWRITE", "a shipped-results registry is required to check the "
                                                "temp dir", fix="pass runs.registry.Registry")
        resolved = Path(registry.assert_writable(temp_dir))
        if not resolved.is_dir():
            raise TableRefusal("G-DISK", "temp dir %s does not exist" % resolved,
                               fix="create it first; the store never creates folders")
        preflight.refuse_orphans(resolved)
        return resolved

    # ---------------------------------------------------------------- properties and lookups
    @property
    def n_trees(self):
        return len(self._trees)

    @property
    def temp_dir(self):
        return self._temp_dir

    def _check_open(self):
        if self._closed:
            raise TableRefusal("R20", "the tree-answer store is closed")

    def own_columns(self, group):
        """Bank positions of the trees the group owns (the columns its rows never see)."""
        group = _group_name(group)
        return np.flatnonzero(self._tree_group == group).astype(np.int64)

    def tree_columns(self, group):
        """Bank positions of the columns a row of ``group`` gets: every tree except the group's own."""
        group = _group_name(group)
        return np.flatnonzero(self._tree_group != group).astype(np.int64)

    def built_row_ids(self, group, kind):
        """Row ids of the (group, kind) table in table order (empty if nothing is built)."""
        self._check_open()
        table = self._tables.get((_group_name(group), _kind_value(kind)))
        if table is None:
            return np.empty(0, dtype=ROW_ID_DTYPE)
        return _table_order_ids(table.index)

    def group_of(self, row_ids):
        """The one group that holds all these rows; refuses rows of several groups or of none."""
        self._check_open()
        ids = _as_row_ids(row_ids, "row_ids", unique=False)
        group_rows = self._group_rows  # one snapshot; a build swaps the whole dict
        holders = []
        covered = np.zeros(ids.shape, dtype=bool)
        for group in sorted(group_rows):
            hit = _member(group_rows[group], ids)
            if hit.any():
                holders.append(group)
                covered |= hit
        if not covered.all():
            missing = ids[~covered]
            raise TableRefusal("R20", "%d requested row(s) belong to no built group (first: %s)"
                               % (missing.size, ", ".join(str(int(v)) for v in missing[:5])),
                               fix="build the rows first, with the group they belong to")
        if len(holders) != 1:
            raise TableRefusal(
                "D", "the requested rows belong to %d groups (%s); a view holds one group's rows, "
                "because each group drops its own trees" % (len(holders), ", ".join(holders)),
                fix="ask per unit (or per group)")
        return holders[0]

    # ---------------------------------------------------------------- build
    def _table(self, group, kind):
        key = (group, kind)
        table = self._tables.get(key)
        if table is not None:
            return table
        if kind == CORRECTOR and self._correctors is None:
            raise TableRefusal("R20", "the bank has no correctors, so there is no corrector table")
        if kind == PLACEBO_CORRECTOR and self._placebo is None:
            raise TableRefusal("R20", "the bank has no placebo correctors, so there is no placebo table")
        tree_index = self.tree_columns(group)
        own_index = self.own_columns(group)
        if tree_index.size == 0:
            raise TableRefusal("D", "group %s owns every tree of the bank, so its rows have no "
                                    "column once its own trees are dropped" % group)
        if group not in self._group_codes:
            self._group_codes[group] = len(self._group_codes)
        pairs = self._pairs(kind, tree_index)
        allow_nan = all(self._allow_nan[id(t)] and (e is None or self._allow_nan[id(e)])
                        for t, e in pairs)
        table = _Table(group, kind, self._group_codes[group], tree_index, own_index, allow_nan)
        self._tables[key] = table
        return table

    def _pairs(self, kind, tree_index):
        trees = self._trees
        if kind == PLAIN:
            return [(trees[j], None) for j in tree_index]
        extra = self._correctors if kind == CORRECTOR else self._placebo
        return [(trees[j], extra[j]) for j in tree_index]

    def _check_row_groups(self, group, ids):
        """Every requested row must belong to ``group`` by the row-group source (ruling D). Checked
        block by block over the WHOLE request before anything is computed or written."""
        step = self._row_block
        for a0 in range(0, ids.size, step):
            block = ids[a0:a0 + step]
            labels = np.asarray(self._row_group(block.copy()))
            if labels.ndim != 1 or labels.shape[0] != block.size:
                raise TableRefusal("D", "the row-group source returned shape %s for %d rows"
                                   % (labels.shape, block.size),
                                   fix="return one group name per row id, in the order given")
            if labels.dtype.kind not in "UO":
                raise TableRefusal("D", "the row-group source returned dtype %s; it must return "
                                        "group names (strings)" % labels.dtype)
            same = np.asarray(labels == group)
            if same.shape != block.shape or same.dtype != np.bool_:
                raise TableRefusal("D", "the row-group source's answers cannot be compared with the "
                                        "group name %r" % group)
            if not same.all():
                wrong = ~same
                others = sorted({repr(v) for v in labels[wrong][:1000].tolist()})
                raise TableRefusal(
                    "D", "%d row(s) asked for group %s belong to another group by the row-group "
                    "source (%s; first rows: %s); building them here would let their own group's "
                    "trees answer them"
                    % (int(wrong.sum()), group, ", ".join(others[:5]),
                       ", ".join(str(int(v)) for v in block[wrong][:5])),
                    fix="build each row with the group of its unit")

    def _check_row_owner(self, group, ids):
        for other in sorted(self._group_rows):
            if other == group:
                continue
            clash = _member(self._group_rows[other], ids)
            if clash.any():
                raise TableRefusal(
                    "D", "%d row(s) asked for group %s are already built for group %s (first: %s); a "
                    "row belongs to one group, and its own group's trees must never answer it"
                    % (int(clash.sum()), group, other,
                       ", ".join(str(int(v)) for v in ids[clash][:5])),
                    fix="build each row with the group of its unit")

    def build(self, group, kind, row_ids, features):
        """Answer every tree except ``group``'s own on the rows ``row_ids``; rows already built are
        not recomputed. Returns the number of rows computed now.

        group     the group the rows belong to (their unit's group); every row is checked against
                  the store's row-group source first, and the build is refused if one differs
        kind      'plain', 'corrector' or 'placebo_corrector' (a Tool enum value is accepted)
        row_ids   unique non-negative integer row ids, in the order the table should keep them
                  (unit by unit in step order, as the router reads them)
        features  a callable: features(ids) -> float32 array (len(ids), n_features), the kept tree
                  features of those rows in that order, 0-filled (R30). It is called once per row
                  block, only for rows not built yet.
        """
        with self._lock:
            self._check_open()
            group = _group_name(group)
            kind = _kind_value(kind)
            ids = _as_row_ids(row_ids, "row_ids", unique=True)
            if not callable(features):
                raise TableRefusal("R20", "features must be a callable returning the rows' features")
            self._check_row_groups(group, ids)
            self._check_row_owner(group, ids)
            table = self._table(group, kind)
            new = ids[~table.contains(ids)]
            if new.size == 0:
                return 0
            self._build_segment(table, new, features)
            prev = self._group_rows.get(group)
            merged = np.sort(new) if prev is None else np.union1d(prev, new)
            group_rows = dict(self._group_rows)
            group_rows[group] = _frozen(merged)
            self._group_rows = group_rows  # one swap: a read sees the old dict or the new one
            return int(new.size)

    def _feature_block(self, features, block_ids):
        V = features(block_ids.copy())
        if not isinstance(V, np.ndarray):
            raise TableRefusal("R20", "the feature source returned a %s, not a numpy array"
                               % type(V).__name__)
        if V.dtype != np.float32:
            raise TableRefusal("R20", "the feature source returned dtype %s; tree features are "
                                      "float32 (C13), and a cast inside predict() would bypass "
                                      "the once-per-block scan" % V.dtype,
                               fix="cast to float32 in the feature source, before the store")
        if V.ndim != 2 or V.shape != (block_ids.size, self.n_features):
            raise TableRefusal("R20", "the feature source returned shape %s for %d rows of %d "
                                      "features" % (V.shape, block_ids.size, self.n_features))
        # a private C-ordered copy: the source cannot change it under the workers, no alias of the
        # source's own buffers is held, and the values are the same bytes
        return np.array(V, dtype=np.float32, order="C", copy=True)

    def _build_segment(self, table, ids, features):
        workers, scan_once = self._writer
        n = int(ids.size)
        ncols = table.n_columns
        block = min(self._row_block, n)
        item = ANSWER_DTYPE.itemsize
        need_disk = n * ncols * item
        need_ram = block * ncols * item + 2 * block * self.n_features * 4
        # owner ruling Q1: an in-run check waits for room (runs.room.wait_for_room) and refuses as before only after
        # P7.room_max_wait_seconds; the first check is the same call as before; its notes go to the run's echo
        wait_for_room(lambda: preflight.check_resources(self._temp_dir, need_disk, need_ram),
                      "a tree-answer table of %d rows x %d trees" % (n, ncols), self._echo)
        pairs = self._pairs(table.kind, table.tree_index)
        estimator_name = type(pairs[0][0]).__name__
        chunks = _column_chunks(ncols, workers)
        tag = "ans%d_%s_g%d_s%d" % (self._serial, _KIND_TAG[table.kind], table.code,
                                    len(table.index.segments))
        buf = np.empty((block, ncols), dtype=ANSWER_DTYPE)
        executor = (ThreadPoolExecutor(max_workers=len(chunks), thread_name_prefix="treeroute-answers")
                    if len(chunks) > 1 else None)
        sec = {"features": 0.0, "predict": 0.0, "write": 0.0}
        n_blocks = 0
        try:
            with ExitStack() as stack:
                tm = stack.enter_context(temp_memmap(self._temp_dir, tag, (n, ncols), ANSWER_DTYPE))
                for a0 in range(0, n, block):
                    b0 = min(a0 + block, n)
                    m = b0 - a0
                    t0 = time.perf_counter()
                    V = self._feature_block(features, ids[a0:b0])
                    t1 = time.perf_counter()
                    if pairs[0][0]._support_missing_values(V) != self._allow_nan[id(pairs[0][0])]:
                        raise ScanOnceGuardError(
                            "a tree's missing-value support depends on the row block now; the "
                            "allow_nan of the once-per-block scan can no longer be fixed per bank")
                    _answer_block(pairs, V, buf, table.allow_nan, estimator_name, chunks, scan_once,
                                  executor)
                    if a0 == 0:
                        _spot_check(pairs, V, buf, m)
                    t2 = time.perf_counter()
                    _write_slab(tm, a0, buf[:m])
                    t3 = time.perf_counter()
                    del V
                    sec["features"] += t1 - t0
                    sec["predict"] += t2 - t1
                    sec["write"] += t3 - t2
                    n_blocks += 1
                owner = stack.pop_all()
        finally:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)
            del buf
        try:
            table.add_segment(_Segment(ids.copy(), tm, owner))
        except BaseException:
            owner.close()  # the segment is not kept: release its file now, loudly
            raise
        entry = {"group": table.group, "kind": table.kind, "rows": n, "columns": ncols,
                 "blocks": n_blocks, "row_block_rows": block, "workers": len(chunks),
                 "scan_once": scan_once, "row_key_hash": row_key_hash(ids),
                 "seconds": {k: round(v, 6) for k, v in sec.items()}}
        table.builds.append(entry)
        self._history.append(entry)

    # ---------------------------------------------------------------- read
    @contextmanager
    def _reading(self):
        """Count a read in flight; while a drop or close is releasing files, new reads wait."""
        with self._read_gate:
            while self._draining:
                self._read_gate.wait()
            self._active_reads += 1
        try:
            yield
        finally:
            with self._read_gate:
                self._active_reads -= 1
                if self._active_reads == 0:
                    self._read_gate.notify_all()

    def _release_when_no_reads(self, release):
        """Hold new reads back, wait for the reads in flight, run ``release``, let reads go on.
        Called with self._lock held (reads never take it, so the order cannot deadlock)."""
        with self._read_gate:
            self._draining = True
            try:
                while self._active_reads:
                    self._read_gate.wait()
                release()
            finally:
                self._draining = False
                self._read_gate.notify_all()

    def _read(self, table, index, ids):
        seg_idx, pos = _locate(table, index, ids)
        out = np.empty((ids.size, table.n_columns), dtype=ANSWER_DTYPE)
        for s, seg in enumerate(index.segments):
            if seg.tm.shape[1] != table.n_columns:
                raise ScanOnceGuardError("a segment of table (%s, %s) has %d columns, the table %d"
                                         % (table.group, table.kind, seg.tm.shape[1],
                                            table.n_columns))
            sel = np.flatnonzero(seg_idx == s)
            if sel.size == 0:
                continue
            rows = pos[sel]
            order = np.argsort(rows, kind="stable")
            out[sel[order]] = _read_rows(seg.tm, rows[order])
        return out

    def unit_view(self, row_keys, table_kind):
        """Answers for one group's rows (a unit's rows), with the bank position of every column.

        The rows' group is found from the built tables; rows of several groups are refused. The
        columns are every tree except the group's own, which are asserted absent. Safe beside a
        running build: the read uses one snapshot of the table's row lookup.
        """
        kind = _kind_value(table_kind)
        ids = _as_row_ids(row_keys, "row_keys", unique=False)
        with self._reading():
            self._check_open()
            group = self.group_of(ids)
            table = self._tables.get((group, kind))
            index = None if table is None else table.index  # the one snapshot this read uses
            if table is None or index.keys.size == 0:
                raise TableRefusal("R20", "group %s has no %s table built" % (group, kind),
                                   fix="build it first (build), or rebuild it after a drop")
            self._assert_own_columns_absent(table)
            values = self._read(table, index, ids)
            if values.shape[1] != table.tree_index.size:
                raise ScanOnceGuardError("a read of table (%s, %s) returned %d columns, not %d"
                                         % (group, kind, values.shape[1], table.tree_index.size))
            return AnswerView(values=values, tree_index=table.tree_index.copy(), group=group,
                              kind=kind)

    def answers(self, row_keys, table_kind):
        """The answer of every tree NOT owned by the rows' group, in bank order: float32 (rows,
        columns), rows in the order given (the TreeAnswerStore protocol, narrowed by ruling D).
        Column j is NOT bank tree j and there are fewer columns than trees: unit_view().tree_index
        gives the bank position of each column. The rows must belong to one group."""
        return self.unit_view(row_keys, table_kind).values

    def _assert_own_columns_absent(self, table):
        """Leave-one-region-out guard (owner ruling D): the group's own trees are not columns, and
        every other tree is, once, in bank order."""
        own = self.own_columns(table.group)
        if np.intersect1d(table.tree_index, own).size != 0:
            raise ScanOnceGuardError("table (%s, %s) holds columns of its own group's trees"
                                     % (table.group, table.kind))
        if (table.tree_index.size + own.size != self.n_trees
                or not np.array_equal(table.tree_index, self.tree_columns(table.group))):
            raise ScanOnceGuardError("table (%s, %s) has %d columns; the bank has %d trees of which "
                                     "the group owns %d" % (table.group, table.kind,
                                                            table.tree_index.size, self.n_trees,
                                                            own.size))

    # ---------------------------------------------------------------- release
    def drop(self, group, kind):
        """Release the (group, kind) table's temp files now (the disk schedule of plan 4.5). Its rows
        stay assigned to the group; building them again gives the same bytes. Waits for the reads
        in flight and holds new reads back until the files are released. The table's summary (as
        record() lists a held table) is kept in record()'s 'dropped_tables'."""
        with self._lock:
            self._check_open()
            key = (_group_name(group), _kind_value(kind))
            if key not in self._tables:
                return

            def release():
                table = self._tables.pop(key)
                self._dropped.append(dict(self._table_summary(table), dropped_after_builds=len(self._history)))
                self._release([table])

            self._release_when_no_reads(release)

    def drop_group(self, group):
        """Release every table of one group (plan R20's per-group batching: one group's tables on disk at
        a time). Returns the kinds released, in TABLE_KINDS order."""
        group = _group_name(group)
        kinds = [k for k in TABLE_KINDS if (group, k) in self._tables]
        for k in kinds:
            self.drop(group, k)
        return kinds

    def held_bytes(self):
        """Bytes of the temp files the store holds now (every segment of every held table)."""
        with self._lock:
            return int(sum(int(np.prod(seg.tm.shape)) * ANSWER_DTYPE.itemsize
                           for t in self._tables.values() for seg in t.index.segments))

    @staticmethod
    def _release(tables):
        with ExitStack() as stack:
            for table in tables:
                table.dropped = True
                for seg in table.clear_index():
                    stack.callback(seg.owner.close)
        # ExitStack runs every release even if one fails, then raises (loud, nothing swallowed)

    def close(self):
        """Release every temp file loudly (after the reads in flight). Safe to call twice."""
        with self._lock:
            if self._closed:
                return

            def release():
                self._closed = True
                tables = list(self._tables.values())
                self._tables.clear()
                self._release(tables)

            self._release_when_no_reads(release)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ---------------------------------------------------------------- record
    @staticmethod
    def _table_summary(t):
        index = t.index
        return {"group": t.group, "kind": t.kind, "rows": int(index.keys.size), "columns": t.n_columns,
                "own_trees_dropped": int(t.own_index.size), "segments": len(index.segments),
                "row_key_hash": row_key_hash(_table_order_ids(index))}

    def record(self):
        """What the run manifest records about this store (JSON-ready). 'dropped_tables' (only when a
        table was dropped) lists the dropped tables' summaries in drop order."""
        with self._lock:
            tables = [self._table_summary(self._tables[key]) for key in sorted(self._tables)]
            workers, scan_once = self._writer
            extra = {"dropped_tables": [dict(d) for d in self._dropped]} if self._dropped else {}
            return dict(extra, **{
                "bank_fingerprint": self.bank_fingerprint,
                "trees": self.n_trees,
                "features": self.n_features,
                # the mode every build of this store used (fixed when the store was made)
                "writer": {"tree_predict_workers": workers, "scan_once_per_block": scan_once,
                           "test_only_mode": self._writer_from_test,
                           "row_block_rows": self._row_block,
                           "answer_dtype": str(ANSWER_DTYPE)},
                "backend": backend_versions(),
                "temp_dir": str(self._temp_dir),
                "tables": tables,
                "builds": [dict(b) for b in self._history],
                "closed": self._closed,
            })


class DropAfterRead(object):
    """A TreeAnswerStore seen by a reader that builds one group's rows, reads them once and moves to the next group
    (the GLS weight model's donor-row pass, fit.weights.weight_model_for_cut), under plan R20's per-group batching:
    the table a unit_view read came from is dropped right after the read, so one group's tables are on disk at a
    time. build, own_columns, tree_columns, n_trees and bank_fingerprint are the store's. The answers read are the
    store's own (a copy the caller owns); a row a later pass needs again is built again (the same bytes)."""

    def __init__(self, store):
        if not isinstance(store, TreeAnswerStore):
            raise TableRefusal("R20", "DropAfterRead takes a TreeAnswerStore, got %s" % type(store).__name__)
        self._store = store

    @property
    def n_trees(self):
        return self._store.n_trees

    @property
    def bank_fingerprint(self):
        return self._store.bank_fingerprint

    def own_columns(self, group):
        return self._store.own_columns(group)

    def tree_columns(self, group):
        return self._store.tree_columns(group)

    def build(self, group, kind, row_ids, features):
        return self._store.build(group, kind, row_ids, features)

    def unit_view(self, row_keys, table_kind):
        view = self._store.unit_view(row_keys, table_kind)
        self._store.drop(view.group, view.kind)
        return view


__all__ = [
    "PLAIN", "CORRECTOR", "PLACEBO_CORRECTOR", "TABLE_KINDS", "ANSWER_DTYPE", "ROW_BLOCK_ROWS",
    "AnswerView", "TreeAnswerStore", "TableRefusal", "ScanOnceGuardError", "backend_versions",
    "row_key_hash", "DropAfterRead",
]
