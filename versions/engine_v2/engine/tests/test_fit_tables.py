"""treeroute.fit.tables: the row-keyed tree-answer store (plan R20, 4.5; owner rulings C and D).

Gates (plan 4.5, the speed proof's G2-G4 inside the engine):
  - byte-identical answers for 1 vs 8 workers, and with the finiteness scan once per block vs once
    per tree (the 'off' path exists only here, through tables._TEST_ONLY_WRITER);
  - byte-identical to the serial per-tree predict (the shipped lines, including p + 1.0 x corrector);
  - the own group's columns are really absent (leave-one-region-out), and a row is only built under
    its REAL group (the row-group source; the planted wrong-label batch is refused).
Plus: rows computed once and reused, requested order, private copies, reads beside a running build
(a read between every line of the build, and reader threads) and beside drop/close, the temp-file
lifecycle, fail loud on bad input, refusals, the runtime guards, the record.

Temp matrices go under D:/treeroute/fit_build/tables_tests_<pid>/<test> and the fixture removes
the folder (loudly) after each test. The banks are small synthetic sklearn trees with fixed
random_state values; the bank module is built elsewhere, so the store is fed plain sequences.
"""

import gc
import json
import os
import re
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from conftest import make_registry

FIT_BUILD = Path("D:/treeroute/fit_build")
REGISTRY_DIR = Path("D:/treeroute/registry")

GROUPS = ("grp_a", "grp_b", "grp_c")
UNITS_PER_GROUP = 5
STEPS = 900                 # 4,500 rows per group: a whole-group block has 36,000 values, so
N_FEATURES = 8              # sklearnex scans it with oneDAL; small blocks go to sklearn's own scan
TREES_PER_GROUP = 5
DONOR_STEPS = 600
OFFSET = {"grp_a": 0.0, "grp_b": 1000.0, "grp_c": 2000.0}
ETA = 1.0                   # the shipped corrector weight (pm25_adaptation.py:202)
KINDS = ("plain", "corrector", "placebo_corrector")


# ------------------------------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module", autouse=True)
def sklearnex_patched():
    """The engine writes tree answers only with sklearn patched by sklearnex (owner ruling C)."""
    import sklearnex

    was = sklearnex.sklearn_is_patched()
    if not was:
        sklearnex.patch_sklearn()
    yield
    if not was:
        sklearnex.unpatch_sklearn()


@pytest.fixture
def build_dir(request):
    """A fresh folder under D:/treeroute/fit_build for this test's temp memmaps, removed after."""
    if not REGISTRY_DIR.is_dir():
        pytest.skip("the machine registry %s is missing" % REGISTRY_DIR)
    root = FIT_BUILD / ("tables_tests_%d" % os.getpid())
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", request.node.name)[:80]
    folder = root / name
    folder.mkdir(parents=True, exist_ok=False)
    yield folder
    gc.collect()
    left = sorted(folder.iterdir())
    for path in left:           # only files this test's own stores made; a live map raises here
        os.remove(str(path))
    folder.rmdir()
    if not any(root.iterdir()):
        root.rmdir()            # only this process's own folder; fit_build itself is shared
    assert not left, "temp files were left behind: %s" % [p.name for p in left]


@pytest.fixture(scope="module")
def registry():
    from treeroute.runs.registry import Registry

    if not REGISTRY_DIR.is_dir():
        pytest.skip("the machine registry %s is missing" % REGISTRY_DIR)
    return Registry(REGISTRY_DIR)


