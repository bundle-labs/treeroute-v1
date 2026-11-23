"""Ruling Z2: the Random Forest out of core (models.rf_forest). Synthetic data only; every write under the test's
basetemp. No run, export or label is read.

  OOC1  the out-of-core forest equals an in-RAM forest fitted on the same per-tree samples: the same samples, the
        same trees (node arrays) and byte-equal predictions, whatever the RAM budget (one batch or many), the
        input (a row-major memmap read with file reads, or an in-RAM array) or a subset of rows.
  OOC2  determinism: two runs give the same trees and byte-equal predictions (the public fit_predict path).
  OOC3  the RAM bound: on a memmap LARGER than the budget, the process's private memory during the fit stays
        within the budget (Windows private bytes; a positive control shows an in-RAM load breaks it).
  OOC4  resume: a fit stopped between two trees resumes from its last checkpoint, refits only the missing trees
        and gives byte-equal predictions; another fit's checkpoint is never used.
  OOC5  the stride is gone (models and harness); a budget too small for one tree refuses.
"""

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest

from rivals.tests import toy_runs as T

PARAMS = {"max_features": 0.5, "min_samples_leaf": 5}


def M():
    return T.rivals_models()


def _data(n=3000, p=12, n_score=257, seed=5):
    rng = np.random.default_rng(seed)                       # test data only; never a model seed
    X = rng.standard_normal((n, p)).astype(np.float32)
    X[rng.random((n, p)) < 0.08] = np.nan
    normal = rng.uniform(-1.0, 1.0, n)
    target = np.nan_to_num(X[:, 0].astype(np.float64)) * 2.0 - np.nan_to_num(X[:, 1]) + rng.standard_normal(n)
    Xs = rng.standard_normal((n_score, p)).astype(np.float32)
    Xs[rng.random((n_score, p)) < 0.08] = np.nan
    normal_s = rng.uniform(-1.0, 1.0, n_score)
    return X, normal, target, Xs, normal_s


def _write_memmap(path: Path, X: np.ndarray, block: int = 1000) -> np.memmap:
    """Row-major, written row block by row block (never column-wise), then reopened read-only."""
    mm = np.memmap(str(path), dtype=np.float32, mode="w+", shape=X.shape)
    for a in range(0, X.shape[0], block):
        mm[a:a + block] = X[a:a + block]
    mm.flush()
    del mm
    return np.memmap(str(path), dtype=np.float32, mode="r", shape=X.shape)


def _sig(tree, sample, target, seed):
    """A tree's identity: its sample and target bytes, its random_state and its node arrays."""
    est = tree.estimators_[0].tree_
    h = hashlib.sha256()
    for a in (np.ascontiguousarray(sample), np.ascontiguousarray(target, dtype=np.float64), est.feature,
              est.threshold, est.value, est.children_left, est.children_right, est.n_node_samples):
        h.update(np.ascontiguousarray(a).tobytes())
    h.update(str(int(seed)).encode("ascii"))
    return h.hexdigest()


@pytest.fixture
def record_trees(monkeypatch):
    """Wrap models._rf_tree: every fitted tree's signature, in fit order."""
    mod = M()
    orig = mod._rf_tree
    sigs = []

    def wrapped(sample, target, params, seed):
        tree = orig(sample, target, params, seed)
        sigs.append(_sig(tree, sample, target, seed))
        return tree

    monkeypatch.setattr(mod, "_rf_tree", wrapped)
    return sigs, orig


def _reference(X_ram, rows, normal, target, params, score_mats, n_trees, fit_tree):
    """The IN-RAM forest on the same per-tree samples: the whole [0-filled X | normal] of the fit rows in RAM,
    each tree on X_full[its rows] (the same draws), whole-set predictions summed in tree order."""
    mod = M()
    X_full = mod._tree_matrix(X_ram, rows, normal)
    tgt = target if rows is None else target[rows]
    n_eff = X_full.shape[0]
    m = mod.rf_rows_per_tree(n_eff)
    accs = [np.zeros(Xs.shape[0]) for _, Xs in score_mats]
    sigs = []
    for t, idx, seed in mod._rf_draws(n_eff, m, n_trees):
        sample = X_full[idx]
        tree = fit_tree(sample, tgt[idx], params, seed)
        sigs.append(_sig(tree, sample, tgt[idx], seed))
        for (_, Xs), acc in zip(score_mats, accs):
            acc += np.asarray(tree.predict(Xs), dtype=np.float64)
    return {nm: acc / float(n_trees) for (nm, _), acc in zip(score_mats, accs)}, sigs


