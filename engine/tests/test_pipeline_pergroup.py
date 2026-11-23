"""Plan R20's per-group batching (owner task 2026-10-06), on test_pipeline's synthetic package read from its files.

The per-group path (every command's default) builds the picked units' column reader one group at a time and walks
every router pass group by group with one group's tree-answer tables on disk at a time. Here:
  - the per-group column readers give the whole reader's lagged frame row for row, its last-value record (counts
    summed over the groups), its static stratum values and its store plan;
  - the separability guard refuses a planted feature script whose output depends on the other groups' rows
    (before any reader of the per-group path is used), and the whole path (gates only) would not have noticed;
  - after a grouped pass the stores hold no table; the disk pre-flight counts the pools and ONE group's tables
    (the largest), not every group's;
  - a group's column reader that does not fit the RAM available is refused before it is built (GiB in the message);
  - route.kinds' only_group routes one group's units with the whole pass's bytes.
The byte identity of whole runs (per group against the whole path) is test_pipeline_census.py's first test.
"""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from test_pipeline import FAKE_LAUNCH, _machine, make_pipeline_package, sklearnex_patched  # noqa: F401
from treeroute.errors import RefusedError

CROSS_GROUP_FEATURES = '''\
"""PLANTED (test only): the router context depends on how many units the frame holds, so a group's value computed
alone differs from its value computed beside the other groups."""
import pandas as pd

OUTPUTS = {
    "ctx:m": {"dtype": "float32", "units": "1",
              "cadence": {"kind": "regular", "length": 1, "unit": "month"},
              "scope": "global", "stamp": "period_end",
              "window": {"length": 1, "unit": "month", "align": "backward"},
              "legal_range": [1.0, 12.0], "derived_from": ["step_month"], "reads_target": False,
              "fact_status": "verified"},
}


def build(frame, keys):
    month = [c for c, part in keys["time"].items() if part == "month"][0]
    n = float(frame[keys["unit"]].nunique())
    return pd.DataFrame({"ctx:m": (1.0 + (frame[month] - 1.0) * n / (n + 1.0)).astype("float32")}, index=frame.index)
'''


def _pipe(pkg, base, per_group=True, streamed=True):
    from treeroute.pipeline.run import Pipeline

    return Pipeline(pkg, base / "runs", "smoke", machine=_machine(base), echo=lambda s: None,
                    launch_record=FAKE_LAUNCH, streamed=streamed, per_group=per_group)


def _derived(pkg, base, per_group=True):
    p = _pipe(pkg, base, per_group)
    p._lock()
    try:
        p._load()
        p._groups()
        p._preflight_target()
        p._read()
        p._derive()
        return p
    finally:
        p._release()


@pytest.fixture(scope="module")
def derived(tmp_path_factory):
    base = tmp_path_factory.mktemp("pergroup")
    pkg = make_pipeline_package(base / "pk", sparse=True)
    (base / "g").mkdir()
    (base / "w").mkdir()
    return pkg, _derived(pkg, base / "g", True), _derived(pkg, base / "w", False)


def test_the_per_group_readers_give_the_whole_readers_values(derived):
    from treeroute.derive import derived_sha256

    _, pg, pw = derived
    assert derived_sha256(pg.derived) == derived_sha256(pw.derived)
    readers, whole = pg.reader, pw.reader
    lags = pg.derived["R8"].value
    lw = whole.lagged(lags)
    assert len(readers.groups) > 1
    assert sum(readers.rows_of(g) for g in readers.groups) == len(whole.units)
    for g in readers.groups:
        r = readers.reader(g)
        lg = readers.lagged(g, lags)
        pos = whole.base_rows(r.units, r.steps)
        for c in whole.kept:
            a, b = lg[c].to_numpy(dtype=np.float64), lw[c].to_numpy(dtype=np.float64)[pos]
            assert a.tobytes() == b.tobytes(), (g, c)
        for c in r.outputs:
            assert r.raw[c].to_numpy().tobytes() == whole.raw[c].to_numpy()[pos].tobytes(), (g, c)
    readers.release()
    assert readers.last_value_record(lags) == whole.last_value_record(lags)
    assert pg.last_value.as_dict() == pw.last_value.as_dict()
    assert [(s["template"], s["columns"], s["by_step"]) for s in readers.data_manifest()["stores"]] == \
        [(s["template"], s["columns"], s["by_step"]) for s in whole.data_manifest()["stores"]]
    assert pg.data_manifest == pw.data_manifest
    assert readers.strata_unread == whole.strata_unread
    for c in pg.strata:
        pd.testing.assert_series_equal(pg.strata[c], pw.strata[c])
    sep = pg.separability
    assert sep["checked"] and sep["values_compared"] > 0 and sep["feature_outputs"] == ["ctx:m"]


