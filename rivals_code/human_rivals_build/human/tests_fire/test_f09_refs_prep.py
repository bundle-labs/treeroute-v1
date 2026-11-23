"""T-F09 the refs label store (SPEC_HUMAN_PARTB.txt 1.4, 3.9; ATTENTION B4; Part 618 precedent).

Prep (adapters/fire_refs_prep.run_prep) on a synthetic toy: a lat/lon-keyed target store (float32 lat / lon, n_valid,
burned_frac), a toy package folder holding a COPY of the package's own reader (engine/datasets/fire/ingest/
target_reader.py, read-only source) with a toy dataset.yaml and static table. It writes cell_id-keyed labels of the bank
units (str / int64 / int64 / float64, NaN kept: n_valid 0 and a unit-month absent from the file; sorted by cell_id,
month) under work_dir()/refs_store; year 2019 refuses (never a test-year label); the prep never imports or opens the
slim or test_preds (read spy).

Then the tool's refs.store_labels on the written files (it cannot run on a FakeCtx: refs.py:251-264), through the
fixture the spec prefers: monkeypatched rivals_human.refs.C.load_products (-> the store's own tool-format manifest) and
rivals_human.refs.S.open_slim (-> a stub with units() and season). Held labels to 24227 -> only the time-24228 rows
(Dec 2018) of scored units with a finite label are added; a 1-ulp difference on an overlapping label refuses; a store
file missing from the manifest refuses.
"""

import ast
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from tests_fire import fixtures_fire as FF

GROUPS = ("g_north", "g_south")


def _toy_package(base: Path):
    """A toy fire package: dataset.yaml (stores.static), data/static/part-0.parquet, ingest/target_reader.py (copy)."""
    pkg = base / "pkg"
    (pkg / "ingest").mkdir(parents=True)
    (pkg / "data" / "static").mkdir(parents=True)
    shutil.copyfile(str(FF.TARGET_READER), str(pkg / "ingest" / "target_reader.py"))
    (pkg / "dataset.yaml").write_text("name: toy_fire\nstores:\n  static: data/static/part-0.parquet\n",
                                      encoding="utf-8")
    rows = []
    for gi, g in enumerate(GROUPS):
        for k in range(6):
            lat = 10.0 + 2.0 * gi + 0.25 * k                      # exact in float32 (the store's key dtype)
            lon = 20.0 + 0.125 * k
            rows.append(("%s_%d_%d" % (g, gi, k), g, lat, lon, k, gi))
    st = pd.DataFrame(rows, columns=["cell_id", "region", "lat", "lon", "grid_ix", "grid_iy"])
    st.to_parquet(str(pkg / "data" / "static" / "part-0.parquet"), index=False)
    return pkg, st


def _toy_target(base: Path, st: pd.DataFrame, year: int = 2018):
    """{group}_{year}.parquet keyed on float32 lat/lon (D:/fire/target layout): labels, n_valid 0 on some rows, one
    unit-month absent, one target cell that is not a unit (dropped by the reader)."""
    rng = np.random.default_rng(FF.RANDOM_STATE)
    folder = base / "target"
    folder.mkdir(parents=True)
    truth = {}
    for g in GROUPS:
        u = st[st["region"] == g]
        rows = []
        for cid, la, lo in zip(u["cell_id"], u["lat"], u["lon"]):
            for m in range(1, 13):
                if cid.endswith("_3") and m == 4:
                    truth[(cid, m)] = np.nan                       # absent from the file: NaN by the census
                    continue
                nv = 0 if (cid.endswith("_2") and m in (1, 2)) else 1000
                y = float(rng.choice([0.0, 0.0, 0.0, rng.uniform(0.0, 0.3)])) if nv else np.nan
                rows.append((np.float32(la), np.float32(lo), year, m, int(round((y if nv else 0) * nv)), nv, 0,
                             y if nv else np.nan, 0.0))
                truth[(cid, m)] = y if nv else np.nan
        rows.append((np.float32(55.5), np.float32(77.5), year, 1, 0, 10, 0, 0.0, 0.0))   # not a unit
        f = pd.DataFrame(rows, columns=["lat", "lon", "year", "month", "n_burned", "n_valid", "n_unmapped",
                                        "burned_frac", "unmapped_frac"])
        f = f.astype({"lat": np.float32, "lon": np.float32, "year": np.int64, "month": np.int64,
                      "n_burned": np.int32, "n_valid": np.int32, "n_unmapped": np.int32, "burned_frac": np.float64,
                      "unmapped_frac": np.float64})
        f.to_parquet(str(folder / ("%s_%d.parquet" % (g, year))), index=False)
    return folder, truth