def _rows():
    """Row ids, group of each row, features and target for the synthetic panel."""
    n_units = len(GROUPS) * UNITS_PER_GROUP
    n = n_units * STEPS
    i = np.arange(n, dtype=np.float64)[:, None]
    k = np.arange(N_FEATURES, dtype=np.float64)[None, :]
    unit = (np.arange(n) // STEPS)
    step = np.arange(n) % STEPS
    X = (np.sin(0.013 * (i + 1.0) * (k + 1.0)) + 0.5 * np.cos(0.0071 * i * (k + 2.0))
         + 0.1 * unit[:, None]).astype(np.float32)
    group = np.array([GROUPS[u // UNITS_PER_GROUP] for u in unit], dtype=object)
    offset = np.array([OFFSET[g] for g in group])
    y = (3.0 * X[:, 0] + X[:, 1] ** 2 - 2.0 * X[:, 2] * X[:, 3] + offset).astype(np.float64)
    return {"ids": np.arange(n, dtype=np.int64), "unit": unit, "step": step, "group": group,
            "X": X, "y": y}


def _fit_bank(data, groups=GROUPS, trees_per_group=TREES_PER_GROUP, criterion="squared_error"):
    from sklearn.tree import DecisionTreeRegressor

    trees, tree_group, corr, plac = [], [], [], []
    for g in groups:
        rows = np.flatnonzero((data["group"] == g) & (data["step"] < DONOR_STEPS))
        X, y = data["X"][rows], data["y"][rows]
        pos = np.arange(rows.size)
        for j in range(trees_per_group):
            inbag = (pos + j) % 3 != 0
            t = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.5,
                                      criterion=criterion, random_state=100 + j)
            t.fit(X[inbag], y[inbag])
            trees.append(t)
            tree_group.append(g)
            ob = ~inbag
            r = y[ob] - t.predict(X[ob]).astype(np.float64)
            if g == groups[-1] and j == trees_per_group - 1:
                corr.append(None)            # a skipped corrector, as the shipped minimum allows
                plac.append(None)
                continue
            corr.append(DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=0.5,
                                              random_state=200 + j).fit(X[ob], r))
            plac.append(DecisionTreeRegressor(max_depth=6, min_samples_leaf=10, max_features=0.5,
                                              random_state=200 + j).fit(X[ob], np.roll(r, r.size // 2)))
    return SimpleNamespace(trees=trees, tree_group=tree_group, correctors=corr,
                           placebo_correctors=plac,
                           manifest=SimpleNamespace(bank_fingerprint="synthetic-bank-1"))


@pytest.fixture(scope="module")
def data():
    return _rows()


@pytest.fixture(scope="module")
def bank(data):
    return _fit_bank(data)


def true_group(ids):
    """The row-group source: each row's group from the panel's own key (row id -> unit -> group),
    never from the label a build is called with."""
    ids = np.asarray(ids)
    return np.asarray(GROUPS, dtype=object)[ids // STEPS // UNITS_PER_GROUP]


def _store(bank, build_dir, registry, row_group=true_group):
    from treeroute.fit.tables import TreeAnswerStore

    return TreeAnswerStore(bank.trees, bank.tree_group, bank.correctors, bank.placebo_correctors,
                           bank.manifest.bank_fingerprint, row_group, build_dir, registry)


class Features(object):
    """The feature source: X[ids] as float32, with a log of every row it was asked for."""

    def __init__(self, X):
        self.X = X
        self.calls = []

    def __call__(self, ids):
        self.calls.append(np.array(ids, copy=True))
        return self.X[ids]

    @property
    def rows_asked(self):
        return int(sum(c.size for c in self.calls))


def _serial(bank, kind, X, cols):
    """The shipped serial loop: one tree after another, full input checks, p + ETA x corrector."""
    out = np.empty((X.shape[0], len(cols)), dtype=np.float32)
    extra = {"plain": None, "corrector": bank.correctors,
             "placebo_corrector": bank.placebo_correctors}[kind]
    for c, j in enumerate(cols):
        p = bank.trees[j].predict(X).astype(np.float32)
        if extra is not None and extra[j] is not None:
            p = p + ETA * extra[j].predict(X).astype(np.float32)
        out[:, c] = p
    return out


def _foreign(bank, group):
    return [j for j, g in enumerate(bank.tree_group) if g != group]


def _group_ids(data, group):
    return data["ids"][data["group"] == group]


def _unit_ids(data, unit):
    return data["ids"][data["unit"] == unit]


def _same_bytes(a, b):
    return a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a.view(np.uint32),
                                                                       b.view(np.uint32))


def _build_all(store, data, kinds=KINDS):
    feats = Features(data["X"])
    for g in GROUPS:
        for kind in kinds:
            store.build(g, kind, _group_ids(data, g), feats)
    return feats


# ------------------------------------------------------------------------------------------ gates
@pytest.mark.parametrize("kind", KINDS)
def test_answers_are_byte_identical_to_the_serial_per_tree_predict(kind, bank, data, build_dir,
                                                                   registry):
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        for g in GROUPS:
            ids = _group_ids(data, g)
            assert store.build(g, kind, ids, feats) == ids.size
            got = store.answers(ids, kind)
            ref = _serial(bank, kind, data["X"][ids], _foreign(bank, g))
            assert _same_bytes(got, ref), (g, kind)
            for u in np.unique(data["unit"][data["group"] == g]):
                uid = _unit_ids(data, u)
                assert _same_bytes(store.answers(uid, kind),
                                   _serial(bank, kind, data["X"][uid], _foreign(bank, g)))


@pytest.mark.parametrize("block", [211, 4500, 12288])
def test_one_vs_eight_workers_and_scan_once_off_vs_on_are_byte_identical(block, bank, data,
                                                                        build_dir, registry,
                                                                        monkeypatch):
    from treeroute.fit import tables

    monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", block)
    results = {}
    for mode in [(1, False), (1, True), (8, False), (8, True), (3, True)]:
        monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", mode)
        with _store(bank, build_dir, registry) as store:
            _build_all(store, data)
            results[mode] = {(g, k): store.answers(_group_ids(data, g), k)
                             for g in GROUPS for k in KINDS}
            builds = store.record()["builds"]
            assert {(b["workers"], b["scan_once"]) for b in builds} == {
                (min(mode[0], 10), mode[1])}          # 10 foreign columns per group here
            assert {b["row_block_rows"] for b in builds} == {min(block, 4500)}
        assert list(build_dir.iterdir()) == []
    ref = results[(1, False)]
    for mode, got in results.items():
        for key in ref:
            assert _same_bytes(got[key], ref[key]), (mode, key)
    for (g, kind), values in ref.items():
        assert _same_bytes(values, _serial(bank, kind, data["X"][_group_ids(data, g)],
                                           _foreign(bank, g)))


def test_the_engine_default_is_eight_workers_with_the_scan_once(bank, data, build_dir, registry):
    from treeroute import engine_constants as K
    from treeroute.fit import tables

    assert tables._TEST_ONLY_WRITER is None and K.TREE_PREDICT_WORKERS == 8
    assert tables._writer_mode() == (8, True)
    with _store(bank, build_dir, registry) as store:
        store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        build = store.record()["builds"][0]
        assert build["workers"] == 8 and build["scan_once"] is True
        assert store.record()["writer"] == {"tree_predict_workers": 8, "scan_once_per_block": True,
                                            "test_only_mode": False, "row_block_rows": 12288,
                                            "answer_dtype": "float32"}


@pytest.mark.parametrize("kind", KINDS)
def test_own_group_columns_are_really_absent(kind, bank, data, build_dir, registry):
    with _store(bank, build_dir, registry) as store:
        _build_all(store, data, kinds=(kind,))
        for g in GROUPS:
            own = [j for j, tg in enumerate(bank.tree_group) if tg == g]
            for u in np.unique(data["unit"][data["group"] == g]):
                view = store.unit_view(_unit_ids(data, u), kind)
                assert view.group == g and view.kind == kind
                assert set(view.tree_index.tolist()).isdisjoint(own)
                assert view.tree_index.tolist() == _foreign(bank, g)
                assert view.values.shape == (STEPS, len(bank.trees) - len(own))
                assert np.array_equal(store.tree_columns(g), view.tree_index)
                assert np.array_equal(store.own_columns(g), own)
                # the own group's trees answer near its offset; no column may sit there
                centres = np.median(view.values, axis=0)
                assert np.all(np.abs(centres - OFFSET[g]) > 500.0), (g, centres)
                # and every column is the foreign tree the index names
                for c, j in enumerate(view.tree_index):
                    assert abs(centres[c] - OFFSET[bank.tree_group[j]]) < 500.0


def test_the_absent_columns_guard_fires_on_a_corrupted_table(bank, data, build_dir, registry):
    from treeroute.fit.tables import ScanOnceGuardError

    with _store(bank, build_dir, registry) as store:
        ids = _group_ids(data, "grp_b")
        store.build("grp_b", "plain", ids, Features(data["X"]))
        table = store._tables[("grp_b", "plain")]
        good = table.tree_index
        table.tree_index = np.arange(len(bank.trees), dtype=np.int64)   # own columns claimed back
        with pytest.raises(ScanOnceGuardError):
            store.answers(ids, "plain")
        table.tree_index = good[1:]                                    # a column lost
        with pytest.raises(ScanOnceGuardError):
            store.answers(ids, "plain")
        table.tree_index = good
        assert store.answers(ids, "plain").shape == (ids.size, 10)


def test_rows_are_computed_once_and_reused_across_passes(bank, data, build_dir, registry):
    g = "grp_a"
    ids = _group_ids(data, g)
    step = data["step"][data["group"] == g]
    hist, test = ids[step < 700], ids[step >= 700]
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        assert store.build(g, "corrector", hist, feats) == hist.size        # the decision pass
        assert feats.rows_asked == hist.size
        n_calls = len(feats.calls)
        assert store.build(g, "corrector", hist, feats) == 0                # asked again: nothing
        assert len(feats.calls) == n_calls
        assert store.build(g, "corrector", ids, feats) == test.size         # the test pass
        assert feats.rows_asked == ids.size                                 # each row once
        assert np.array_equal(np.sort(np.concatenate(feats.calls)), np.sort(ids))
        first = store.answers(hist, "corrector")
        again = store.answers(hist, "corrector")
        assert len(feats.calls) == n_calls + 1                              # reads compute nothing
        assert _same_bytes(first, again)
        assert np.array_equal(store.built_row_ids(g, "corrector"), np.concatenate([hist, test]))
        two_pass = store.answers(ids, "corrector")
        with _store(bank, build_dir, registry) as one_shot:
            one_shot.build(g, "corrector", ids, Features(data["X"]))
            assert _same_bytes(one_shot.answers(ids, "corrector"), two_pass)
        assert store.record()["tables"][0]["segments"] == 2


def test_rows_come_back_in_the_order_asked_across_segments(bank, data, build_dir, registry):
    g = "grp_c"
    ids = _group_ids(data, g)
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        store.build(g, "plain", ids[1::2], feats)
        store.build(g, "plain", ids[::2][::-1], feats)       # a second segment, reversed order
        order = np.argsort(np.sin(ids * 0.77))               # a fixed shuffle
        mixed = ids[order]
        mixed = np.concatenate([mixed, mixed[:7]])           # repeats are served as asked
        got = store.answers(mixed, "plain")
        assert _same_bytes(got, _serial(bank, "plain", data["X"][mixed], _foreign(bank, g)))


def test_reads_are_private_copies(bank, data, build_dir, registry):
    ids = _group_ids(data, "grp_a")[:50]
    with _store(bank, build_dir, registry) as store:
        store.build("grp_a", "plain", ids, Features(data["X"]))
        out = store.answers(ids, "plain")
        assert type(out) is np.ndarray and out.flags.writeable and out.flags.c_contiguous
        before = out.copy()
        out[:] = -1.0
        assert _same_bytes(store.answers(ids, "plain"), before)


# ------------------------------------------------------------------------------------------ lifecycle
def test_temp_files_are_preflight_named_live_and_deleted_by_drop_and_close(bank, data, build_dir,
                                                                           registry):
    from treeroute.fit.tables import TableRefusal
    from treeroute.runs.preflight import TEMP_NAME, find_orphan_temp_files

    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        store.build("grp_a", "plain", _group_ids(data, "grp_a")[:100], feats)
        store.build("grp_a", "plain", _group_ids(data, "grp_a")[100:300], feats)
        store.build("grp_b", "corrector", _group_ids(data, "grp_b"), feats)
        files = sorted(p.name for p in build_dir.iterdir())
        assert len(files) == 3 and all(TEMP_NAME.match(f) for f in files), files
        assert find_orphan_temp_files(build_dir) == []                  # alive, not orphans
        sizes = sorted(p.stat().st_size for p in build_dir.iterdir())
        assert sizes == sorted([100 * 10 * 4, 200 * 10 * 4, 4500 * 10 * 4])
        store.drop("grp_a", "plain")
        assert len(list(build_dir.iterdir())) == 1
        with pytest.raises(TableRefusal):
            store.answers(_group_ids(data, "grp_a")[:10], "plain")      # dropped: rebuild first
        store.build("grp_a", "plain", _group_ids(data, "grp_a")[:10], feats)
        assert _same_bytes(store.answers(_group_ids(data, "grp_a")[:10], "plain"),
                           _serial(bank, "plain", data["X"][:10], _foreign(bank, "grp_a")))
    assert list(build_dir.iterdir()) == []
    with pytest.raises(TableRefusal):
        store.answers(_group_ids(data, "grp_b")[:10], "corrector")
    store.close()                                                       # twice is fine


@pytest.mark.parametrize("mode", [(1, False), (8, False), (1, True), (8, True)])
def test_an_inf_stops_the_run_and_nothing_is_kept(mode, bank, data, build_dir, registry,
                                                  monkeypatch):
    from treeroute.fit import tables

    monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", mode)
    monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", 1000)
    ids = _group_ids(data, "grp_b")
    bad = data["X"].copy()
    bad[ids[1500], 3] = np.inf                                           # inside the second block
    with pytest.raises(ValueError):                                      # the serial path agrees
        bank.trees[0].predict(bad[ids[1000:2000]])
    with _store(bank, build_dir, registry) as store:
        with pytest.raises(ValueError, match="infinity"):
            store.build("grp_b", "plain", ids, Features(bad))
        assert list(build_dir.iterdir()) == []
        assert store.built_row_ids("grp_b", "plain").size == 0
        with pytest.raises(tables.TableRefusal):
            store.answers(ids[:5], "plain")
        store.build("grp_b", "plain", ids, Features(data["X"]))          # good rows still build
        assert _same_bytes(store.answers(ids, "plain"),
                           _serial(bank, "plain", data["X"][ids], _foreign(bank, "grp_b")))


@pytest.mark.parametrize("mode", [(1, False), (8, True)])
def test_a_nan_is_treated_exactly_as_predict_treats_it(mode, data, build_dir, registry,
                                                       monkeypatch):
    from treeroute.fit import tables

    monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", mode)
    nan_x = data["X"].copy()
    ids = _group_ids(data, "grp_a")
    nan_x[ids[::97], 2] = np.nan
    allow = _fit_bank(data)                                   # squared error: trees allow NaN
    with _store(allow, build_dir, registry) as store:
        store.build("grp_a", "corrector", ids, Features(nan_x))
        assert _same_bytes(store.answers(ids, "corrector"),
                           _serial(allow, "corrector", nan_x[ids], _foreign(allow, "grp_a")))
    strict = _fit_bank(data, criterion="absolute_error", trees_per_group=2)   # no NaN support
    assert not strict.trees[0]._support_missing_values(nan_x[:4])
    with pytest.raises(ValueError):
        strict.trees[-1].predict(nan_x[ids])
    with _store(strict, build_dir, registry) as store:
        with pytest.raises(ValueError, match="NaN"):
            store.build("grp_a", "plain", ids, Features(nan_x))
    assert list(build_dir.iterdir()) == []


def test_a_worker_error_propagates_and_the_segment_is_released(data, build_dir, registry):
    from sklearn.tree import DecisionTreeRegressor

    class ExplodingTree(DecisionTreeRegressor):
        armed = False

        def predict(self, X, check_input=True):
            if ExplodingTree.armed:
                raise RuntimeError("tree failed on purpose")
            return super().predict(X, check_input)

    bank = _fit_bank(data)
    rows = np.flatnonzero(data["group"] == "grp_c")[:300]
    boom = ExplodingTree(max_depth=3, random_state=0).fit(data["X"][rows], data["y"][rows])
    bank.trees[-1] = boom
    with _store(bank, build_dir, registry) as store:
        ExplodingTree.armed = True
        try:
            with pytest.raises(RuntimeError, match="on purpose"):
                store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        finally:
            ExplodingTree.armed = False
        assert list(build_dir.iterdir()) == []
        assert store.built_row_ids("grp_a", "plain").size == 0


def test_the_runtime_spot_check_catches_a_changed_number(bank, data, build_dir, registry,
                                                         monkeypatch):
    from treeroute.fit import tables

    real = tables._fill_body

    def nudged(pairs, V, buf, m, lo, hi):
        real(pairs, V, buf, m, lo, hi)
        if lo == 0:
            buf[:m, 0] = np.nextafter(buf[:m, 0], np.float32(np.inf))    # one ulp, one column

    monkeypatch.setattr(tables, "_fill_body", nudged)
    with _store(bank, build_dir, registry) as store:
        with pytest.raises(tables.ScanOnceGuardError, match="differs"):
            store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        assert list(build_dir.iterdir()) == []


def test_assume_finite_on_in_the_scanning_thread_is_refused(bank, data, build_dir, registry):
    import sklearn

    from treeroute.fit.tables import ScanOnceGuardError

    with _store(bank, build_dir, registry) as store:
        with sklearn.config_context(assume_finite=True):
            with pytest.raises(ScanOnceGuardError, match="assume_finite"):
                store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        assert list(build_dir.iterdir()) == []


def test_reads_from_several_threads_agree(bank, data, build_dir, registry):
    with _store(bank, build_dir, registry) as store:
        _build_all(store, data, kinds=("plain",))
        units = np.unique(data["unit"])
        out = {}

        def read(u):
            out[u] = store.answers(_unit_ids(data, u), "plain")

        threads = [threading.Thread(target=read, args=(u,)) for u in units]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for u in units:
            g = GROUPS[u // UNITS_PER_GROUP]
            uid = _unit_ids(data, u)
            assert _same_bytes(out[u], _serial(bank, "plain", data["X"][uid], _foreign(bank, g)))


def _hist_and_test(data, group, cut=700):
    ids = _group_ids(data, group)
    step = data["step"][data["group"] == group]
    return ids[step < cut], ids[step >= cut]


def _unit_split(data, unit, cut=700):
    uid = _unit_ids(data, unit)
    step = data["step"][uid]
    return uid[step < cut], uid[step >= cut]


def test_a_read_slotted_between_every_line_of_a_build_is_right(bank, data, build_dir, registry,
                                                                monkeypatch):
    """The race found in review, made deterministic: the history rows are built, then the test rows
    are added unit by unit, and a read of already-built rows runs between EVERY line of build,
    _build_segment, add_segment and the group-row update (a trace function in the build thread;
    Python does not trace code run by the trace function itself)."""
    import sys

    from treeroute.fit import tables

    monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", 150)       # several blocks per build
    g = "grp_b"
    hist, _ = _hist_and_test(data, g)
    units = np.unique(data["unit"][data["group"] == g])
    watched = {tables.TreeAnswerStore.build.__code__, tables.TreeAnswerStore._build_segment.__code__,
               tables._Table.add_segment.__code__}
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        store.build(g, "corrector", hist, feats)
        probes = []                                     # (built rows, their serial answers)
        for u in units[:2]:
            ids = _unit_split(data, u)[0]
            probes.append((ids, _serial(bank, "corrector", data["X"][ids], _foreign(bank, g))))
        outcomes = []

        def read_now():
            for ids, ref in probes:
                outcomes.append(_same_bytes(store.answers(ids, "corrector"), ref))

        def tracer(frame, event, arg):
            if frame.f_code not in watched:
                return None

            def on_line(frame, event, arg):
                if event == "line":
                    read_now()
                return on_line

            return on_line

        for u in units:
            new = _unit_split(data, u)[1]
            sys.settrace(tracer)
            try:
                store.build(g, "corrector", new, feats)
            finally:
                sys.settrace(None)
            probes.append((new, _serial(bank, "corrector", data["X"][new], _foreign(bank, g))))
        assert len(outcomes) > 200 and all(outcomes), outcomes.count(False)
        assert _same_bytes(store.answers(_group_ids(data, g), "corrector"),
                           _serial(bank, "corrector", data["X"][_group_ids(data, g)],
                                   _foreign(bank, g)))


def test_reads_in_other_threads_while_segments_are_added_agree(bank, data, build_dir, registry):
    g = "grp_c"
    hist, test = _hist_and_test(data, g)
    probe = _unit_split(data, np.unique(data["unit"][data["group"] == g])[1])[0]
    other = _group_ids(data, "grp_a")
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        store.build(g, "plain", hist, feats)
        store.build("grp_a", "plain", other, feats)
        refs = {"probe": _serial(bank, "plain", data["X"][probe], _foreign(bank, g)),
                "other": _serial(bank, "plain", data["X"][other], _foreign(bank, "grp_a"))}
        stop = threading.Event()
        counts = {"reads": 0, "wrong": 0}
        errors = []

        def reader():
            try:
                while not stop.is_set():
                    for name, ids in (("probe", probe), ("other", other)):
                        if not _same_bytes(store.answers(ids, "plain"), refs[name]):
                            counts["wrong"] += 1
                        counts["reads"] += 1
            except BaseException as exc:    # reported by the assert below
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        try:
            for chunk in np.array_split(test, 60):          # 60 small segments, one after another
                store.build(g, "plain", chunk, feats)
        finally:
            stop.set()
            for t in threads:
                t.join(60)
        assert not errors, errors
        assert counts["reads"] > 0 and counts["wrong"] == 0, counts
        assert store.record()["tables"][1]["segments"] == 61


@pytest.mark.parametrize("how", ["drop", "close"])
def test_drop_and_close_wait_for_a_read_in_flight(how, bank, data, build_dir, registry,
                                                  monkeypatch):
    from treeroute.fit import tables

    real = tables._read_rows
    inside, go = threading.Event(), threading.Event()

    def held_read(tm, rows):
        inside.set()
        assert go.wait(60)
        return real(tm, rows)

    ids = _group_ids(data, "grp_a")[:300]
    with _store(bank, build_dir, registry) as store:
        store.build("grp_a", "plain", ids, Features(data["X"]))
        monkeypatch.setattr(tables, "_read_rows", held_read)
        out, errors = {}, []

        def reader():
            try:
                out["values"] = store.answers(ids, "plain")
            except BaseException as exc:
                errors.append(exc)

        def releaser():
            try:
                store.drop("grp_a", "plain") if how == "drop" else store.close()
                out["released"] = True
            except BaseException as exc:
                errors.append(exc)

        r = threading.Thread(target=reader)
        r.start()
        assert inside.wait(60)
        d = threading.Thread(target=releaser)
        d.start()
        d.join(0.5)
        assert d.is_alive(), "the release did not wait for the read in flight"
        assert len(list(build_dir.iterdir())) == 1
        go.set()
        r.join(60)
        d.join(60)
        monkeypatch.setattr(tables, "_read_rows", real)
        assert not errors, errors
        assert out.get("released") is True and list(build_dir.iterdir()) == []
        assert _same_bytes(out["values"], _serial(bank, "plain", data["X"][ids],
                                                  _foreign(bank, "grp_a")))
        with pytest.raises(tables.TableRefusal):
            store.answers(ids, "plain")                    # released: a new read is refused


# ------------------------------------------------------------------------------------------ real group
def test_rows_built_under_the_wrong_group_are_refused(bank, data, build_dir, registry,
                                                      monkeypatch):
    """The planted fault found in review: 2,000 rows of one group built under another group's label.
    The row-group source refuses it before anything is computed, so the rows' own trees can never
    become their columns."""
    from treeroute.fit import tables

    monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", 500)       # the check runs block by block
    a, b = _group_ids(data, "grp_a"), _group_ids(data, "grp_b")
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        for label, ids in [("grp_b", a[:2000]),                               # a whole wrong batch
                           ("grp_b", np.concatenate([b[:1700], a[:1]])),      # one row, 4th block
                           ("grp_a", np.concatenate([a[:10], b[5:6], a[10:20]]))]:
            for kind in KINDS:
                with pytest.raises(tables.TableRefusal) as info:
                    store.build(label, kind, ids, feats)
                assert info.value.rule == "D" and "row-group source" in str(info.value)
        assert feats.calls == []                                # nothing was computed
        assert list(build_dir.iterdir()) == []                  # and nothing written
        assert all(store.built_row_ids(g, k).size == 0 for g in GROUPS for k in KINDS)
        with pytest.raises(tables.TableRefusal):
            store.group_of(a[:5])                               # no row was assigned a group
        store.build("grp_a", "plain", a[:2000], feats)          # the right label builds
        view = store.unit_view(a[:2000], "plain")
        assert view.group == "grp_a"
        assert set(view.tree_index.tolist()).isdisjoint(store.own_columns("grp_a").tolist())


def test_a_bad_row_group_source_is_refused(bank, data, build_dir, registry):
    from treeroute.fit.tables import TableRefusal

    a = _group_ids(data, "grp_a")
    bad_sources = [
        lambda ids: true_group(ids)[:-1],                               # one short
        lambda ids: true_group(ids).reshape(-1, 1),                     # 2-D
        lambda ids: np.zeros(ids.size, dtype=np.int64),                 # codes, not names
        lambda ids: np.array([s.encode() for s in true_group(ids)]),    # bytes, not names
        lambda ids: np.array([None] * ids.size, dtype=object),          # no names at all
    ]
    for i, source in enumerate(bad_sources):
        with _store(bank, build_dir, registry, row_group=source) as store:
            feats = Features(data["X"])
            with pytest.raises(TableRefusal) as info:
                store.build("grp_a", "plain", a, feats)
            assert info.value.rule == "D", i
            assert feats.calls == [] and list(build_dir.iterdir()) == [], i

    def failing(ids):
        raise RuntimeError("the grid key is missing on purpose")

    with _store(bank, build_dir, registry, row_group=failing) as store:
        with pytest.raises(RuntimeError, match="on purpose"):
            store.build("grp_a", "plain", a, Features(data["X"]))
        assert list(build_dir.iterdir()) == []
    as_list = lambda ids: true_group(ids).tolist()                        # a plain list is fine
    with _store(bank, build_dir, registry, row_group=as_list) as store:
        assert store.build("grp_a", "plain", a, Features(data["X"])) == a.size


def test_a_row_already_built_under_another_group_is_refused(bank, data, build_dir, registry):
    """The second door of ruling D: even if the row-group source changed its answer between builds,
    a row already built for one group is never built for another."""
    from treeroute.fit.tables import TableRefusal

    a = _group_ids(data, "grp_a")
    source = {"override": None}

    def switchable(ids):
        labels = true_group(ids)
        if source["override"] is not None:
            labels = np.full(ids.size, source["override"], dtype=object)
        return labels

    with _store(bank, build_dir, registry, row_group=switchable) as store:
        store.build("grp_a", "plain", a[:100], Features(data["X"]))
        source["override"] = "grp_b"
        with pytest.raises(TableRefusal) as info:
            store.build("grp_b", "plain", a[50:150], Features(data["X"]))
        assert info.value.rule == "D" and "already built" in str(info.value)


# ------------------------------------------------------------------------------------------ refusals
def test_refusals_of_bad_requests(bank, data, build_dir, registry):
    from treeroute.fit.tables import TableRefusal

    a, b = _group_ids(data, "grp_a"), _group_ids(data, "grp_b")
    with _store(bank, build_dir, registry) as store:
        feats = Features(data["X"])
        cases = [
            lambda: store.build("grp_a", "trees_off", a, feats),
            lambda: store.build("grp_a", "gls", a, feats),
            lambda: store.build("", "plain", a, feats),
            lambda: store.build("grp_a", "plain", np.array([], dtype=np.int64), feats),
            lambda: store.build("grp_a", "plain", np.array([1, 2, 2]), feats),
            lambda: store.build("grp_a", "plain", np.array([-1, 2]), feats),
            lambda: store.build("grp_a", "plain", a.astype(np.float64), feats),
            lambda: store.build("grp_a", "plain", a.reshape(-1, 1), feats),
            lambda: store.build("grp_a", "plain", a, "not callable"),
            lambda: store.build("grp_a", "plain", a, lambda ids: data["X"][ids].astype(np.float64)),
            lambda: store.build("grp_a", "plain", a, lambda ids: data["X"][ids][:, :-1]),
            lambda: store.build("grp_a", "plain", a, lambda ids: data["X"][ids][:-1]),
            lambda: store.build("grp_a", "plain", a, lambda ids: data["X"][ids].tolist()),
        ]
        for i, case in enumerate(cases):
            with pytest.raises(TableRefusal):
                case()
            assert list(build_dir.iterdir()) == [], i
        store.build("grp_a", "plain", a, feats)
        with pytest.raises(TableRefusal) as info:                  # a row of grp_a under grp_b
            store.build("grp_b", "plain", np.concatenate([b[:10], a[:3]]), feats)
        assert info.value.rule == "D"
        store.build("grp_b", "plain", b, feats)
        with pytest.raises(TableRefusal) as info:                  # a view spans two groups
            store.answers(np.concatenate([a[:5], b[:5]]), "plain")
        assert info.value.rule == "D"
        with pytest.raises(TableRefusal):                          # rows nobody built
            store.answers(_group_ids(data, "grp_c")[:5], "plain")
        with pytest.raises(TableRefusal):                          # that kind is not built
            store.answers(a[:5], "corrector")
        store.build("grp_a", "corrector", a[:100], feats)
        with pytest.raises(TableRefusal):                          # only part of the rows built
            store.answers(a[:101], "corrector")


def test_refusals_of_bad_banks_and_places(bank, data, build_dir, registry, tmp_path):
    from sklearn.linear_model import LinearRegression
    from sklearn.tree import DecisionTreeRegressor

    from treeroute.errors import RefusedError
    from treeroute.fit.tables import TableRefusal, TreeAnswerStore

    fp = "fp"
    t, g = bank.trees, bank.tree_group
    narrow = DecisionTreeRegressor(max_depth=2).fit(data["X"][:50, :4], data["y"][:50])
    two_out = DecisionTreeRegressor(max_depth=2).fit(data["X"][:50], np.c_[data["y"][:50],
                                                                           data["y"][:50]])
    lin = LinearRegression().fit(data["X"][:50], data["y"][:50])
    bad = [
        ([], [], None, None, fp),
        (t, g[:-1], None, None, fp),
        (t, g[:-1] + [""], None, None, fp),
        (t[:-1] + [lin], g, None, None, fp),
        (t[:-1] + [DecisionTreeRegressor()], g, None, None, fp),
        (t[:-1] + [narrow], g, None, None, fp),
        (t[:-1] + [two_out], g, None, None, fp),
        (t, g, bank.correctors[:-1], None, fp),
        (t, g, None, None, ""),
    ]
    for i, args in enumerate(bad):
        with pytest.raises(TableRefusal):
            TreeAnswerStore(*args, true_group, build_dir, registry)
    with pytest.raises(TableRefusal):                                   # no registry
        TreeAnswerStore(t, g, None, None, fp, true_group, build_dir, None)
    with pytest.raises(TableRefusal):                                   # folder missing
        TreeAnswerStore(t, g, None, None, fp, true_group, build_dir / "missing", registry)
    with pytest.raises(TableRefusal) as info:                           # no row-group source
        TreeAnswerStore(t, g, None, None, fp, None, build_dir, registry)
    assert info.value.rule == "D"
    fake = make_registry(tmp_path, [build_dir])                          # temp dir is protected
    from treeroute.runs.registry import Registry

    with pytest.raises(RefusedError) as info:
        TreeAnswerStore(t, g, None, None, fp, true_group, build_dir, Registry(fake))
    assert info.value.rule == "G-NOOVERWRITE"
    with TreeAnswerStore(t, g, None, None, fp, true_group, build_dir, registry) as store:
        with pytest.raises(TableRefusal):                               # no correctors in the bank
            store.build("grp_a", "corrector", _group_ids(data, "grp_a"), Features(data["X"]))
    single = _fit_bank(data, groups=("grp_a",), trees_per_group=2)
    with _store(single, build_dir, registry) as store:
        with pytest.raises(TableRefusal) as info:                       # owns every tree
            store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        assert info.value.rule == "D"
        store.build("grp_b", "plain", _group_ids(data, "grp_b"), Features(data["X"]))  # full width
        assert store.unit_view(_group_ids(data, "grp_b"), "plain").tree_index.tolist() == [0, 1]
    assert list(build_dir.iterdir()) == []


def test_an_unpatched_sklearn_is_refused(bank, build_dir, registry, monkeypatch):
    import sklearnex

    from treeroute.fit.tables import TableRefusal

    monkeypatch.setattr(sklearnex, "sklearn_is_patched", lambda *a, **k: False)
    with pytest.raises(TableRefusal) as info:
        _store(bank, build_dir, registry)
    assert info.value.rule == "C14" and "launcher" in str(info.value)


def test_an_orphan_temp_file_is_refused(bank, build_dir, registry):
    from treeroute.errors import PreflightRefusal

    orphan = build_dir / "treeroute_999999_1_ans0_plain_g0_s0.mm"      # pid 999999 is not alive
    orphan.write_bytes(b"")
    try:
        with pytest.raises(PreflightRefusal):
            _store(bank, build_dir, registry)
    finally:
        os.remove(str(orphan))


# ------------------------------------------------------------------------------------------ records
def test_from_bank_and_the_record(bank, data, build_dir, registry):
    from treeroute.fit.tables import TreeAnswerStore, row_key_hash

    with TreeAnswerStore.from_bank(bank, true_group, build_dir, registry) as store:
        ids = _group_ids(data, "grp_c")
        store.build("grp_c", "placebo_corrector", ids, Features(data["X"]))
        rec = json.loads(json.dumps(store.record()))
        assert rec["bank_fingerprint"] == "synthetic-bank-1"
        assert rec["trees"] == 15 and rec["features"] == N_FEATURES
        assert rec["tables"] == [{"group": "grp_c", "kind": "placebo_corrector", "rows": ids.size,
                                  "columns": 10, "own_trees_dropped": 5, "segments": 1,
                                  "row_key_hash": row_key_hash(ids)}]
        backend = rec["backend"]
        assert backend["sklearn_patched"] is True
        assert backend["finite_scan"].startswith("daal4py.")
        assert backend["scikit-learn"] and backend["scikit-learn-intelex"] and backend["numpy"]
        assert set(rec["builds"][0]["seconds"]) == {"features", "predict", "write"}
    from treeroute.fit.tables import TableRefusal

    with pytest.raises(TableRefusal):
        TreeAnswerStore.from_bank(SimpleNamespace(trees=bank.trees), true_group, build_dir, registry)


def test_the_record_writer_block_is_the_mode_the_builds_used(bank, data, build_dir, registry,
                                                            monkeypatch):
    from treeroute.fit import tables

    monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", (1, False))
    monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", 211)
    with _store(bank, build_dir, registry) as store:
        monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", None)      # later changes do not reach it
        monkeypatch.setattr(tables, "ROW_BLOCK_ROWS", 12288)
        store.build("grp_a", "plain", _group_ids(data, "grp_a"), Features(data["X"]))
        rec = store.record()
        assert rec["writer"] == {"tree_predict_workers": 1, "scan_once_per_block": False,
                                 "test_only_mode": True, "row_block_rows": 211,
                                 "answer_dtype": "float32"}
        assert [(b["workers"], b["scan_once"], b["row_block_rows"]) for b in rec["builds"]] == [
            (1, False, 211)]
    monkeypatch.setattr(tables, "_TEST_ONLY_WRITER", (8, True))
    with _store(bank, build_dir, registry) as store:                # the engine mode, but set by a
        assert store.record()["writer"]["test_only_mode"] is True   # test: the record says so


def test_row_key_hash_is_order_sensitive_and_dtype_stable():
    from treeroute.fit.tables import row_key_hash

    assert row_key_hash([1, 2, 3]) == row_key_hash(np.array([1, 2, 3], dtype=np.int32))
    assert row_key_hash([1, 2, 3]) != row_key_hash([3, 2, 1])


def test_the_tool_enum_values_are_the_table_kinds():
    from enum import Enum

    from treeroute.fit.tables import TABLE_KINDS, _kind_value

    class Tool(Enum):            # the approved common.Tool values (treeroute/_proposed/common.py)
        PLAIN = "plain"
        CORRECTOR = "corrector"
        PLACEBO_CORRECTOR = "placebo_corrector"
        TREES_OFF = "trees_off"

    assert [_kind_value(t) for t in (Tool.PLAIN, Tool.CORRECTOR, Tool.PLACEBO_CORRECTOR)] == list(
        TABLE_KINDS)
    from treeroute.fit.tables import TableRefusal

    with pytest.raises(TableRefusal):
        _kind_value(Tool.TREES_OFF)


def test_the_corrector_sum_equals_the_shipped_eta_line():
    x = np.linspace(-700.0, 700.0, 100001).astype(np.float32)
    c = np.cos(np.arange(x.size) * 0.01).astype(np.float32) * 3.0
    assert _same_bytes(x + c, x + ETA * c)


def test_the_store_drops_the_same_columns_as_the_bank_module(bank, build_dir, registry):
    bank_mod = pytest.importorskip("treeroute.fit.bank")
    with _store(bank, build_dir, registry) as store:
        for g in GROUPS + ("grp_none",):
            assert np.array_equal(store.tree_columns(g),
                                  bank_mod.columns_excluding_group(bank.tree_group, g))
            assert np.array_equal(store.own_columns(g),
                                  bank_mod.group_tree_columns(bank.tree_group, g))
