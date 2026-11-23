"""The RAM tactics (D:/treeroute/engine_next/RAM_TACTICS.md): each saves RAM and changes no byte.

  4  frames built in one go: _one_go_frame equals the insert-by-insert build (columns, order, dtypes, values); the
     column reader's lagged frame (one preallocated float64 block in kept order) equals the old build exactly;
  5  driver files decoded in batches: read_unit_rows equals the whole-file read and its unit filter (rows, order,
     schema with metadata, values), at any batch size, for one or many row groups, an empty file and no match; a
     column reader built with it equals one built with the whole-file read;
  6  the GLS donor matrix as a C-ordered float32 temp memmap: the GLS forest's fit is byte-identical on it
     (out-of-bag sigma, predictions, every tree's arrays), weight_model_for_cut with matrix_dir gives the same
     model and record as in RAM, and the temp file is deleted after it returns or raises; its RAM parts
     (_file_backed) leave the matrix out of the build and the answer read only;
  7  the blocked finite check equals numpy's; the census release drops the static table.
Tiny sizes only.
"""

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from test_fit_weights import _store_for, patched, singles, tree_group  # noqa: F401
from test_pipeline_lastvalue import _lags, _reader
from test_vault_world import make_context, make_world
from treeroute import engine_constants as K
from treeroute.derive.shapes import CutKind


# ------------------------------------------------------------------------------------------- tactic 4
def _inserts_frame(pairs, index=None):
    """The old build: a frame of the first two columns, then one insert a column ('_present' as the scalar 1.0)."""
    out = pd.DataFrame(dict(pairs[:2]), index=index)
    for name, values in pairs[2:]:
        out[name] = 1.0 if name == "_present" else values
    return out


def _same_frame(a, b):
    pd.testing.assert_frame_equal(a, b, check_exact=True)
    assert list(a.columns) == list(b.columns) and list(a.dtypes) == list(b.dtypes)
    assert a.index.equals(b.index) and type(a.index) is type(b.index)
    for c in range(a.shape[1]):
        x, y = a.iloc[:, c].to_numpy(), b.iloc[:, c].to_numpy()
        if x.dtype.kind in "fiub":
            assert x.tobytes() == y.tobytes()


def test_one_go_frame_equals_the_insert_by_insert_build():
    from treeroute.pipeline.data import _one_go_frame

    rng = np.random.default_rng(5)
    n = 37
    f32 = rng.normal(size=n).astype(np.float32)
    f32[::5] = np.nan
    pairs = [("_unit_code", np.arange(n, dtype=np.int64)), ("_step", np.arange(n, dtype=np.int64) + 100),
             ("_present", np.full(n, 1.0)), ("a", f32), ("b", rng.normal(size=n)),
             ("c", (np.arange(n) % 3).astype(np.int8)), ("d", np.arange(n) % 2 == 0),
             ("e", np.array(["u%d" % i for i in range(n)], dtype=object)), ("a", f32 * 2)]   # 'a' again: replaced
    _same_frame(_one_go_frame(pairs), _inserts_frame(pairs))
    empty = [(k, v[:0]) for k, v in pairs]
    _same_frame(_one_go_frame(empty), _inserts_frame(empty))