def _prep_toy(tmp_path: Path, years=(2018,)):
    pkg, st = _toy_package(tmp_path)
    target, truth = _toy_target(tmp_path, st)
    units = []
    for g in GROUPS:
        ids = st.loc[st["region"] == g, "cell_id"].tolist()
        for k, cid in enumerate(ids[:5]):                          # the 6th unit of a group is not a bank unit
            units.append((cid, g, k != 4))                         # the 5th bank unit is not scored
    units = pd.DataFrame(units, columns=["unit", "group", "is_scored"]).assign(seen_during_design=False)
    static_dir = pkg / "data" / "static"
    FF.write_tool_manifest(static_dir, tmp_path / "_hout" / "_products" / FF.STATIC_PID / "product_manifest.json",
                           FF.STATIC_PID)
    FF.write_tool_manifest(target, tmp_path / "_hout" / "_products" / FF.TARGET_PID / "product_manifest.json",
                           FF.TARGET_PID)
    products = {FF.STATIC_PID: {"path": str(static_dir), "patterns": ["part-0.parquet"]},
                FF.TARGET_PID: {"path": str(target), "patterns": ["*_2018.parquet"]},
                FF.STORE_PID: {"path": str(tmp_path / "_unused_store"), "patterns": ["*"]}}
    opt = FF.era5_options()
    opt["refs_store"] = dict(opt["refs_store"], target_reader=str(pkg / "ingest" / "target_reader.py"),
                             years=list(years))
    rival = FF.era5_rival()
    rival["options"] = opt
    run = FF.FakeRun()
    ctx = FF.FakeCtx(tmp_path, run, rival, 0, stage="train", products=products, units=units)
    return SimpleNamespace(ctx=ctx, rival=rival, units=units, truth=truth, pkg=pkg, target=target, st=st)


def _store_files(ctx):
    d = ctx.work_dir() / "refs_store"
    return d, sorted(d.glob("*_labels_2018.parquet"))


def test_f09_prep_writes_cell_id_keyed_labels(refs_prep, tmp_path):
    toy = _prep_toy(tmp_path)
    res = refs_prep.run_prep(toy.ctx, toy.rival)
    assert isinstance(res, dict)
    d, files = _store_files(toy.ctx)
    assert [p.name for p in files] == ["%s_labels_2018.parquet" % g for g in sorted(GROUPS)]
    for g, p in zip(sorted(GROUPS), files):
        f = pd.read_parquet(str(p))
        assert list(f.columns) == ["cell_id", "year", "month", "burned_frac"]
        assert f["cell_id"].map(type).eq(str).all()
        assert f["year"].dtype == np.int64 and f["month"].dtype == np.int64 and f["burned_frac"].dtype == np.float64
        bank = sorted(toy.units.loc[toy.units["group"] == g, "unit"])
        assert sorted(set(f["cell_id"])) == bank                      # bank units only (scored or not)
        assert len(f) == len(bank) * 12 and (f["year"] == 2018).all()
        assert f[["cell_id", "month"]].equals(f[["cell_id", "month"]].sort_values(["cell_id", "month"])
                                                .reset_index(drop=True))
        for cid, m, y in zip(f["cell_id"], f["month"], f["burned_frac"]):
            want = toy.truth[(cid, int(m))]
            if np.isnan(want):
                assert np.isnan(y), (cid, m)                          # NaN kept (n_valid 0, absent month)
            else:
                assert y == want, (cid, m, y, want)
        assert f["burned_frac"].isna().sum() >= 1
    for p in files:
        p.resolve().relative_to(toy.ctx.work_dir().resolve())        # written under the rival's work folder only


def test_f09_a_test_year_refuses(refs_prep, tmp_path):
    toy = _prep_toy(tmp_path, years=(2019,))
    FF.refuses(refs_prep.run_prep, toy.ctx, toy.rival)
    d, files = _store_files(toy.ctx)
    assert not files


