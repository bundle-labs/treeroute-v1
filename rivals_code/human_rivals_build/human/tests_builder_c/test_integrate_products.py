"""Integration test (INTEGRATE_REPORT.txt): a product the tool writes itself (a prep output) names its folder from the
config's index_root ({index_root}/...), so the build config and the production config each find the prep outputs
where `prep` writes them (ctx.work_dir = <index_root>/<pkg>/<run>/_work/<rival>). Config files only; nothing is read.
"""
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
HUMAN_ROOT = Path(__file__).resolve().parents[1]
if str(HUMAN_ROOT) not in sys.path:
    sys.path.insert(0, str(HUMAN_ROOT))

from rivals_human import config as C          # noqa: E402

BUILD = HUMAN_ROOT / "human_rivals.yaml"
PROD = HUMAN_ROOT / "human_rivals_production.DRAFT.yaml"


@pytest.mark.parametrize("cfg_file", [BUILD, PROD])
def test_staged_products_follow_the_config_index_root(cfg_file):
    cfg = C.load_config(str(cfg_file))
    products = C.load_products(cfg)
    root = str(cfg.data["index_root"]).replace("\\", "/").rstrip("/")
    for pid, rel in (("defo_vt0007_prep", "/defo/20261017_d71c61f4/_work/vt0007_shipped"),
                     ("ndvi_kraft_store", "/ndvi/20261016_d1de3158/_work/kraft_lstm/store")):
        assert products[pid]["path"] == root + rel, (pid, products[pid]["path"])
    for pid, rec in products.items():
        for f in ("path", "manifest"):
            assert "{" not in str(rec.get(f) or ""), (pid, f)


def test_dry_config_shares_slim_index_ledger_and_product_manifests_with_production():
    """The DRY pass config (O9): its own out_root, but the production slim and index roots (so the ledger under
    index_root is shared, review issue 7) and the production product manifests (product_manifest_root)."""
    prod = C.load_config(str(PROD))
    dry = C.load_config(str(HUMAN_ROOT / "human_rivals_DRY.DRAFT.yaml"))
    assert dry["out_root"] != prod["out_root"]
    for k in ("slim_root", "index_root", "registry_dir", "on_disk_products", "machine_file"):
        assert dry[k] == prod[k], k
    assert C.product_out_manifest(dry, "x") == C.product_out_manifest(prod, "x")
    data = dict(prod.data, product_manifest_root="relative/path")
    with pytest.raises(C.ConfigRefusal, match="absolute"):
        C.load_config(data)


def test_an_unknown_root_refuses(tmp_path):
    p = tmp_path / "_products.yaml"
    p.write_text("products:\n  x:\n    path: '{nowhere_root}/a'\n", encoding="utf-8")
    data = dict(C.load_config(str(BUILD)).data)
    data = {k: v for k, v in data.items() if not str(k).startswith("_")}
    data["on_disk_products"] = str(p)
    cfg = C.load_config(data)
    with pytest.raises(C.ConfigRefusal, match="unknown root"):
        C.load_products(cfg)