def _old_lagged(reader, lags):
    """ColumnReader.lagged as it was before tactic 4 (column inserts, then the kept columns selected), uncached."""
    from treeroute.io.apply import apply_lags
    from treeroute.io.joins import coarse_periods, join_coarser_column
    from treeroute.io.lastvalue import fill_last_value
    from treeroute.io.steps import cadence_identity, cadence_view
    from treeroute.pipeline import data as D

    target_id = cadence_identity(cadence_view(reader.cadence))
    same, coarse, static = [], [], []
    for c in reader.kept:
        facts = reader.spec.store_facts.get(c)
        kind = D._v(getattr(getattr(facts, "cadence", None), "kind", None))
        if kind == "static":
            static.append(c)
            continue
        if cadence_identity(cadence_view(lags[c].column_cadence)) == target_id:
            same.append(c)
        else:
            coarse.append(c)
    out = pd.DataFrame(index=reader.raw.index)
    if same:
        moved = apply_lags(reader.raw[same], reader.codes, reader.steps, {c: lags[c] for c in same}, reader.cadence)
        for c in same:
            out[c] = moved[c].to_numpy(dtype=np.float64)
    for c in coarse:
        cad = lags[c].column_cadence
        grid_periods = coarse_periods(reader.steps, reader.cadence, cad)
        store = reader._column_store(c)
        if store is not None and not store.by_step:
            frame = store.coarse[[c]]
            ucodes = store.coarse[D.UNIT_CODE].to_numpy()
            periods = store.coarse["_period"].to_numpy()
        else:
            frame, ucodes, periods = reader.raw[[c]], reader.codes, grid_periods
        joined = join_coarser_column(pd.DataFrame(index=reader.raw.index), reader.codes, grid_periods, frame,
                                     ucodes, periods, c, cad, reader.cadence, lags[c])
        out[c] = joined[c].to_numpy(dtype=np.float64)
    for c in static:
        out[c] = reader.raw[c].to_numpy(dtype=np.float64)
    out = out[list(reader.kept)]
    trees = set(reader.spec.tree_features)
    out, _ = fill_last_value(out, reader.codes, reader.steps, tuple(c for c in reader.kept if c in trees),
                             reader.cadence)
    return out


def _old_read_unit_rows(path, columns, unit_col, unit_set):
    """The driver read as it was before tactic 5: the whole file's columns, then the unit filter."""
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    with pq.ParquetFile(path) as pf:
        table = pf.read(columns=list(columns))
    return table.filter(pc.is_in(table.column(unit_col).cast(pa.string()), value_set=unit_set))


def test_the_column_reader_and_its_lagged_frame_are_the_same_bytes_as_before(tmp_path, monkeypatch):
    from treeroute.pipeline import data as D

    new, cad = _reader(tmp_path / "new")
    monkeypatch.setattr(D, "read_unit_rows", _old_read_unit_rows)
    monkeypatch.setattr(D, "_one_go_frame", _inserts_frame)
    old, cad_old = _reader(tmp_path / "old")
    monkeypatch.undo()
    _same_frame(new.raw, old.raw)
    assert [(s.template, s.columns, s.by_step) for s in new.stores] == [(s.template, s.columns, s.by_step)
                                                                       for s in old.stores]
    assert all(np.array_equal(a.present, b.present) for a, b in zip(new.stores, old.stores))
    assert [p.split("pk")[-1] for p in new.files_read] == [p.split("pk")[-1] for p in old.files_read]
    lags = _lags(cad)
    lagged = new.lagged(lags)
    assert {"x1", "x2", "s1"} <= set(new.kept)                      # same-step, coarser and static columns
    _same_frame(lagged, _old_lagged(new, lags))
    _same_frame(old.lagged(_lags(cad_old)), _old_lagged(old, _lags(cad_old)))


# ------------------------------------------------------------------------------------------- tactic 5
def _write_files(folder):
    rng = np.random.default_rng(1)
    n = 3000
    df = pd.DataFrame({"cell": np.array(["c%04d" % (i % 400) for i in range(n)], dtype=object), "reg": "r1",
                       "yr": np.full(n, 7, dtype=np.int16), "mo": (np.arange(n) % 12 + 1).astype(np.int8),
                       "v1": rng.normal(size=n).astype(np.float32), "v2": rng.normal(size=n)})
    df.loc[::7, "v1"] = np.nan
    folder.mkdir(parents=True, exist_ok=True)
    df.to_parquet(folder / "one.parquet", index=False)
    df.to_parquet(folder / "many.parquet", index=False, row_group_size=700)
    df.iloc[:0].to_parquet(folder / "empty.parquet", index=False)
    df.assign(cell="zz").to_parquet(folder / "nomatch.parquet", index=False)
    return ["one", "many", "empty", "nomatch"]