def _small_blocks(monkeypatch, rows_per_tree=700):
    mod = M()
    monkeypatch.setattr(mod, "RF_ROWS_PER_TREE", rows_per_tree)
    monkeypatch.setattr(mod, "RF_READ_BLOCK_BYTES", 4800)    # 100 rows of 12 columns per read
    monkeypatch.setattr(mod, "RF_SLACK_BYTES", 0)


def _budget_for(n, p, m, score_rows, trees_per_batch):
    """A budget whose parent part holds about `trees_per_batch` trees' rows."""
    mod = M()
    plan = mod._rf_budget(n, p, m, score_rows, 1e12)
    fixed = sum(v for k, v in plan.items() if k not in ("parent_budget", "row_bytes", "block_rows"))
    return fixed + trees_per_batch * m * (plan["row_bytes"] + 8)


# ------------------------------------------------------------------------------------------ OOC1
@pytest.mark.parametrize("case", ["memmap_many_batches", "array_one_batch", "memmap_row_subset"])
def test_ooc1_out_of_core_equals_the_in_ram_forest_on_the_same_samples(case, tmp_path, monkeypatch, record_trees):
    mod = M()
    _small_blocks(monkeypatch)
    sigs, fit_tree = record_trees
    X, normal, target, Xs, normal_s = _data()
    n, p = X.shape
    score_mats = [("s", mod._tree_matrix(Xs, None, normal_s)), ("fitrows", mod._tree_matrix(X[:300], None,
                                                                                             normal[:300]))]
    rows = np.arange(1, n, 3, dtype=np.int64) if case == "memmap_row_subset" else None
    n_trees = 9
    if case == "array_one_batch":
        Xin, budget = X, 1e12
    else:
        Xin = _write_memmap(tmp_path / ("fit_%s.f32" % case), X)
        n_eff = n if rows is None else rows.size
        budget = _budget_for(n, p, mod.rf_rows_per_tree(n_eff), sum(s.shape[0] for _, s in score_mats), 2)
    f, info = mod.rf_forest(Xin, rows, normal, target, PARAMS, score_mats, n_trees=n_trees, budget=budget)
    ooc_sigs = list(sigs)
    ref, ref_sigs = _reference(X, rows, normal, target, PARAMS, score_mats, n_trees, fit_tree)
    assert len(ooc_sigs) == n_trees and ooc_sigs == ref_sigs              # same samples, same trees
    for nm, _ in score_mats:
        assert f[nm].tobytes() == ref[nm].tobytes(), nm                  # byte-equal predictions
    if rows is None:                                  # the data-free batch plan is the fit's own plan
        plan = mod.rf_batch_plan(n, p, sum(s.shape[0] for _, s in score_mats), n_trees, budget)
        assert plan["trees_per_batch"] == info["trees_per_batch"]
        assert plan["parent_rows_per_batch"] == info["parent_rows_per_batch"]
    if case == "array_one_batch":
        assert info["batches"] == 1
    else:
        assert info["batches"] >= 2, info["trees_per_batch"]
        assert max(info["parent_rows_per_batch"]) < (n if rows is None else rows.size)
    # the trees differ from each other (each its own sample and random_state)
    assert len(set(ooc_sigs)) == n_trees


