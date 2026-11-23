"""T-F17 no label in the index path (SPEC_HUMAN_PARTB.txt 2.2, 3.6, 3.9; PROT H2): a read spy (builtins / io open,
pyarrow, pandas, xarray) shows

- fire_geff.build never opens fire_target_2018, fire_refs_label_store (both listed by geff_era5 and present in the
  toy, with files), a slim train / test parquet or a test_preds file, and opens only its own product and the unit
  centres through ctx.open_product;
- fire_refs_prep.run_prep never opens a slim parquet or test_preds (test_f09 runs it under the spy); and no fire
  adapter imports rivals_human.slim / lockfile / refs (the slim reader, the lock and the label-holding refs code);
- a runner's predict never calls fit_labels (the stand-in ctx counts the calls).
"""

import ast

import numpy as np
import pytest

from tests_fire import fixtures_fire as FF

FORBIDDEN_MODULES = ("rivals_human.slim", "rivals_human.lockfile", "rivals_human.refs")


@pytest.mark.parametrize("kind", ["era5", "seas5"])
def test_f17_build_opens_no_label_file(geff, raw_subsets, tmp_path, monkeypatch, kind):
    toy = FF.era5_toy(tmp_path, raw_subsets) if kind == "era5" else FF.seas5_toy(tmp_path, raw_subsets)
    decoys = FF.decoy_slim(tmp_path)
    if kind == "seas5":                                   # the label products exist in this toy too
        toy.products[FF.TARGET_PID] = FF.decoy_product(tmp_path, FF.TARGET_PID, ["great_plains_2018.parquet"])
        toy.products[FF.STORE_PID] = FF.decoy_product(tmp_path, FF.STORE_PID, ["great_plains_labels_2018.parquet"])
    ctx = toy.ctx()
    spy = FF.ReadSpy().install(monkeypatch)
    frame = geff.build(ctx, toy.rival, toy.lead, "all")
    monkeypatch.undo()
    assert len(frame) == len(ctx.keys("all"))
    pid = FF.ERA5_PID if kind == "era5" else FF.SEAS5_PID
    assert set(ctx.opened) <= {pid, FF.STATIC_PID}, sorted(ctx.opened)
    for p in (FF.TARGET_PID, FF.STORE_PID):
        assert not spy.under(toy.products[p]["path"]), (p, spy.under(toy.products[p]["path"]))
    assert not spy.under(decoys)
    assert not spy.named("test_preds", "slim_manifest", "test_labels_opened")
    assert spy.paths, "the spy saw no read at all (it is not installed where the adapter reads)"


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            out += [mod] + ["%s.%s" % (mod, a.name) for a in node.names]
    return out


def test_f17_no_fire_adapter_imports_the_slim_lock_or_refs():
    files = sorted((FF.HUMAN_ROOT / "adapters").glob("fire_*.py"))
    assert len(files) >= 4
    for p in files:
        bad = [m for m in _imports(p) if m in FORBIDDEN_MODULES]
        assert not bad, (p.name, bad)


@pytest.mark.parametrize("which", ["enso", "turco"])
def test_f17_runner_predict_never_asks_for_labels(tmp_path, runners, which):
    runner = runners[0] if which == "enso" else runners[1]
    f = FF.runner_frame(6)
    y = f["N"].to_numpy() * 1.1
    if which == "enso":
        rival, extras = FF.enso_rival(), ["x__oni"]
    else:
        rival, extras = FF.turco_rival(), FF.SPI_COLS
    ctx = FF.runner_ctx(tmp_path, rival, 6, FF.runner_sets(f, y, extras))
    for fit_set, score_set in (("guardfit", "guard"), ("refit", "test")):
        params = FF.fit_in_scope(runner, ctx, rival, 6, fit_set)
        before = list(ctx.label_calls)
        assert before[-1] == fit_set
        out = runner.predict(ctx, dict(rival), 6, params, score_set)
        assert ctx.label_calls == before
        assert np.isfinite(out["pre"].to_numpy(np.float64)).all()
    assert ctx.label_calls == ["guardfit", "refit"]
