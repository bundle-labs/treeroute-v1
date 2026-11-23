"""T-H04 no test-window label before the lock (SPEC_HUMAN.txt A2, 1.3, 1.4, 1.11).

A read spy (the common tests' ReadSpy, rivals/tests/toy_runs.py:301) watches init, tune and lock of the grid flow:
no slim test file, no export test file and no test-stage index table is opened, and no saved test_preds is asked
for y. Before the lock, refit / score / refs refuse and so does a stage-test adapt. An adapter context gives labels
of fit sets only, and test features only with the lock.
"""

import os
from pathlib import Path

import pytest

from rivals_human.tests import hooks as HK


def _under(path: str, root: Path) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    r = os.path.normcase(os.path.abspath(str(root)))
    return p.startswith(r + os.sep)


def test_h04_init_tune_lock_open_no_test_file(grid_flow):
    spy = grid_flow.spy
    h = grid_flow.h
    for root in (h.roots["slim_root"], h.roots["export_root"]):
        hits = spy.test_file_reads(Path(root), decoded_only=False)
        assert hits == [], "init / tune / lock read test files under %s: %s" % (root, hits[:5])
    stage_test = [c for c in spy.calls if not c[1].startswith("<") and _under(c[1], h.roots["index_root"])
                  and c[1].endswith("__test.parquet")]
    assert stage_test == [], stage_test[:5]
    assert spy.test_y_requests() == [], spy.test_y_requests()[:5]
    assert spy.test_label_opens == []


def test_h04_pre_lock_commands_refuse(grid_flow):
    for step, res in sorted(grid_flow.pre_lock.items()):
        assert res.startswith("refused:"), "%s before the lock: %s" % (step, res)
        assert "INTERFACE" not in res
    assert any(k.startswith("adapt_test_") for k in grid_flow.pre_lock) or not any(
        HK.staged(r) for r in HK.index_rivals(grid_flow.h)), "no staged rival was tried before the lock"


def test_h04_fit_labels_only_for_fit_sets(grid_human, grid_slim):
    ctx = HK.adapter_ctx(grid_human, "toy_m", 0, "train")
    keys, y, normals = ctx.fit_labels("tune")
    assert len(keys) == len(y) and "identity" in normals
    for s in ("inner", "guard", "test"):
        HK.refuses(("fit set", "only the fit sets", "labels"), ctx.fit_labels, s)


def test_h04_test_features_need_the_lock(grid_human, grid_slim):
    ctx = HK.adapter_ctx(grid_human, "toy_m", 0, "all")
    HK.refuses(("lock", "token"), ctx.features, "test")
    ctx_train = HK.adapter_ctx(grid_human, "toy_idx", 0, "train")
    HK.refuses(("may not read test", "stage train"), ctx_train.keys, "test")


def test_h04_stage_test_adapt_refuses_without_a_lock(grid_human, grid_slim):
    """A staged toy rival on a variant registry: stage train adapts; stage test refuses while no human lock exists."""
    from rivals_human.tests import toy_products as TP
    reg = TP.grid_registry(grid_human.package)
    staged = dict(next(r for r in reg["rivals"] if r["id"] == "toy_idx"))
    staged["id"] = "toy_idx_staged"
    staged["reads_target_in_test_window"] = True
    staged["coverage"] = "all_rows"
    reg = dict(reg, rivals=[staged])
    v = HK.variant_config(grid_human, "staged", reg, index_name="_index_staged")
    HK.adapt(v, "toy_idx_staged", 0, "train")
    HK.refuses(("lock", "not locked"), HK.adapt, v, "toy_idx_staged", 0, "test")