def test_ooc1_the_file_reader_returns_the_memmap_bytes(tmp_path):
    mod = M()
    X, *_ = _data(n=1000, p=7)
    mm = _write_memmap(tmp_path / "r.f32", X)
    r = mod._RowReader(mm, 64)
    assert r.fh is not None                                   # the file path is used for a memmap on a file
    for a, b in ((0, 64), (5, 69), (936, 1000), (999, 1000)):
        assert r.read(a, b).tobytes() == np.asarray(mm[a:b]).tobytes()
    r.close()
    view = mm[10:500]                                         # a view of a memmap is sliced, never file-read
    rv = mod._RowReader(view, 64)
    assert rv.fh is None and rv.read(3, 50).tobytes() == np.asarray(view[3:50]).tobytes()


# ------------------------------------------------------------------------------------------ OOC2
def test_ooc2_two_runs_give_the_same_trees_and_bytes(tmp_path, monkeypatch, record_trees):
    mod = M()
    _small_blocks(monkeypatch, rows_per_tree=900)
    monkeypatch.setattr(mod, "RF_TREES", 7)
    sigs, _ = record_trees
    X, normal, target, Xs, normal_s = _data(seed=9)
    mm = _write_memmap(tmp_path / "det.f32", X)
    fit = mod.FitData(name="fit", X=mm, columns=tuple("f%d" % i for i in range(X.shape[1])), y=target,
                      normal={"identity": normal})
    score = [mod.ScoreData(name="s", X=Xs, normal={"identity": normal_s})]
    params = dict(PARAMS, link="identity", c=None, ub=None)
    runs = []
    for _ in range(2):
        del sigs[:]
        res = mod.fit_predict("rf", params, fit, score, (mod.RF_TREES,))
        runs.append((np.asarray(res["s"][mod.RF_TREES]["pre"]).tobytes(), list(sigs), res.info["samples_sha256"]))
    assert runs[0] == runs[1]
    assert len(runs[0][1]) == 7


# ------------------------------------------------------------------------------------------ OOC3
_RAM_SCRIPT = textwrap.dedent(r'''
    import json, sys
    import numpy as np, psutil
    sys.path.insert(0, sys.argv[1])
    from rivals import models as M
    path, n, p, budget, mode = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
    M.RF_ROWS_PER_TREE = 20000
    M.RF_READ_BLOCK_BYTES = 4 << 20
    M.RF_SLACK_BYTES = 16 << 20
    params = {"max_features": 0.2, "min_samples_leaf": 50}
    X = np.memmap(path, dtype=np.float32, mode="r", shape=(n, p))
    normal = np.zeros(n)
    target = np.sin(np.arange(n, dtype=np.float64))
    M._rf_tree(np.zeros((64, p + 1), np.float32), np.arange(64.0), params, 0)      # load the oneDAL libraries
    proc = psutil.Process()
    c0 = proc.memory_info().private
    if mode == "ooc":
        f, info = M.rf_forest(X, None, normal, target, params, [], n_trees=6, budget=budget)
    else:                                                                           # positive control
        info = {"sum": float(np.asarray(X, dtype=np.float32).copy().sum(dtype=np.float64))}
    print(json.dumps({"c0": c0, "peak": proc.memory_info().peak_pagefile, "info": info}))
''')