@pytest.mark.parametrize("batch", [7, 1000, 65536])
def test_read_unit_rows_equals_the_whole_file_read(tmp_path, monkeypatch, batch):
    import pyarrow as pa

    from treeroute.pipeline.data import read_unit_rows

    monkeypatch.setattr(K, "READER_BATCH_ROWS", batch)
    units = pa.array(sorted({"c%04d" % i for i in range(0, 400, 7)} | {"absent"}), type=pa.string())
    cols = ["cell", "mo", "yr", "v2", "v1"]                          # not the file's column order
    for name in _write_files(tmp_path):
        path = tmp_path / ("%s.parquet" % name)
        got, want = read_unit_rows(path, cols, "cell", units), _old_read_unit_rows(path, cols, "cell", units)
        assert got.column_names == want.column_names == cols
        assert got.schema.equals(want.schema, check_metadata=True) and got.equals(want)
        _same_frame(got.to_pandas(), want.to_pandas())
    assert K.get("P7.reader_batch_rows") == 65536


# ------------------------------------------------------------------------------------------- tactic 6
def _forest_bytes(X, e):
    import hashlib

    from sklearn.ensemble import RandomForestRegressor

    from treeroute.fit.weights import _features

    f = RandomForestRegressor(n_estimators=K.GLS_TREES, max_depth=K.GLS_MAX_DEPTH, min_samples_leaf=K.GLS_MIN_LEAF,
                              max_features=K.GLS_MAX_FEATURES, bootstrap=K.GLS_BOOTSTRAP,
                              random_state=K.GLS_RANDOM_STATE, n_jobs=K.GLS_THREADS, oob_score=True)
    f.fit(_features(X, "X"), e)
    h = hashlib.sha256()
    h.update(np.asarray(f.oob_prediction_, dtype=np.float64).tobytes())
    h.update(np.asarray(f.predict(np.asarray(X[:100], dtype=np.float32)), dtype=np.float64).tobytes())
    for est in f.estimators_:
        t = est.tree_
        for arr in (t.feature, t.threshold, t.value, t.children_left, t.children_right, t.n_node_samples):
            h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def test_the_gls_forest_is_byte_identical_on_a_temp_memmap(patched, tmp_path):
    from treeroute.runs.tempmem import temp_memmap

    rng = np.random.default_rng(11)
    X = rng.normal(size=(900, 14)).astype(np.float32)
    X[rng.random(size=X.shape) < 0.05] = 0.0
    e = np.abs(X[:, 0].astype(np.float64) * 0.7 + X[:, 1] ** 2 * 0.2 + rng.normal(size=900) * 0.1)
    with temp_memmap(tmp_path, "forest_probe", X.shape, np.float32) as tm:
        M = tm.array
        for a in range(0, X.shape[0], 251):                         # row blocks, as the donor matrix is written
            M[a:a + 251] = X[a:a + 251]
        assert M.flags.c_contiguous and M.dtype == np.float32
        got = _forest_bytes(M, e)
        del M
    assert got == _forest_bytes(X, e) == _forest_bytes(X.copy(), e)
    assert list(tmp_path.iterdir()) == []


def _record(model):
    from treeroute.derive.derived import derived_entry
    from treeroute.fit.weights import weight_model_record
    from treeroute.runs.atomic import dumps

    return json.loads(dumps(derived_entry(weight_model_record(model))))


def test_weight_model_for_cut_with_a_memmap_matrix_is_the_same_model(patched, tmp_path, monkeypatch):
    from treeroute.fit.weights import weight_model_for_cut
    from treeroute.runs import tempmem

    w = make_world()
    store, d, A = _store_for(w)
    ram = weight_model_for_cut(make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD), store,
                               tree_group(), blocks=singles())
    made = []
    real = tempmem.temp_memmap

    def spy(temp_dir, tag, shape, dtype):
        made.append((tag, tuple(shape), np.dtype(dtype).name))
        return real(temp_dir, tag, shape, dtype)
    monkeypatch.setattr(tempmem, "temp_memmap", spy)
    notes = []
    temp = tmp_path / "run_temp"
    temp.mkdir()
    mm = weight_model_for_cut(make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD), store,
                              tree_group(), blocks=singles(), matrix_dir=temp, echo=notes.append)
    assert made == [("gls_donor_l0_c%d" % d.cut, (d.y.size, d.X.shape[1]), "float32")]
    assert list(temp.iterdir()) == []                               # deleted before the call returned
    assert mm.forest.oob_sigma.tobytes() == ram.forest.oob_sigma.tobytes()
    assert (mm.cut, mm.lead, mm.sigma_floor, mm.clip_low, mm.clip_high, mm.fold) == \
        (ram.cut, ram.lead, ram.sigma_floor, ram.clip_low, ram.clip_high, ram.fold)
    assert _record(mm) == _record(ram)
    probe = np.asarray(d.X[:50], dtype=np.float32)
    assert mm.forest.predict(probe).tobytes() == ram.forest.predict(probe).tobytes()
    assert any("memory given back before the donor matrix" in n and "temp file" in n for n in notes)