def test_f09_prep_never_touches_the_slim(refs_prep, tmp_path, monkeypatch):
    src = Path(refs_prep.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [a.name for a in node.names]
            assert not (mod == "rivals_human" and {"slim", "lockfile", "refs"} & set(names)), names
            assert mod not in ("rivals_human.slim", "rivals_human.lockfile", "rivals_human.refs"), mod
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name not in ("rivals_human.slim", "rivals_human.lockfile", "rivals_human.refs"), a.name
    toy = _prep_toy(tmp_path)
    decoys = FF.decoy_slim(tmp_path)
    from rivals_human import slim as S

    def boom(*a, **k):
        raise AssertionError("the prep touched the slim reader")
    monkeypatch.setattr(S, "open_slim", boom)
    monkeypatch.setattr(S.SlimLead, "read_set", boom)
    spy = FF.ReadSpy().install(monkeypatch)
    refs_prep.run_prep(toy.ctx, toy.rival)
    monkeypatch.undo()
    assert not spy.under(decoys), spy.under(decoys)
    assert not spy.named("test_preds", "slim_manifest")
    assert spy.under(toy.target), "the prep read the target store through the reader"


# ------------------------------------------------------------------------------------------ store_labels
STORE = {"product": FF.STORE_PID, "file_pattern": "{group}_labels_{year}.parquet", "unit_column": "cell_id",
         "year_column": "year", "month_column": "month", "label_column": "burned_frac", "dtype": "float64"}


def _store_toy(refs_prep, tmp_path, monkeypatch, drop_from_manifest=None):
    toy = _prep_toy(tmp_path)
    refs_prep.run_prep(toy.ctx, toy.rival)
    d, files = _store_files(toy.ctx)
    man = FF.write_tool_manifest(d, d / "product_manifest.json", FF.STORE_PID)
    if drop_from_manifest:
        doc = FF.read_json(man)
        doc["files"].pop(drop_from_manifest)
        FF.write_json(man, doc)
    from rivals_human import refs as R
    monkeypatch.setattr(R.C, "load_products", lambda cfg: {FF.STORE_PID: {"manifest": str(man)}})
    stub = SimpleNamespace(units=lambda: toy.units.copy(), season={"kind": "month_of_year", "steps_per_year": 12})
    monkeypatch.setattr(R.S, "open_slim", lambda cfg, run, lead: stub)
    run = SimpleNamespace(cuts={0: {"fit_cut": 24228}})
    held = []
    for (cid, m), y in sorted(toy.truth.items()):
        if m <= 11 and np.isfinite(y) and cid in set(toy.units["unit"]):
            held.append((cid, FF.step(2018, m), float(y)))
    held = pd.DataFrame(held, columns=["unit", "time", "y"])
    return R, run, held, toy


def test_f09_store_labels_adds_only_dec_2018(refs_prep, tmp_path, monkeypatch):
    R, run, held, toy = _store_toy(refs_prep, tmp_path, monkeypatch)
    assert int(held["time"].max()) == 24227
    add = R.store_labels(None, run, STORE, held)
    assert len(add) > 0
    assert (add["time"] == 24228).all()
    assert not add["unit"].duplicated().any()
    scored = set(toy.units.loc[toy.units["is_scored"], "unit"])
    want = {cid: y for (cid, m), y in toy.truth.items() if m == 12 and cid in scored and np.isfinite(y)}
    assert set(add["unit"]) == set(want)
    for u, y in zip(add["unit"], add["y"]):
        assert y == want[u]


def test_f09_store_labels_refuses_a_one_ulp_difference(refs_prep, tmp_path, monkeypatch):
    R, run, held, toy = _store_toy(refs_prep, tmp_path, monkeypatch)
    k = int(np.flatnonzero(held["y"].to_numpy() > 0)[0])
    held.loc[k, "y"] = np.nextafter(held.loc[k, "y"], 1.0)
    FF.refuses(R.store_labels, None, run, STORE, held, kinds=FF.tool_refusals(), words=("differs",))


def test_f09_store_labels_refuses_a_file_missing_from_the_manifest(refs_prep, tmp_path, monkeypatch):
    R, run, held, toy = _store_toy(refs_prep, tmp_path, monkeypatch,
                                   drop_from_manifest="%s_labels_2018.parquet" % GROUPS[1])
    FF.refuses(R.store_labels, None, run, STORE, held, kinds=FF.tool_refusals(), words=("lists no",))