@pytest.mark.skipif(sys.platform != "win32", reason="private-bytes peak (psutil peak_pagefile) is Windows-only")
def test_ooc3_ram_stays_within_the_budget_on_a_memmap_larger_than_it(tmp_path):
    n, p = 300_000, 250
    budget = 160 << 20
    path = tmp_path / "big.f32"
    mm = np.memmap(str(path), dtype=np.float32, mode="w+", shape=(n, p))
    rng = np.random.default_rng(3)                                                  # test data only
    for a in range(0, n, 20_000):                                                   # row-major row blocks
        blk = rng.standard_normal((min(n, a + 20_000) - a, p)).astype(np.float32)
        blk[blk > 2.5] = np.nan
        mm[a:a + blk.shape[0]] = blk
    mm.flush()
    del mm
    assert os.path.getsize(path) > budget * 1.5                                    # the file is larger than the budget
    script = tmp_path / "ram_probe.py"
    script.write_text(_RAM_SCRIPT, encoding="utf-8")

    def run(mode):
        out = subprocess.run([sys.executable, "-B", str(script), str(T.BUILD_ROOT), str(path), str(n), str(p),
                              str(budget), mode], capture_output=True, text=True, timeout=900)
        assert out.returncode == 0, out.stderr[-3000:]
        return json.loads(out.stdout.strip().splitlines()[-1])

    rec = run("ooc")
    used = rec["peak"] - rec["c0"]
    print("OOC3: file %.0f MiB, budget %.0f MiB, private growth %.1f MiB, batches %s"
          % (os.path.getsize(path) / 2 ** 20, budget / 2 ** 20, used / 2 ** 20, rec["info"]["trees_per_batch"]))
    assert rec["info"]["batches"] >= 2, rec["info"]
    assert rec["info"]["read_gib"] * (1 << 30) >= os.path.getsize(path) * 0.5     # it really read the file
    assert used <= budget, "private memory grew %.1f MiB during the fit; budget %.1f MiB" % (used / 2 ** 20,
                                                                                         budget / 2 ** 20)
    ctl = run("in_ram")                                     # the measurement sees an in-RAM load of the same file
    assert ctl["peak"] - ctl["c0"] > budget


# ------------------------------------------------------------------------------------------ OOC4
class _Store(object):
    def __init__(self):
        self.data, self.saves = None, 0

    def load(self):
        return self.data

    def save(self, data):
        self.data, self.saves = data, self.saves + 1


class _Killed(Exception):
    pass


def test_ooc4_a_fit_stopped_between_trees_resumes_from_its_checkpoint(tmp_path, monkeypatch, record_trees):
    mod = M()
    _small_blocks(monkeypatch)
    monkeypatch.setattr(mod, "RF_CKPT_EVERY", 3)
    sigs, _ = record_trees
    X, normal, target, Xs, normal_s = _data(seed=11)
    mm = _write_memmap(tmp_path / "res.f32", X)
    mats = [("s", mod._tree_matrix(Xs, None, normal_s))]
    budget = _budget_for(X.shape[0], X.shape[1], 700, Xs.shape[0], 2)
    full, full_info = mod.rf_forest(mm, None, normal, target, PARAMS, mats, n_trees=10, budget=budget)
    full_sigs = list(sigs)

    store = _Store()

    def kill_at_7(t):
        if t == 7:
            raise _Killed()

    del sigs[:]
    with pytest.raises(_Killed):
        mod.rf_forest(mm, None, normal, target, PARAMS, mats, n_trees=10, budget=budget, store=store,
                      caller_key="fit-A", on_tree=kill_at_7)
    assert store.saves == 2                                   # after trees 3 and 6
    del sigs[:]
    f, info = mod.rf_forest(mm, None, normal, target, PARAMS, mats, n_trees=10, budget=budget, store=store,
                            caller_key="fit-A")
    assert info["resumed_from_tree"] == 6
    assert sigs == full_sigs[6:]                              # only trees 6-9 were fitted again, the same trees
    assert f["s"].tobytes() == full["s"].tobytes()
    assert info["samples_sha256"] == full_info["samples_sha256"]
    # a finished fit's checkpoint returns the result without fitting a tree
    del sigs[:]
    f2, info2 = mod.rf_forest(mm, None, normal, target, PARAMS, mats, n_trees=10, budget=budget, store=store,
                              caller_key="fit-A")
    assert sigs == [] and info2["resumed_from_tree"] == 10 and f2["s"].tobytes() == full["s"].tobytes()
    # another fit (another caller key, or other settings) never uses it
    del sigs[:]
    _, info3 = mod.rf_forest(mm, None, normal, target, PARAMS, mats, n_trees=10, budget=budget, store=store,
                             caller_key="fit-B")
    assert info3["resumed_from_tree"] == 0 and len(sigs) == 10