def test_the_memmap_is_deleted_and_the_original_error_raised_when_a_step_fails(patched, tmp_path):
    from treeroute.fit.weights import weight_model_for_cut

    w = make_world()
    store, d, A = _store_for(w)
    calls = []
    real_view = store.unit_view

    def failing_view(row_keys, kind):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("planted store failure")
        return real_view(row_keys, kind)
    store.unit_view = failing_view
    temp = tmp_path / "run_temp"
    temp.mkdir()
    with pytest.raises(RuntimeError, match="planted store failure"):
        weight_model_for_cut(make_context(w, 0, CutKind.FIT), make_context(w, 0, CutKind.GUARD), store,
                             tree_group(), blocks=singles(), matrix_dir=temp, echo=lambda s: None)
    assert list(temp.iterdir()) == []


def test_file_backed_parts_leave_the_matrix_out_of_the_build_and_the_answer_read_only():
    from treeroute.fit.weights import _file_backed, gls_ram_bytes

    parts = gls_ram_bytes({"g_a": 1000, "g_b": 3000}, 50, {"g_a": 200, "g_b": 100})
    fb = _file_backed(parts)
    m = parts["matrix"]
    assert fb["matrix_file"] == m and fb["matrix"] == m
    assert fb["build"] == parts["build"] - m and fb["answer_read"] == parts["answer_read"] - m
    assert fb["forest"] == parts["forest"]                          # the forest's fit copies its input
    assert fb["peak"] == max(fb["build"], fb["answer_read"], fb["forest"]) <= parts["peak"]


def test_the_gls_disk_check_refuses_a_matrix_file_that_does_not_fit(tmp_path, monkeypatch):
    from treeroute.fit.weights import WeightsRefusal, _file_backed, _refuse_gls_ram, gls_ram_bytes
    from treeroute.runs import preflight

    fb = _file_backed(gls_ram_bytes({"g_a": 1000}, 50, {"g_a": 200}))
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: 1 << 40)
    monkeypatch.setattr(preflight, "free_disk_bytes", lambda path: fb["matrix_file"] - 1)
    with pytest.raises(WeightsRefusal, match="donor matrix file"):
        _refuse_gls_ram(fb, tmp_path)
    monkeypatch.setattr(preflight, "free_disk_bytes", lambda path: fb["matrix_file"])
    _refuse_gls_ram(fb, tmp_path)                                   # exactly enough: go


# ------------------------------------------------------------------------------------------- tactic 7
def test_the_blocked_finite_check_equals_numpy(monkeypatch):
    from treeroute.fit.weights import _all_finite

    monkeypatch.setattr(K, "DONOR_BLOCK_VALUES", 30)                # blocks of 3 rows of 10 columns
    base = np.zeros((11, 10), dtype=np.float32)
    assert _all_finite(base) is True
    for r, bad in ((0, np.nan), (5, np.inf), (10, -np.inf), (2, np.nan)):
        a = base.copy()
        a[r, r % 10] = bad
        assert _all_finite(a) is bool(np.isfinite(a).all()) is False
    assert _all_finite(np.zeros((0, 10), dtype=np.float32)) is True


def test_the_census_release_drops_the_static_table():
    from treeroute.pipeline.run import Pipeline

    cache = {"k": 1}
    fake = SimpleNamespace(census=SimpleNamespace(rows=10, n_units=lambda: 2), presence=SimpleNamespace(_cache=cache),
                           static=pd.DataFrame({"a": [1, 2]}), log=lambda s: None)
    Pipeline._release_census(fake)
    assert fake.census is None and fake.static is None and cache == {}
    assert fake.census_counts == {"rows": 10, "units": 2}
