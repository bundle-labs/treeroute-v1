"""R07 (ISSUE 7): "nothing is re-picked after a test number is seen" holds only inside ONE out_root.

The human ledger lives at <out_root>/_ledger/<run fingerprint>.jsonl (lockfile.py:57-58). A second config with
another out_root (the planned DRY coral pass O9, a re-run, a typo) has its own empty ledger, so it can tune and lock
NEW picks for a run whose test labels were already opened, and refit / score them. The index tables (index_root) and
slim copies are shared, so nothing else notices.

Here: the grid toy's full flow (scored at every lead under the main config) is board A; board B is a variant config
(own out_root, same slim and index roots) whose registry drops one rival, so its picks content differs.
"""
import pytest

from rivals_human import lockfile as LK
from rivals_human.tests import hooks as HK

pytestmark = pytest.mark.flow


def test_r07_board_a_opened_test_labels(grid_flow):
    grid_flow.ok("score 0")
    run = grid_flow.h.h_run()
    events = [r for r in LK.ledger_read(grid_flow.out, run.fingerprint) if r.get("event") == "test_labels_opened"]
    assert events, "the main flow's ledger shows no test_labels_opened"


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="ISSUE 7: a board under another out_root locks new picks for a run whose test labels were "
                          "opened (the ledger is per out_root)")
def test_r07_other_out_root_cannot_relock_after_test_labels_opened(grid_flow):
    grid_flow.ok("score 0")
    h = grid_flow.h
    reg = dict(h.registry, rivals=[r for r in h.registry["rivals"] if r["id"] != "toy_noise"])
    v = HK.variant_config(h, "rv_ledger", reg)
    refused = None
    try:
        HK.run_tune_lock(v)
    except Exception as exc:                                         # noqa: BLE001
        refused = str(exc)
    if refused is not None and "ledger" not in refused.lower():
        raise RuntimeError("board B refused for another reason (fix the test setup): %s" % refused)
    assert refused is not None, \
        "board B (out_root %s) tuned and locked new picks after board A opened test labels" % v.roots["out_root"]