# ------------------------------------------------------------------------------------------ OOC5
def test_ooc5_the_stride_is_gone_and_a_too_small_budget_refuses():
    mod = M()
    H = T.rivals_harness()
    for name in ("rf_stride", "rf_max_samples"):
        assert not hasattr(mod, name), name
    for name in ("rf_rows", "board_rf_stride", "_probe_rf"):
        assert not hasattr(H, name), name
    assert H.board_rf_method()["method"] == mod.RF_METHOD
    assert mod.rf_rows_per_tree(11_338) == 11_338 and mod.rf_rows_per_tree(2_680_841) == mod.RF_ROWS_PER_TREE
    X, normal, target, Xs, normal_s = _data(n=500, p=6)
    with pytest.raises(mod.ModelRefusal, match="budget"):
        mod.rf_forest(X, None, normal, target, PARAMS, [], n_trees=2, budget=1 << 20)


# ------------------------------------------------------------------------------------------ OOC6-OOC9 (Z check 4)
# Moved here from the Z2 skeptic review (review_tests_z/test_z_rf_skeptic.py Z1, Z2, Z3, by its author) because
# OOC1 builds its reference with the same _rf_draws and _tree_matrix it tests. These tests re-implement the
# written draw rule and the gathering here, WITHOUT calling the models helpers, and compare with plain sklearnex
# trees.
def _spec_draws(n, m, n_trees):
    """The board's written rule, re-implemented: one default_rng(0); per tree in order rows = integers(0, n, m)
    sorted, then random_state = integers(0, 2**31 - 1)."""
    rng = np.random.default_rng(0)
    for _ in range(n_trees):
        idx = rng.integers(0, n, size=m, dtype=np.int64)
        seed = int(rng.integers(0, 2 ** 31 - 1))
        yield np.sort(idx, kind="stable"), seed


def _sk_data(n=2500, p=11, n_score=301, seed=21):
    rng = np.random.default_rng(seed)                    # synthetic test data only
    X = rng.standard_normal((n, p)).astype(np.float32)
    X[rng.random((n, p)) < 0.1] = np.nan
    X[:, 3] = np.round(X[:, 3])                          # a discrete column (ties)
    normal = rng.uniform(-2.0, 2.0, n)
    target = np.nan_to_num(X[:, 0]).astype(np.float64) * 3 - np.nan_to_num(X[:, 2]) + rng.standard_normal(n)
    Xs = rng.standard_normal((n_score, p)).astype(np.float32)
    Xs[rng.random((n_score, p)) < 0.1] = np.nan
    ns = rng.uniform(-2.0, 2.0, n_score)
    return X, normal, target, Xs, ns


def _sk_write(path, X, header=0, tail_rows=0, poison=np.inf):
    """Row-major file: `header` bytes of 0xFF, the rows block by block, then tail_rows poison rows."""
    with open(path, "wb") as fh:
        fh.write(b"\xff" * header)
        for a in range(0, X.shape[0], 500):
            fh.write(np.ascontiguousarray(X[a:a + 500], dtype=np.float32).tobytes())
        if tail_rows:
            fh.write(np.full((tail_rows, X.shape[1]), poison, dtype=np.float32).tobytes())
    return np.memmap(str(path), dtype=np.float32, mode="r", offset=header, shape=X.shape)


def _sk_gather(X, normal, fr):
    S = np.array(X[fr], dtype=np.float32, copy=True)
    S[np.isnan(S)] = 0.0
    return np.concatenate([S, np.asarray(normal, dtype=np.float64)[fr].astype(np.float32)[:, None]], axis=1)


def _sk_score(Xs, ns):
    S = np.array(Xs, dtype=np.float32, copy=True)
    S[np.isnan(S)] = 0.0
    return np.concatenate([S, ns.astype(np.float32)[:, None]], axis=1)


def _sk_knobs(monkeypatch, m=600, block_rows=37, p=11):
    mod = M()
    monkeypatch.setattr(mod, "RF_ROWS_PER_TREE", m)
    monkeypatch.setattr(mod, "RF_READ_BLOCK_BYTES", block_rows * p * 4)
    monkeypatch.setattr(mod, "RF_SLACK_BYTES", 0)


