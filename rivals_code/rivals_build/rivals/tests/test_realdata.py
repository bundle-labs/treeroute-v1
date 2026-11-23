"""Real-data tests (opt-in: RIVALS_REAL=1; read-only on every run, package and store; writes only under
D:/treeroute/rivals_build). SPEC_RIVALS.md 4.3 (smoke-size grid export parity) and 4.4 (coral tune-only dry pass).

Run them one at a time, as owner-approved commands, e.g. from D:/treeroute/rivals_build:
  set RIVALS_REAL=1 && py -3.9 -m pytest rivals/tests/test_realdata.py -k defo --basetemp D:/treeroute/rivals_build/pt/tests/real_<stamp>
No rival is fitted on smoke rows; the coral pass stops after the picks lock (no test row read, no test score).
"""

from pathlib import Path

import numpy as np
import pytest

from rivals.tests import toy_runs as T
from rivals.tests.test_export_parity import _independent_parity

pytestmark = pytest.mark.realdata

MACHINE_DIR = T.BUILD_ROOT / "_machine"
SMOKE_CFG = MACHINE_DIR / "rivals_smoke.yaml"
DRYRUN_CFG = MACHINE_DIR / "rivals_dryrun.yaml"
REAL_LOCK = Path("D:/treeroute/tmp/treeroute_heavy_job.lock")
GIB = 2 ** 30

DEFO_SMOKE = Path("D:/treeroute/coral_build_v6b/noop/new/defo/smoke/20261020_192b4285")
FIRE_SMOKE = Path("D:/treeroute/coral_build_v6b/noop/new/fire/smoke/20261020_ee5cd20a")
CORAL_RUN = Path("D:/treeroute/runs/coral/headline/20261020_f3b8e3da")


def _no_real_heavy_job():
    if REAL_LOCK.exists():
        pytest.skip("a real heavy job holds %s: one heavy job at a time" % REAL_LOCK)


def _real(run, package_name, cfg, out_root):
    run = Path(run)
    assert run.is_dir(), run
    machine = MACHINE_DIR / "machine.yaml"
    temp = Path(_machine_value(machine, "temp_dir"))
    export_root = Path(_machine_value(cfg, "export_root"))
    toy = T.Toy(name="real_" + package_name, kind="real", variant="real", base=T.BUILD_ROOT, package=
                T.ENGINE_ROOT / "datasets" / package_name, run=run, config=cfg, machine_file=machine, temp_dir=temp,
                export_root=export_root, export_ckpt_root=Path(_machine_value(cfg, "export_ckpt_root")),
                out_root=Path(out_root), moved_root=T.BUILD_ROOT / "_moved",
                leads=tuple(sorted(int(k) for k in T.read_json(run / "derived.json")["R11"]["value"])))
    return toy


def _machine_value(path, key):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.split("#", 1)[0].strip().startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise KeyError("%s has no %s" % (path, key))


def _assert_all_pass(lead_dir, skipped=()):
    st = T.export_checks(lead_dir)
    for cid in T.CHECK_IDS_P:
        assert cid in st, cid
        if cid in skipped:
            assert st[cid].lower().startswith("skipped"), (cid, st[cid])
        else:
            assert st[cid].lower().startswith(("pass", "printed")), (cid, st[cid])


# ------------------------------------------------------------------------------------------ 4.3
def test_smoke_export_parity_defo_region_kind():
    """Region kind, 4 groups x 40 units, leads 0 and 1, 3 links; inner 480 rows, test 640 rows per lead."""
    _no_real_heavy_job()
    toy = _real(DEFO_SMOKE, "defo", SMOKE_CFG, T.BUILD_ROOT / "_out")
    with T.ReadSpy() as spy:
        dirs = T.export_run(toy, toy.leads, None, resume=True)   # C-A2: a rerun resumes, never refuses
    assert spy.test_label_opens == [] and spy.test_y_requests() == []
    assert spy.test_file_reads(toy.export_root, decoded_only=True) == []
    assert len(dirs) == len(toy.leads)
    for lead, d in zip(toy.leads, dirs):
        _assert_all_pass(d)
        _independent_parity(toy, lead, d)
        tst = sum(len(T.read_parquet(f, ["unit"])) for f in (d / "test").glob("*.parquet"))
        assert tst == 640, (lead, tst)
        if lead == 0:
            tr = T.train_frames(d)
            assert int(tr["r_inner"].sum()) == 480


def test_smoke_export_parity_fire_per_unit_kind_with_context():
    """Per-unit kind with context, monthly leads 6/12; derive peak 2.6 GiB: only with more than 5 GiB available."""
    import psutil

    _no_real_heavy_job()
    if psutil.virtual_memory().available <= 5 * GIB:
        pytest.skip("available RAM %.1f GiB <= 5 GiB" % (psutil.virtual_memory().available / GIB))
    toy = _real(FIRE_SMOKE, "fire", SMOKE_CFG, T.BUILD_ROOT / "_out")
    with T.ReadSpy() as spy:
        dirs = T.export_run(toy, toy.leads, None, resume=True)   # C-A2: a rerun resumes, never refuses
    assert spy.test_label_opens == [] and spy.test_y_requests() == []
    for lead, d in zip(toy.leads, dirs):
        _assert_all_pass(d)
        _independent_parity(toy, lead, d)


# ------------------------------------------------------------------------------------------ 4.4
def test_coral_tune_only_dry_pass_stops_at_the_lock():
    """Export lead 0 with roles tune,inner (no test/ folder); init (hgb_l1) / tune / lock into _dryrun. The picks
    are LABELLED DRY; the board's coral tune must later reproduce them byte for byte."""
    import psutil

    _no_real_heavy_job()
    out_root = T.BUILD_ROOT / "_dryrun"
    toy = _real(CORAL_RUN, "coral", DRYRUN_CFG, out_root)
    out_dir = out_root / toy.package_name / toy.run_name
    if out_dir.exists():
        T.move_aside(out_dir, toy.moved_root)          # keep the earlier dry picks, moved aside
    with T.ReadSpy() as spy:
        (d,) = T.export_run(toy, [0], ["tune", "inner"], resume=True)   # C-A2
        assert not (d / "test").exists(), "the dry pass wrote a test/ folder"
        _assert_all_pass(d, skipped=("P6", "P9"))
        with T.counting_fit_predict() as box:
            out = T.h_init(toy, d, out_root, ("hgb_l1",))
            T.h_tune(toy, out)
        T.h_lock(toy, out)
    assert spy.test_label_opens == []
    assert spy.test_file_reads(toy.export_root, decoded_only=False) == []
    assert spy.test_y_requests() == []
    assert (out / "picks.json").is_file() and (out / "picks.json.lock.json").is_file()
    assert not (out / "scores").exists()
    assert not list(out.glob("test_labels_opened_rivals*"))
    counts = {p.name: len([q for q in p.iterdir() if (q / "trial.json").is_file()]) for p in (out / "trials").iterdir()}
    assert counts.get("ridge") == 3 and counts.get("rf") == 12, counts
    assert counts.get("lgbm", 0) >= 12 and counts.get("lgbm_tweedie", 0) >= 8 and counts.get("hgb_l1", 0) >= 12, counts
    peak = psutil.Process().memory_info().peak_wset / GIB
    print("coral dry pass: %d fits, trials %s, peak working set %.2f GiB" % (box["calls"], counts, peak))
    assert peak < 6.0
