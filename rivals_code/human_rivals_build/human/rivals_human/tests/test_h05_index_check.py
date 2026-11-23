"""T-H05 index check (SPEC_HUMAN.txt 1.4): a missing key, a duplicate key, an infinite value, a src whose sha256 is
not the product manifest's, and a src never opened through ctx.open_product each refuse; an index table edited
after it was written refuses at `check`."""

import numpy as np
import pandas as pd
import pytest

from rivals_human.tests import hooks as HK


@pytest.fixture(scope="module")
def idx_case(grid_human, grid_slim):
    """toy_idx at lead 0, adapted once (its own index root), with everything check_frame needs."""
    v = HK.variant_config(grid_human, "h05", index_name="_index_h05")
    HK.adapt(v, "toy_idx", 0)
    I = HK.tool("index")
    cfg = HK.load_config(v)
    run = v.h_run()
    rival = v.rival("toy_idx")
    files = I.index_files(cfg, run, "toy_idx", 0)
    frame = HK.read_parquet(files["all"])
    man = HK.read_json(files["manifest"])
    opened = man["stages"]["all"]["opened"]
    products = HK.need(HK.tool("config"), "load_products", "A1")(cfg)
    manifests = {pid: I.product_manifest(cfg, products, pid) for pid in opened}
    sl = HK.slim_lead(v, grid_slim[0])
    keys = sl.keys("all")
    tm = HK.timing(run, rival, 0)
    return {"v": v, "frame": frame, "keys": keys, "rival": rival, "tm": tm, "legal": run.legal,
            "opened": opened, "manifests": manifests, "file": files["all"]}


def _check(case, frame, opened=None, manifests=None):
    return HK.check_frame(frame, case["keys"], case["rival"], case["tm"], "P", case["legal"],
                          opened if opened is not None else case["opened"],
                          manifests if manifests is not None else case["manifests"])


def test_h05_the_written_table_passes(idx_case):
    rec = _check(idx_case, idx_case["frame"])
    assert rec["rows"] == len(idx_case["keys"])
    HK.check(idx_case["v"], "toy_idx")


def test_h05_a_missing_key_refuses(idx_case):
    f = idx_case["frame"].iloc[1:].reset_index(drop=True)
    HK.refuses(("no index row", "missing"), _check, idx_case, f)


def test_h05_an_extra_key_refuses(idx_case):
    f = idx_case["frame"].copy()
    extra = f.iloc[[0]].copy()
    extra["time"] = extra["time"] + 100000
    extra["issue"] = extra["issue"] + 100000
    f = pd.concat([f, extra], ignore_index=True)
    HK.refuses(("name no slim key", "extra", "index rows name"), _check, idx_case, f)


def test_h05_a_duplicate_key_refuses(idx_case):
    f = pd.concat([idx_case["frame"], idx_case["frame"].iloc[[3]]], ignore_index=True)
    HK.refuses(("twice", "duplicate"), _check, idx_case, f)


def test_h05_an_infinite_value_refuses(idx_case):
    f = idx_case["frame"].copy()
    col = idx_case["rival"]["stats"][0]
    i = int(np.flatnonzero(np.isfinite(f[col].to_numpy()))[0])
    f.loc[i, col] = np.inf
    HK.refuses(("infinite", "inf"), _check, idx_case, f)


def test_h05_a_src_with_another_sha_refuses(idx_case):
    opened = {pid: {name: "0" * 64 for name in files} for pid, files in idx_case["opened"].items()}
    HK.refuses(("sha", "manifest"), _check, idx_case, idx_case["frame"], opened=opened)


def test_h05_a_src_never_opened_refuses(idx_case):
    f = idx_case["frame"].copy()
    f["src"] = "some_other_file.nc"
    HK.refuses(("never opened", "src"), _check, idx_case, f)


def test_h05_an_index_table_edited_after_it_was_written_refuses_at_check(idx_case):
    v = idx_case["v"]
    p = idx_case["file"]
    f = HK.read_parquet(p)
    f = f.iloc[:-1].reset_index(drop=True)                 # drop a row and write the table back (an edit)
    HK.move_aside(p, v.base / "_moved_by_tests")
    HK.write_parquet(p, f)
    HK.refuses(("changed", "sha"), HK.check, v, "toy_idx")