@pytest.fixture
def spy_trees(monkeypatch):
    mod = M()
    orig = mod._rf_tree
    got = []

    def wrapped(sample, target, params, seed):
        tree = orig(sample, target, params, seed)
        got.append({"sample": np.array(sample, copy=True), "target": np.array(target, copy=True),
                    "seed": int(seed), "onedal": getattr(tree, "_onedal_estimator", None) is not None,
                    "root": int(tree.estimators_[0].tree_.n_node_samples[0])})
        return tree

    monkeypatch.setattr(mod, "_rf_tree", wrapped)
    return got


class _SpyFile(object):
    def __init__(self, fh, log):
        self.fh, self.log, self.pos = fh, log, 0

    def seek(self, off, *a):
        self.pos = int(off)
        return self.fh.seek(off, *a)

    def readinto(self, mv):
        r = self.fh.readinto(mv)
        self.log.append((self.pos, int(r or 0)))
        self.pos += int(r or 0)
        return r

    def close(self):
        return self.fh.close()


@pytest.fixture
def spy_reads(monkeypatch):
    mod = M()
    log, readers = [], []
    base = mod._RowReader

    class Spy(base):
        def __init__(self, X, block_rows):
            base.__init__(self, X, block_rows)
            readers.append(self)
            self.file_path_used = self.fh is not None
            if self.fh is not None:
                self.fh = _SpyFile(self.fh, log)

    monkeypatch.setattr(mod, "_RowReader", Spy)
    return log, readers


def test_ooc6_the_draws_follow_the_written_rule():
    mod = M()
    for n, n_trees in ((9292, 300), (11338, 40), (2_205_498, 12)):
        m = mod.rf_rows_per_tree(n)
        assert m == min(200_000, n)
        for (t, idx, seed), (sidx, sseed) in zip(mod._rf_draws(n, m, n_trees), _spec_draws(n, m, n_trees)):
            assert idx.dtype == np.int64 and idx.size == m
            assert np.array_equal(idx, sidx) and seed == sseed, (n, t)


def test_ooc7_every_tree_spans_all_rows_and_300_trees_reach_every_row_at_ndvi_size():
    mod = M()
    n = 2_205_498                                     # NDVI tune rows (SPEC_RIVALS 2.9, _bench/z2_rf_plans.py)
    m = mod.rf_rows_per_tree(n)
    hits = np.zeros(n, dtype=np.int32)
    seeds = set()
    for t, idx, seed in mod._rf_draws(n, m, mod.RF_TREES):
        assert idx[0] < n * 0.001 and idx[-1] > n * 0.999, t      # each tree's own rows span the file
        hits += np.bincount(idx, minlength=n).astype(np.int32)
        seeds.add(seed)
    assert len(seeds) == mod.RF_TREES
    assert hits.sum() == mod.RF_TREES * m
    assert int((hits == 0).sum()) == 0, "some fit rows are never drawn by any tree"
    dec = np.add.reduceat(hits.astype(np.int64), np.linspace(0, n, 11).astype(np.int64)[:-1])
    exp = mod.RF_TREES * m / 10.0
    assert np.all(np.abs(dec - exp) < 6 * np.sqrt(exp)), dec          # uniform over the file