def test_a_cross_group_feature_script_refuses_the_per_group_path(tmp_path):
    base = tmp_path
    pkg = make_pipeline_package(base / "pk", sparse=True)
    (Path(pkg) / "features" / "build.py").write_text(CROSS_GROUP_FEATURES, encoding="utf-8")
    (base / "g").mkdir()
    with pytest.raises(RefusedError, match="not group-separable") as info:
        _derived(pkg, base / "g", True)
    text = str(info.value)
    assert "R20" in text and "ctx:m" in text and "per-group path" in text
    # the whole path (gates only) reads every group together and does not notice
    (base / "w").mkdir()
    pw = _derived(pkg, base / "w", False)
    assert "R30" in pw.derived


def test_the_disk_plan_counts_the_largest_group_not_every_group(derived):
    from treeroute import engine_constants as K
    from treeroute.pipeline import run as RUN

    _, pg, _ = derived
    parts = pg.disk_plan()
    lists = pg.derived["R18:units"].value
    big = max(len(v) for v in lists.bank.values())
    trees = len(lists.bank) * pg.trees_per_group
    one = big * parts["steps"] * (trees - pg.trees_per_group) * np.dtype(K.TREE_DTYPE).itemsize
    assert parts["table_one_kind_largest_group"] == one
    assert parts["nowcast_tables_at_peak"] == RUN.NOWCAST_TABLE_KINDS * one
    assert parts["total"] == parts["pool"] + parts["history_block"] + max(
        parts["nowcast_tables_at_peak"], parts["lead_pool"] + parts["lead_guard_history_block"] + parts["lead_tables_at_peak"])
    every = sum(len(v) for v in lists.bank.values()) * parts["steps"] * (trees - pg.trees_per_group) *         np.dtype(K.TREE_DTYPE).itemsize
    assert parts["nowcast_tables_at_peak"] < RUN.NOWCAST_TABLE_KINDS * every       # not the sum over groups


def test_a_disk_plan_that_does_not_fit_is_refused(derived, tmp_path, monkeypatch):
    from treeroute import engine_constants as K
    from treeroute.runs import preflight

    _, pg, _ = derived
    pg.temp_dir = tmp_path
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)          # owner ruling Q1: no wait, so it refuses as before
    monkeypatch.setattr(preflight, "free_disk_bytes", lambda path: 1000)
    with pytest.raises(RefusedError, match="per-group schedule's temp disk") as info:
        pg._preflight_disk()
    assert "GiB" in str(info.value) and "ONE group's tables" in str(info.value)


def test_a_group_reader_that_does_not_fit_is_refused_before_it_is_built(derived, monkeypatch):
    """The RAM go/refuse of the per-group path counts ONE group's reader (its rows at a reader's peak, beside one
    driver file in flight) and refuses before that group's reader is built, with sizes in GiB."""
    from treeroute import engine_constants as K
    from treeroute.runs import preflight

    _, pg, _ = derived
    readers = pg.reader
    readers.release()
    g, n = readers.largest()
    need = pg.group_reader_bytes(n)
    assert need == preflight.column_reader_peak_bytes(n, pg._frame_columns()) + pg._driver_file_bytes()
    builds = readers.builds
    monkeypatch.setattr(K, "ROOM_MAX_WAIT_SECONDS", 0)          # owner ruling Q1: no wait, so it refuses as before
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: need - 1)
    with pytest.raises(RefusedError, match="one group's picked-unit column reader") as info:
        readers.reader(g)
    assert "G-DISK" in str(info.value) and "GiB" in str(info.value) and " GB" not in str(info.value)
    assert readers.builds == builds                       # refused before the reader was built
    monkeypatch.setattr(preflight, "available_ram_bytes", lambda: need)
    readers.reader(g)                                     # exactly enough: go
    assert readers.builds == builds + 1
    readers.release()


