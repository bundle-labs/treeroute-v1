"""Mutation tests of the export's parity checks that had no test (parity review 7): each case edits ONE fact in a
copy of the grid toy run and the export must refuse naming the check, writing no manifest.

  I6  the run manifest's fingerprint            P2  the inner bank hand-out (fitctx_log bank_inner)
  P3  a lead's guard bank hand-out              P4  one inner_preds label
  P5  one lead guard_preds label                P8  one group in tables.json builds
  P9  a saved trees-off on the test rows (the new every-link check)
  P10 a saved trees-off on the inner rows beyond the run's tolerance
"""

import numpy as np

from rivals.tests import toy_runs as T
from rivals.tests.test_export_parity import _assert_no_manifest, _case_config, _edit_json, _write_parquet_like


def _lead_l(toy):
    return max(int(x) for x in toy.leads)


def test_m_run_fingerprint_flipped_refuses_i6(grid_toy):
    cfg = _case_config(grid_toy, "m_i6")
    run = T.copy_run(grid_toy, "m_i6")
    _edit_json(run / "manifest.json", lambda m: m.__setitem__("fingerprint", "0" * 64))
    T.expect_refusal("I6", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def _edit_fitctx(run, purpose, lead):
    path = run / "fitctx_log.parquet"
    f = T.read_parquet(path)
    sel = (f["object_kind"] == "donor_rows") & (f["purpose"] == purpose) & (f["lead"].astype(float) == float(lead))
    assert sel.any(), (purpose, lead)
    f.loc[sel, "row_key_hash"] = "0" * 64
    _write_parquet_like(f, path)


def test_m_inner_bank_handout_edited_refuses_p2(grid_toy):
    cfg = _case_config(grid_toy, "m_p2")
    run = T.copy_run(grid_toy, "m_p2")
    _edit_fitctx(run, "bank_inner", 0)
    T.expect_refusal("P2", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_m_guard_bank_handout_edited_refuses_p3(grid_toy):
    L = _lead_l(grid_toy)
    cfg = _case_config(grid_toy, "m_p3")
    run = T.copy_run(grid_toy, "m_p3")
    _edit_fitctx(run, "bank_guard", L)
    T.expect_refusal("P3", T.export_run, grid_toy, [L], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_m_one_inner_label_edited_refuses_p4(grid_toy):
    cfg = _case_config(grid_toy, "m_p4")
    run = T.copy_run(grid_toy, "m_p4")
    path = run / "inner_preds.parquet"
    f = T.read_parquet(path)
    f.loc[0, "y"] = float(f.loc[0, "y"]) + 1e-9
    _write_parquet_like(f, path)
    T.expect_refusal("P4", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_m_one_guard_label_edited_refuses_p5(grid_toy):
    L = _lead_l(grid_toy)
    cfg = _case_config(grid_toy, "m_p5")
    run = T.copy_run(grid_toy, "m_p5")
    path = run / "ladder" / ("lead_%d" % L) / "guard_preds.parquet"
    f = T.read_parquet(path)
    f.loc[0, "y"] = float(f.loc[0, "y"]) + 1e-9
    _write_parquet_like(f, path)
    T.expect_refusal("P5", T.export_run, grid_toy, [L], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_m_one_tables_build_group_edited_refuses_p8(grid_toy):
    cfg = _case_config(grid_toy, "m_p8")
    run = T.copy_run(grid_toy, "m_p8")
    _edit_json(run / "tables.json", lambda t: t["fit_cut_store"]["builds"][0].__setitem__("group", "zz_not_a_group"))
    T.expect_refusal("P8", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def _shift_trees_off(path, link="identity", by=1e-3):
    f = T.read_parquet(path)
    col = "pre__%s_trees_off_unweighted" % link
    assert col in f.columns, (path, [c for c in f.columns if "trees_off" in c])
    f.loc[0, col] = float(f.loc[0, col]) + by
    _write_parquet_like(f, path)


def test_m_inner_trees_off_shifted_beyond_tolerance_refuses_p10(grid_toy):
    cfg = _case_config(grid_toy, "m_p10")
    run = T.copy_run(grid_toy, "m_p10")
    _shift_trees_off(run / "inner_preds.parquet")
    T.expect_refusal("P10", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    _assert_no_manifest(cfg)


def test_m_test_trees_off_shifted_refuses_p9_on_every_link(grid_toy):
    links = [l for l in grid_toy.links() if l != "identity"] or ["identity"]
    cfg = _case_config(grid_toy, "m_p9")
    run = T.copy_run(grid_toy, "m_p9")
    _shift_trees_off(run / "test_preds.parquet", link=links[0], by=1e-2)
    text = T.expect_refusal("P9", T.export_run, grid_toy, [0], None, run=run, config=cfg)
    assert links[0] in text, text[-600:]
    _assert_no_manifest(cfg)