@pytest.mark.parametrize("case", ["header_offset_odd_blocks", "row_subset_poisoned", "one_tree_per_batch"])
def test_ooc8_each_tree_gets_exactly_its_own_rows(case, tmp_path, monkeypatch, spy_trees, spy_reads):
    mod = M()
    _sk_knobs(monkeypatch)
    X, normal, target, Xs, ns = _sk_data()
    n, p = X.shape
    n_trees = 7
    rows = None
    Xfile = X.copy()
    if case == "row_subset_poisoned":
        rows = np.flatnonzero(np.arange(n) % 4 != 1).astype(np.int64)
        out = np.setdiff1d(np.arange(n), rows)
        Xfile[out] = np.inf                                # a non-fit row in a tree would refuse or move a split
        normal = normal.copy()
        target = target.copy()
        normal[out] = 1e30
        target[out] = 1e30
    mm = _sk_write(tmp_path / "fit.f32", Xfile, header=96, tail_rows=40)
    n_eff = n if rows is None else rows.size
    m = mod.rf_rows_per_tree(n_eff)
    mats = [("s", _sk_score(Xs, ns))]
    k = 1 if case == "one_tree_per_batch" else 2
    budget = _budget_for(n, p, m, Xs.shape[0], k + 0.3)
    f, info = mod.rf_forest(mm, rows, normal, target, PARAMS, mats, n_trees=n_trees, budget=budget)
    log, readers = spy_reads
    assert readers and readers[0].file_path_used, "the memmap on a file was not read with file reads"
    assert len(spy_trees) == n_trees and info["batches"] >= 2
    if case == "one_tree_per_batch":
        assert info["trees_per_batch"] == [1] * n_trees
    for rec, (sidx, sseed) in zip(spy_trees, _spec_draws(n_eff, m, n_trees)):
        fr = sidx if rows is None else rows[sidx]
        assert rec["seed"] == sseed
        assert rec["sample"].shape == (m, p + 1)
        assert rec["sample"].tobytes() == _sk_gather(X, normal, fr).tobytes()
        assert rec["target"].tobytes() == np.asarray(target, dtype=np.float64)[fr].tobytes()
        assert np.isfinite(rec["sample"]).all() and np.all(np.abs(rec["target"]) < 1e29)
    lo, hi = 96, 96 + n * p * 4                          # every byte read lies inside the fit-set rows
    assert min(o for o, _ in log) >= lo and max(o + r for o, r in log) <= hi


def test_ooc9_forest_equals_plain_sklearnex_trees_on_the_same_samples(tmp_path, monkeypatch, spy_trees):
    from sklearnex.ensemble import RandomForestRegressor
    mod = M()
    _sk_knobs(monkeypatch, m=900)
    X, normal, target, Xs, ns = _sk_data(n=3100, seed=41)
    n, p = X.shape
    mm = _sk_write(tmp_path / "fit.f32", X)
    m = mod.rf_rows_per_tree(n)
    n_trees = 8
    S = _sk_score(Xs, ns)
    for params in (PARAMS, {"max_features": 0.2, "min_samples_leaf": 50}):
        del spy_trees[:]
        f, info = mod.rf_forest(mm, None, normal, target, params, [("s", S)], n_trees=n_trees,
                                budget=_budget_for(n, p, m, S.shape[0], 3))
        acc = np.zeros(S.shape[0])
        for sidx, seed in _spec_draws(n, m, n_trees):
            est = RandomForestRegressor(n_estimators=1, bootstrap=False, max_features=float(params["max_features"]),
                                        min_samples_leaf=int(params["min_samples_leaf"]), criterion="squared_error",
                                        random_state=seed, n_jobs=mod.THREADS).fit(_sk_gather(X, normal, sidx),
                                                                                    target[sidx])
            acc += np.asarray(est.predict(S), dtype=np.float64)
        ref = acc / float(n_trees)
        assert f["s"].tobytes() == ref.tobytes(), (params, float(np.abs(f["s"] - ref).max()))
        assert all(r["onedal"] for r in spy_trees), "a tree fell back from oneDAL"
        assert all(r["root"] == m for r in spy_trees), [r["root"] for r in spy_trees]


# ------------------------------------------------------------------------------------------ OOC10 (heavy, opt-in)
# Z check 4: OOC3 checks RAM at 20k rows per tree and 250 columns only. OOC10 (the Z2 review's Z8) checks it at the
# production shape: 200,000 rows per tree, 507 + 1 columns, a 95,184-row score set (NDVI refit), the public
# fit_predict path, a budget that forces one tree per batch. ~1 GB synthetic file, ~2.5 GiB RAM, ~3 min.
# Runs only with RIVALS_HEAVY=1.
_HEAVY_N, _HEAVY_P, _HEAVY_SCORE = 500_000, 507, 95_184