def test_only_group_routes_one_group_with_the_whole_pass_bytes(derived, tmp_path):
    """route.kinds' per-unit kernel with only_group: each group's units' rows equal the whole pass's rows, the other
    rows are NaN, and the reference check stays on the whole pass's first units."""
    from treeroute.derive.shapes import CutKind, Link
    from treeroute.fit.bank import fit_donor_bank
    from treeroute.fit.context import FitContext
    from treeroute.fit.pool import open_pool
    from treeroute.fit.tables import TreeAnswerStore
    from treeroute.pipeline import stages as ST
    from treeroute.route import kinds as RK

    _, _, pw = derived
    p = pw
    vg = p._vault(None)
    lists = p.derived["R18:units"].value
    spec17 = p.derived["R17"].value
    n = int(vg.grid.n_steps)
    rows = np.arange(len(vg.grid.unit_ids) * n, dtype=np.int64)
    lagged = p.reader.lagged(p.derived["R8"].value)
    base = p.reader.base_rows(vg.unit_ids, vg.steps)
    tv = lagged[list(p.spec.tree_features)].to_numpy(dtype=np.float32)
    cv = lagged[list(p.spec.context)].to_numpy(dtype=np.float32)
    cut = p.derived["R11"].value[0]
    with open_pool(tmp_path, "pool", rows, tuple(p.spec.tree_features), tuple(p.spec.context)) as pool:
        ST.fill_pool(pool, vg, lambda r: tv[base[r]], lambda r: cv[base[r]], np.zeros((rows.size, 0), np.float32),
                     lambda s: None)
        ctx = FitContext(p.derived, p.split_sets, vg.grid, vg.labels, pool, lists, 0, CutKind.FIT)
        bank = fit_donor_bank(ctx.donor_rows("bank"), p.trees_per_group)
        scored = sorted(u for g in lists.scored for u in lists.scored[g])
        keys = ST.unit_positions(vg, scored, int(cut.fit_cut) + 1, None)
        rows_p = ST.pass_rows(ctx, scored, vg.unit_ids[keys], vg.steps[keys], keys, "test")
        normals = ST.unit_normals(ctx, scored, Link.IDENTITY, None, None, 0.0, p.derived["R2"].value)
        unit_group = {u: g for g in lists.bank for u in lists.bank[g]}
        pr = ST.per_unit_rows(rows_p, Link.IDENTITY, None, None, normals, p.derived["R2"].value, unit_group)
        masks = ST.block_masks(bank.tree_group, p.blocks)
        with TreeAnswerStore.from_bank(bank, ST.row_group_of(vg), tmp_path, p.registry) as store:
            for g in sorted(lists.bank):
                store.build(g, "plain", ST.unit_positions(vg, lists.scored[g], None, None), ST.zero_filled(pool))
            whole = RK._route_per_unit_grid(pr, store, "plain", masks, 1.0)
            groups = np.asarray([unit_group[u] for u in np.asarray(pr.score_unit, dtype=object).tolist()], dtype=object)
            fitted = 0
            for g in sorted(lists.bank):
                one = RK._route_per_unit_grid(pr, store, "plain", masks, 1.0, only_group=g)
                sel = groups == g
                assert one.predictions[sel].tobytes() == whole.predictions[sel].tobytes(), g
                assert one.trees_off[sel].tobytes() == whole.trees_off[sel].tobytes(), g
                assert np.isnan(one.predictions[~sel]).all() and np.isnan(one.trees_off[~sel]).all()
                fitted += one.n_units_fitted
            assert fitted == whole.n_units_fitted


def test_a_bank_fitted_from_lazy_donor_features_is_the_eager_banks(derived, tmp_path):
    """Plan R20: FitContext.donor_rows_lazy hands the same rows (and the same fitctx log row) with features read
    one group at a time; fit.bank.fit_donor_bank on them fits the same trees, correctors and placebos byte for byte
    (the same bank fingerprint); the lazy matrix refuses to be read whole."""
    from treeroute.derive.shapes import CutKind
    from treeroute.fit.bank import fit_donor_bank
    from treeroute.fit.context import FitContext, FitContextRefusal
    from treeroute.fit.pool import open_pool
    from treeroute.pipeline import stages as ST

    _, _, p = derived
    vg = p._vault(None)
    lists = p.derived["R18:units"].value
    n = int(vg.grid.n_steps)
    rows = np.arange(len(vg.grid.unit_ids) * n, dtype=np.int64)
    lagged = p.reader.lagged(p.derived["R8"].value)
    base = p.reader.base_rows(vg.unit_ids, vg.steps)
    tv = lagged[list(p.spec.tree_features)].to_numpy(dtype=np.float32)
    with open_pool(tmp_path, "pool", rows, tuple(p.spec.tree_features), ()) as pool:
        ST.fill_pool(pool, vg, lambda r: tv[base[r]], lambda r: None, np.zeros((rows.size, 0), np.float32),
                     lambda s: None)
        ctx = FitContext(p.derived, p.split_sets, vg.grid, vg.labels, pool, lists, 0, CutKind.FIT)
        eager = ctx.donor_rows("bank")
        lazy = ctx.donor_rows_lazy("bank")
        log = ctx.log()
        assert log[-1] == log[-2]                                     # the same hand-out, logged the same
        assert lazy.row_key_hash == eager.row_key_hash and lazy.X.shape == eager.X.shape
        idx = np.arange(0, eager.X.shape[0], 7)
        assert lazy.X[idx].tobytes() == eager.X[idx].tobytes()
        with pytest.raises(FitContextRefusal, match="asked for whole"):
            np.asarray(lazy.X)
        a = fit_donor_bank(eager, p.trees_per_group)
        b = fit_donor_bank(lazy, p.trees_per_group)
        assert a.manifest == b.manifest and a.oob_share == b.oob_share
        assert a.manifest.bank_fingerprint == b.manifest.bank_fingerprint
