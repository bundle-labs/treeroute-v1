"""The export on the toy runs: T2 (no test label leaves the vault), T4 (one refusal per parity check), T5 (parity
passes, re-checked here independently of the export's own P-checks), and resume (SPEC_RIVALS.md 2.2-2.8, 4.2).

Needs builder A (rivals/export.py, rivals/layout.py). Until it exists every test here fails at the import.
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from rivals.tests import toy_runs as T


def _fitctx(run, purpose, lead):
    f = T.read_parquet(Path(run) / "fitctx_log.parquet")
    sel = f[(f["object_kind"] == "donor_rows") & (f["purpose"] == purpose) & (f["lead"] == float(lead))]
    assert len(sel), "fitctx_log has no %s rows at lead %s" % (purpose, lead)
    assert sel["row_key_hash"].nunique() == 1, sel
    return sel.iloc[0]


def _row_key_hash(units, times):
    from treeroute.labels.vault import row_key_hash
    return row_key_hash(np.asarray(units, dtype=object), np.asarray(times, dtype=np.int64))


def _keys(frame, cols=("unit", "time")):
    return list(zip(*[frame[c].tolist() for c in cols]))


# ------------------------------------------------------------------------------------------ T2
@pytest.mark.parametrize("which", ["grid_export", "table_export"])
def test_t2_no_test_label_in_any_export_file(which, request):
    """test/*.parquet has no y; every train row is dated at or before the lead's fit cut; tune and guard-fit rows at
    or before the guard cut; inner and guard rows after the guard cut (their score window)."""
    exp = request.getfixturevalue(which)
    toy = request.getfixturevalue("grid_toy" if which == "grid_export" else "table_toy")
    dirs = exp if isinstance(exp, dict) else exp.dirs
    for lead, d in sorted(dirs.items()):
        cuts = toy.cuts(lead)
        tests = sorted((d / "test").glob("*.parquet"))
        assert tests, "no test/*.parquet at lead %d" % lead
        for f in tests:
            cols = T.parquet_columns(f)
            assert "y" not in cols, "%s holds a y column" % f
            assert not [c for c in cols if c.startswith(("ngd__", "h__"))], (f, cols)
        tr = T.train_frames(d)
        for flag in T.ROLE_FLAGS:
            assert flag in tr.columns, "train files lack the role flag %s" % flag
        assert int(tr["time"].max()) <= cuts["fit_cut"], "a train row after the fit cut at lead %d" % lead
        refit = tr[tr["r_refit"]]
        assert len(refit) and int(refit["time"].max()) <= cuts["fit_cut"]
        guardside = tr[tr["r_tune"] | tr["r_guardfit"]]
        assert len(guardside), "no tune / guard-fit rows at lead %d" % lead
        assert int(guardside["time"].max()) <= cuts["guard_cut"], "a tune/guard-fit row after the guard cut"
        scored = tr[tr["r_inner"] | tr["r_guard"]]
        assert len(scored), "no inner / guard rows at lead %d" % lead
        assert int(scored["time"].min()) > cuts["guard_cut"], "an inner/guard row at or before the guard cut"
        # lead 0 has tune + inner, a forecast lead guard-fit + guard
        if lead == 0:
            assert not tr["r_guardfit"].any() and not tr["r_guard"].any()
        else:
            assert not tr["r_tune"].any() and not tr["r_inner"].any()
        assert (tr["issue"] == tr["time"] - tr["lead"]).all() and (tr["lead"] == lead).all()


# ------------------------------------------------------------------------------------------ T5
def _check_statuses(lead_dir, allow=("pass", "printed")):
    st = T.export_checks(lead_dir)
    for cid in T.CHECK_IDS_P:
        assert cid in st, "export_manifest.json lacks check %s" % cid
        assert st[cid].lower().startswith(allow), "%s: %s" % (cid, st[cid])
    return st


def _independent_parity(toy, lead, d):
    """Re-check P1-P7 and P9 from the run's own files, without the export's numbers."""
    man = T.read_json(toy.run / "manifest.json")
    plan = T.read_json(toy.run / "plan.json")
    tr = T.train_frames(d)
    # P7: columns
    x_cols = [c[3:] for c in tr.columns if c.startswith("x__")]
    c_cols = [c[3:] for c in tr.columns if c.startswith("c__")]
    assert x_cols == list(man["feature_list"]), (x_cols, man["feature_list"])
    assert c_cols == list(plan["context"]) == list(man["config"]["context_list"])
    for link in toy.links():
        assert "nfit__%s" % link in tr.columns
    # P1-P3: row-key hashes and counts against fitctx_log
    sets = [("r_refit", "bank")] + ([("r_tune", "bank_inner")] if lead == 0 else [("r_guardfit", "bank_guard")])
    for flag, purpose in sets:
        rows = tr[tr[flag]]
        ref = _fitctx(toy.run, purpose, lead)
        order = rows.sort_values(["unit", "time"], kind="stable")
        got = _row_key_hash(rows["unit"], rows["time"])
        got_sorted = _row_key_hash(order["unit"], order["time"])
        assert ref["row_key_hash"] in (got, got_sorted), "%s rows: row-key hash differs from fitctx_log" % flag
        assert int(ref["n_rows"]) == len(rows)
        assert int(ref["max_label_time"]) == int(rows["time"].max())
    # P4 / P5: score rows and their y against the saved inner / guard rows
    if lead == 0:
        saved = T.read_parquet(toy.run / "inner_preds.parquet", ["unit", "time", "y"])
        rows = tr[tr["r_inner"]]
    else:
        saved = T.read_parquet(toy.run / "ladder" / ("lead_%d" % lead) / "guard_preds.parquet", ["unit", "time", "y"])
        rows = tr[tr["r_guard"]]
    a = rows.set_index(["unit", "time"])["y"].sort_index()
    b = saved.set_index(["unit", "time"])["y"].sort_index()
    assert list(a.index) == list(b.index), "score rows differ from the saved %s rows" % ("inner" if lead == 0 else "guard")
    assert np.array_equal(a.to_numpy(), b.to_numpy(), equal_nan=True)
    # guardside: same rows, same order as the train subset
    gs = pd.concat([T.read_parquet(f) for f in sorted((d / "guardside").glob("*.parquet"))], ignore_index=True)
    sub = tr[tr["r_tune"] | tr["r_inner"] | tr["r_guardfit"] | tr["r_guard"]]
    assert _keys(gs) == _keys(sub), "guardside rows are not the train subset in the same order"
    for link in toy.links():
        assert "ngd__%s" % link in gs.columns
    hist = list(plan.get("history_columns", []))
    assert [c[3:] for c in gs.columns if c.startswith("h__")] == hist
    # P6: test keys
    tst = pd.concat([T.read_parquet(f) for f in sorted((d / "test").glob("*.parquet"))], ignore_index=True)
    keys = ["unit", "group", "time", "lead", "issue"]
    saved_t = T.read_parquet(toy.saved_test_preds(lead), keys + ["normal"])
    assert not tst.duplicated(keys).any()
    assert sorted(_keys(tst, keys)) == sorted(_keys(saved_t, keys))
    # P9: the identity fit-cut normal on test rows equals the saved normal (not for the neighbour kind: R-CN)
    if plan.get("router_kind") != "neighbour":
        j = tst.merge(saved_t, on=keys, how="inner", validate="one_to_one")
        assert len(j) == len(tst)
        assert np.array_equal(j["nfit__identity"].to_numpy(np.float64), j["normal"].to_numpy(np.float64),
                              equal_nan=True), "P9: the exported identity normal differs from the saved normal"
    # units.parquet
    units = T.read_parquet(d / "units.parquet")
    for c in ("unit", "group", "is_scored", "seen_during_design"):
        assert c in units.columns
    assert set(tst["unit"]) <= set(units.loc[units["is_scored"], "unit"])


def test_t5_parity_passes_on_the_grid_toy_every_lead(grid_toy, grid_export):
    for lead, d in sorted(grid_export.items()):
        _check_statuses(d)
        _independent_parity(grid_toy, lead, d)


def test_t5_parity_passes_on_the_table_toy_every_lead(table_toy, table_export):
    for lead, d in sorted(table_export.dirs.items()):
        _check_statuses(d)
        _independent_parity(table_toy, lead, d)


@pytest.mark.parametrize("variant", ["grid_toy_sparse", "grid_toy_decline", "table_toy_donor_only"])
def test_t5_parity_passes_on_the_other_toy_variants_lead_0(variant, request):
    toy = request.getfixturevalue(variant)
    (d,) = T.export_run(toy, [0], None)
    _check_statuses(d)
    _independent_parity(toy, 0, d)


def test_export_resume_skips_finished_files_and_is_byte_equal(table_toy, table_export):
    """A rerun with the same key skips every finished group file (no byte changes, no file moved aside), and the
    export's own determinism check P14 ran.

    Runs on its OWN export root (integration fix 2026-10-20): a resume rewrites export_manifest.json (new timings),
    and the session's shared table export is the one the harness boards of flows A and B were initialised on; a
    changed manifest there makes every later board command refuse ("the lead-0 export manifest changed since
    init"), which is the harness working as designed, not a defect."""
    cfg = _case_config(table_toy, "resume")
    (d0,) = T.export_run(table_toy, [0], None, config=cfg)
    before = {p: T.sha256_file(p) for p in sorted(d0.rglob("*.parquet"))}
    mtimes = {p: os.stat(p).st_mtime_ns for p in before}
    (d,) = T.export_run(table_toy, [0], None, config=cfg, resume=True)
    assert d == d0
    after = {p: T.sha256_file(p) for p in sorted(d0.rglob("*.parquet"))}
    assert after == before
    assert {p: os.stat(p).st_mtime_ns for p in before} == mtimes, "a finished file was rewritten on resume"
    assert T.export_checks(d0)["P14"].lower().startswith("pass")


# ------------------------------------------------------------------------------------------ T4
def _case_config(toy, case):
    """A config whose export root is the case's own (a refusal leaves nothing in the session export)."""
    root = toy.base / "t4" / case
    return T.write_rivals_yaml(root / "rivals.yaml", toy.machine_file, root / "_export", toy.export_ckpt_root,
                               root / "_out", root / "_moved")


def _assert_no_manifest(cfg):
    root = Path(cfg).parent / "_export"
    assert not list(root.rglob("export_manifest.json")), "a refused export wrote export_manifest.json"


def _edit_json(path, fn):
    doc = T.read_json(path)
    fn(doc)
    Path(path).write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")


def _write_parquet_like(frame, path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    schema = pq.read_schema(str(path))
    pq.write_table(pa.Table.from_pandas(frame, schema=schema, preserve_index=False), str(path))


def test_t4_package_fingerprint_changed_refuses_i2(grid_toy):
    cfg = _case_config(grid_toy, "pkg_fp")
    src = grid_toy.package.parent                                  # pk/ holds the package and its _stores
    dst = grid_toy.base / "t4" / "pkg_fp" / "pk"
    shutil.copytree(str(src), str(dst))
    pkg = dst / grid_toy.package.name
    cat = pkg / "catalog.yaml"
    text = cat.read_text(encoding="utf-8")
    assert "measurement_error_floor: 0.5" in text
    cat.write_text(text.replace("measurement_error_floor: 0.5", "measurement_error_floor: 0.6"), encoding="utf-8")
    T.expect_refusal("I2", T.export_run, grid_toy, [0], None, package=pkg, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_derived_json_differs_refuses_i7(grid_toy):
    cfg = _case_config(grid_toy, "derived")
    run = T.copy_run(grid_toy, "derived")
    _edit_json(run / "derived.json", lambda d: d["R22"]["flags"].append("edited_by_test"))
    T.expect_refusal("I7", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_data_file_mtime_changed_refuses_i5(grid_toy):
    cfg = _case_config(grid_toy, "mtime")
    target = sorted((grid_toy.package / "data" / "target").rglob("*.parquet"))[0]
    st = os.stat(target)
    try:
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        T.expect_refusal("I5", T.export_run, grid_toy, [0], None, config=cfg)
    finally:
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert os.stat(target).st_mtime_ns == st.st_mtime_ns
    _assert_no_manifest(cfg)


def test_t4_engine_modules_differ_without_a_lineage_hop_refuses_i4(grid_toy):
    cfg = _case_config(grid_toy, "engine")
    run = T.copy_run(grid_toy, "engine")

    def edit(m):
        name = sorted(m["engine_modules"])[0]
        m["engine_modules"][name] = "0" * 64
        m["engine_code_hash"] = "1" * 64
    _edit_json(run / "manifest.json", edit)
    T.expect_refusal("I4", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_library_versions_differ_refuses_i3(grid_toy):
    cfg = _case_config(grid_toy, "versions")
    run = T.copy_run(grid_toy, "versions")
    _edit_json(run / "manifest.json", lambda m: m["versions"].__setitem__("numpy", "0.0.0"))
    T.expect_refusal("I3", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_feature_list_differs_refuses_p7(grid_toy):
    cfg = _case_config(grid_toy, "features")
    run = T.copy_run(grid_toy, "features")

    def edit(m):
        fl = list(m["feature_list"])
        fl[0], fl[1] = fl[1], fl[0]
        m["feature_list"] = fl
    _edit_json(run / "manifest.json", edit)
    T.expect_refusal("P7", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_row_key_hash_differs_refuses_p1(grid_toy):
    cfg = _case_config(grid_toy, "rowkey")
    run = T.copy_run(grid_toy, "rowkey")
    path = run / "fitctx_log.parquet"
    f = T.read_parquet(path)
    sel = (f["object_kind"] == "donor_rows") & (f["purpose"] == "bank") & (f["lead"] == 0.0)
    assert sel.any()
    f.loc[sel, "row_key_hash"] = "0" * 64
    _write_parquet_like(f, path)
    T.expect_refusal("P1", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_test_keys_differ_refuses_p6(grid_toy):
    cfg = _case_config(grid_toy, "testkeys")
    run = T.copy_run(grid_toy, "testkeys")
    path = run / "test_preds.parquet"
    f = T.read_parquet(path)
    _write_parquet_like(f.iloc[1:].reset_index(drop=True), path)
    T.expect_refusal("P6", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_saved_normal_differs_refuses_p9(grid_toy):
    cfg = _case_config(grid_toy, "normal")
    run = T.copy_run(grid_toy, "normal")
    path = run / "test_preds.parquet"
    f = T.read_parquet(path)
    f.loc[0, "normal"] = f.loc[0, "normal"] + 1e-9
    _write_parquet_like(f, path)
    T.expect_refusal("P9", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_t4_a_missing_run_file_refuses_i1(grid_toy):
    cfg = _case_config(grid_toy, "missing")
    run = T.copy_run(grid_toy, "missing")
    T.move_aside(run / "inner_preds.parquet", grid_toy.base / "t4" / "missing" / "_moved")
    T.expect_refusal("I1", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_the_export_writes_nothing_into_the_run_or_the_package(grid_toy, grid_export):
    """The export machine's registry protects the toy's run root and package (toy_runs._finish); the export ran,
    so it wrote nothing there: every file under the run and the package has the size and mtime it had right after
    the toy run (snapshot taken in toy_runs._finish), and no file was added or removed."""
    assert T.snapshot(grid_toy) == grid_toy.extra["snapshot"]