_HEAVY_RAM = textwrap.dedent(r'''
    import json, sys, time
    import numpy as np, psutil
    sys.path.insert(0, sys.argv[2]); sys.path.insert(0, sys.argv[1])
    from rivals import models as M
    path, n, p, sr = sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
    rng = np.random.default_rng(5)                                          # synthetic data only
    X = np.memmap(path, dtype=np.float32, mode="r", shape=(n, p))
    y = rng.standard_normal(n)
    fit = M.FitData(name="fit", X=X, columns=tuple("f%d" % i for i in range(p)), y=y,
                    normal={"identity": np.zeros(n)})
    Xs = rng.standard_normal((sr, p), dtype=np.float32)
    score = [M.ScoreData(name="s", X=Xs, normal={"identity": np.zeros(sr)})]
    m = M.rf_rows_per_tree(n)
    plan = M._rf_budget(n, p, m, sr, 1e12)
    fixed = sum(v for k, v in plan.items() if k not in ("parent_budget", "row_bytes", "block_rows"))
    budget = fixed + 1.3 * m * (plan["row_bytes"] + 8)
    M.RF_RAM_BUDGET = budget
    M.RF_TREES = 3
    params = {"max_features": 0.5, "min_samples_leaf": 5, "link": "identity", "c": None, "ub": None}
    M.link_forward(np.zeros(4), "identity", None, None)                    # engine import before the baseline
    M._rf_tree(np.zeros((64, p + 1), np.float32), np.arange(64.0), params, 0)
    proc = psutil.Process()
    c0 = proc.memory_info().private
    p0 = proc.memory_info().peak_pagefile
    t0 = time.time()
    res = M.fit_predict("rf", params, fit, score, (3,))
    wall = time.time() - t0
    mi = proc.memory_info()
    info = {k: res.info[k] for k in ("batches", "trees_per_batch", "parent_rows_per_batch", "read_gib",
                                      "read_seconds", "fit_seconds", "predict_seconds")}
    print(json.dumps({"c0": c0, "peak_before": p0, "peak": mi.peak_pagefile, "budget": budget, "fixed": fixed,
                      "wall": wall, "info": info}))
''')


@pytest.mark.heavy
@pytest.mark.skipif(sys.platform != "win32", reason="Windows private-bytes peak")
def test_ooc10_ram_within_budget_at_the_production_shape(tmp_path):
    path = tmp_path / "ndvi_width.f32"
    rng = np.random.default_rng(2026)                                     # synthetic data only
    with open(path, "wb") as fh:                                          # row-major row blocks
        for a in range(0, _HEAVY_N, 20_000):
            blk = rng.standard_normal((min(_HEAVY_N, a + 20_000) - a, _HEAVY_P), dtype=np.float32)
            blk[blk > 1.645] = np.nan
            fh.write(blk.tobytes())
    script = tmp_path / "ram.py"
    script.write_text(_HEAVY_RAM, encoding="utf-8")
    out = subprocess.run([sys.executable, "-B", str(script), str(T.BUILD_ROOT), str(_engine_root()), str(path),
                          str(_HEAVY_N), str(_HEAVY_P), str(_HEAVY_SCORE)], capture_output=True, text=True,
                         timeout=1800)
    assert out.returncode == 0, out.stderr[-4000:]
    rec = json.loads(out.stdout.strip().splitlines()[-1])
    assert rec["peak_before"] <= rec["c0"] + (64 << 20), "the peak was set before the fit; the test cannot see it"
    growth = rec["peak"] - rec["c0"]
    (tmp_path / "ooc10_ram.json").write_text(json.dumps(dict(rec, growth=growth), indent=1), encoding="utf-8")
    assert rec["info"]["batches"] == 3
    assert growth <= rec["budget"], "private memory grew %.2f GiB; budget %.2f GiB" % (growth / 2 ** 30,
                                                                                       rec["budget"] / 2 ** 30)


def _engine_root():
    from rivals.tests import conftest as C
    return C.ENGINE_ROOT
