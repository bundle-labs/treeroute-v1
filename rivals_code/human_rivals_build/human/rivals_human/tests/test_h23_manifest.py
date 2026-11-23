"""Product manifests (SPEC_HUMAN.txt 1.8; manifest.py): `manifest --product <id>` hashes every file of a product
that was on disk before the plan into <out_root>/_products/<id>/product_manifest.json, never into the product
folder; a second run with the same files writes nothing; a changed product refuses; a download keeps its own
manifest (only --verify re-checks it). Not a numbered T-H test: the spec's 1.8 rule, tested on a toy folder."""

import pytest

from rivals_human.tests import hooks as HK
from rivals_human.tests import toy_products as TP


def test_manifest_hashes_a_product_into_the_out_root_never_into_its_folder(grid_human, tmp_path):
    folder = tmp_path / "plain_product"
    folder.mkdir()
    (folder / "a.nc").write_bytes(b"alpha")
    (folder / "b.nc").write_bytes(b"beta")
    (folder / "notes.txt").write_bytes(b"not hashed: outside the pattern")
    v = HK.variant_config(grid_human, "manifest")
    prods = HK.read_yaml(v.roots["on_disk_products"])
    prods["products"]["toy_plain"] = {"path": str(folder), "patterns": ["*.nc"], "licence": "toy",
                                      "source": "test folder"}
    TP.write_yaml(v.roots["on_disk_products"], prods)
    before = HK.snapshot(folder)
    mp = HK.manifest(v, "toy_plain")
    assert mp == v.roots["out_root"] / "_products" / "toy_plain" / "product_manifest.json"
    assert HK.snapshot(folder) == before
    m = HK.read_json(mp)
    assert sorted(m["files"]) == ["a.nc", "b.nc"] and m["complete"] is True
    for name, e in m["files"].items():
        assert e["sha256"] == HK.sha256_file(folder / name)
    sha = HK.sha256_file(mp)
    assert HK.manifest(v, "toy_plain") == mp and HK.sha256_file(mp) == sha        # same files: nothing written
    (folder / "b.nc").write_bytes(b"BETA changed")
    HK.refuses(("changed", "other files"), HK.manifest, v, "toy_plain")


def test_a_download_keeps_its_own_manifest(grid_human):
    HK.refuses(("download", "own manifest"), HK.manifest, grid_human, "toy_grid")
