"""Toy fixtures of Builder B (coral + defo adapters). Toy data only; no real product, run or export is opened.

Run from D:\\treeroute\\human_rivals_build\\human:
    set PYTHONDONTWRITEBYTECODE=1
    py -3.9 -B -m pytest tests_builder_b -p no:cacheprovider --basetemp D:\\treeroute\\human_rivals_build\\pt\\B_coral_defo\\<fresh>
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.dont_write_bytecode = True
BUILD_ROOT = Path(__file__).resolve().parents[1]
if str(BUILD_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_ROOT))


class FakeRun(object):
    def __init__(self, cuts, plan=None, fingerprint="toyfingerprint", package="toy", name="toyrun"):
        self.cuts = cuts
        self.plan = plan or {}
        self.fingerprint = fingerprint
        self.package = package
        self.name = name
        self.leads = sorted(cuts)


class FakeCtx(object):
    """The AdapterCtx calls the B adapters use (BUILD_NOTES_shared.txt), backed by toy folders."""

    def __init__(self, tmp, run, rival_id, products, keys=None, extras=None, stage="all", token=None):
        self.run = run
        self.rival_id = rival_id
        self.products = {k: Path(v) for k, v in products.items()}
        self._keys = keys or {}
        self._extras = extras or {}
        self.stage = stage
        self._token = token
        self.root = Path(tmp) / "_work"
        self.lines = []
        self.opened = {}

    def keys(self, set_name="stage"):
        if set_name == "stage":
            set_name = {"all": "all", "train": "train", "test": "test"}[self.stage]
        if set_name in ("test", "all") and self.stage == "train":
            raise RuntimeError("stage train may not read test keys")
        return self._keys[set_name].copy()

    def extras(self, set_name):
        return self._extras[set_name].copy()

    def product_root(self, pid):
        return self.products[pid]

    def product_files(self, pid):
        root = self.products[pid]
        return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                      if p.is_file() and p.name != "product_manifest.json")

    def open_product(self, pid, name):
        p = self.products[pid] / name
        assert p.is_file(), p
        self.opened.setdefault(pid, set()).add(name)
        return p

    def work_dir(self):
        d = self.root / self.rival_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_bytes(self, path, data):
        p = Path(path)
        p.resolve().relative_to(self.work_dir().resolve())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def log(self, message):
        self.lines.append(str(message))


@pytest.fixture
def fake_ctx_class():
    return FakeCtx


@pytest.fixture
def fake_run_class():
    return FakeRun
