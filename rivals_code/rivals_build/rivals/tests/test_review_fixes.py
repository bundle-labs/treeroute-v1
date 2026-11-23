"""Tests of the review fixes (rivals review: leak-fairness, parity, robustness). Toy runs only; every write under the
test's basetemp. No real test label is read.

  F1  export files are checked against the manifest (edited file, stray file), and the cut rules are re-checked
      on every row read (a tune row after the guard cut).
  F2  the board is bound to its export's CONTENT (a rebuilt manifest with new timings passes), to one engine,
      to the lead-0 export identity at every lead, and to the run files.
  F3  the lock: a label record under other picks, the run's ledger, tune / lock after test traces, a killed lock.
  F4  robustness: unlock of a stale lock (and never a live one), the CLI's one-line refusals and --config,
      private memory not counting memmap pages, RF with a row fraction below 1, the fit-set copy's disk check
      and its killed temp file, one RF method per board (Z2: out of core, no stride), the kept export files, ours tied to the run.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from rivals.tests import toy_runs as T


def H():
    return T.rivals_harness()


def _copy(src: Path, dst: Path) -> Path:
    shutil.copytree(str(src), str(dst))
    return dst


def _write_parquet(path: Path, frame: pd.DataFrame):
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), str(path), compression="snappy")


def _resign(lead_dir: Path):
    """Re-sign the manifest's file sha256 values after a deliberate edit (a forger's step)."""
    mp = lead_dir / "export_manifest.json"
    m = T.read_json(mp)
    for f in m["files"]:
        f["sha256"] = T.sha256_file(lead_dir / f["path"])
    mp.write_text(json.dumps(m, indent=1, sort_keys=True), encoding="utf-8")


def _first_with(lead_dir: Path, flag: str):
    for f in sorted((lead_dir / "train").glob("*.parquet")):
        t = pq.read_table(f).to_pandas()
        if t[flag].any():
            return f, t
    raise AssertionError("no group file with %s" % flag)


# ================================================================================================== F1
def test_f1_an_edited_export_file_is_refused(table_toy, table_export):
    d = _copy(table_export.dirs[0], table_toy.base / "fix_copies" / "edited" / "lead_0")
    f, t = _first_with(d, "r_tune")
    i = int(np.flatnonzero(t["r_tune"].to_numpy(bool))[0])
    t.loc[i, "y"] = float(t.loc[i, "y"]) + 1.0
    _write_parquet(f, t)
    ex = H().ExportLead(d, 0, H().Run(table_toy.run))
    with pytest.raises(H().HarnessRefusal, match="sha256"):
        ex.read_set("tune")


def test_f1_a_stray_export_file_is_refused(table_toy, table_export):
    d = _copy(table_export.dirs[0], table_toy.base / "fix_copies" / "stray" / "lead_0")
    f = sorted((d / "train").glob("*.parquet"))[0]
    shutil.copyfile(str(f), str(d / "train" / "zz_stray.parquet"))
    with pytest.raises(H().HarnessRefusal, match="not listed"):
        H().ExportLead(d, 0, H().Run(table_toy.run))


def test_f1_a_tune_row_after_the_guard_cut_is_refused_even_when_signed(table_toy, table_export):
    d = _copy(table_export.dirs[0], table_toy.base / "fix_copies" / "cut" / "lead_0")
    f, t = _first_with(d, "r_inner")
    i = int(np.flatnonzero(t["r_inner"].to_numpy(bool))[0])
    t.loc[i, "r_tune"] = True                 # the guardside union is unchanged (tune | inner)
    _write_parquet(f, t)
    _resign(d)                                # the file hashes now pass: the cut rule must still refuse
    ex = H().ExportLead(d, 0, H().Run(table_toy.run))
    with pytest.raises(H().HarnessRefusal, match="cut rule"):
        ex.read_set("tune")


# ================================================================================================== F2
def test_f2_content_hash_ignores_timings_and_sees_a_changed_file(table_export):
    m = T.read_json(table_export.dirs[0] / "export_manifest.json")
    a = H().export_content_sha(m)
    m2 = json.loads(json.dumps(m))
    m2["timings_seconds"] = {"total": 1.0}
    m2["written_utc"] = "1999-01-01T00:00:00+00:00"
    m2["peak_rss_bytes"] = 1
    m2["files_written"], m2["files_skipped_resume"] = 0, 99
    assert H().export_content_sha(m2) == a
    m2["files"][0]["sha256"] = "0" * 64
    assert H().export_content_sha(m2) != a


def test_f2_a_lead_export_of_another_identity_or_c_is_refused(table_toy, table_flow):
    board = T.read_json(table_flow.out / "board.json")
    run = H().Run(table_toy.run)
    L = max(table_toy.leads)
    H().export_lead(board, run, L)                                  # as built: passes
    bad = json.loads(json.dumps(board))
    bad["export"]["identity"]["export_code_sha256"] = "0" * 64
    with pytest.raises(H().HarnessRefusal, match="differs from the board"):
        H().export_lead(bad, run, L)
    bad = json.loads(json.dumps(board))
    bad["run"]["c"][str(L)] = 12345.0
    with pytest.raises(H().HarnessRefusal, match="R23"):
        H().export_lead(bad, run, L)


def test_f2_a_changed_engine_refuses_every_later_command(table_toy, table_flow, monkeypatch):
    monkeypatch.setattr(H(), "engine_file_sha", lambda: "f" * 64)
    with pytest.raises(H().HarnessRefusal, match="LIVE engine changed"):
        H().board(table_flow.out, config=table_toy.config)


def test_f2_the_board_keeps_each_leads_manifest_and_units(table_toy, table_flow):
    for L in table_toy.leads:
        d = table_flow.out / "exports" / ("lead_%d" % L)
        assert (d / "export_manifest.json").is_file() and (d / "units.parquet").is_file(), d
        u = H().kept_units(table_flow.out, L)
        assert len(u) > 0


# ================================================================================================== F3
def _fake_board_dir(base: Path, fp: str) -> Path:
    out = base / "pkg" / "run"
    out.mkdir(parents=True)
    picks = {"lgbm": {"trial_id": "t", "extended": False, "link": "identity", "setting": {}, "checkpoint": "200"}}
    doc = json.dumps({"run_fingerprint": fp, "picks": picks}).encode()
    (out / "picks.json").write_bytes(doc)
    (out / "picks.json.lock.json").write_text(json.dumps({"sha256": H().sha256_bytes(doc)}))
    return out


def test_f3_a_label_record_under_other_picks_refuses(table_toy):
    out = _fake_board_dir(table_toy.base / "fix_lock_a", "fp_a")
    H().verify_lock(out)
    (out / "test_labels_opened_rivals_lead_0.json").write_text(json.dumps(
        {"picks_sha256": "1" * 64, "history": [{"picks_sha256": "1" * 64}]}))
    with pytest.raises(H().HarnessRefusal, match="re-locked"):
        H().verify_lock(out)


def test_f3_the_run_ledger_refuses_other_picks_and_accepts_the_same_picks(table_toy):
    out = _fake_board_dir(table_toy.base / "fix_lock_b", "fp_b")
    led = out.parent.parent / "_ledger"
    led.mkdir()
    doc = T.read_json(out / "picks.json")
    same = H().picks_content_sha(doc["picks"])
    (led / "fp_b.jsonl").write_text(json.dumps({"event": "test_labels_opened", "picks_content_sha256": same}) + "\n")
    H().verify_lock(out)                                            # the same picks: passes
    with open(led / "fp_b.jsonl", "a") as fh:
        fh.write(json.dumps({"event": "test_labels_opened", "picks_content_sha256": "2" * 64}) + "\n")
    with pytest.raises(H().HarnessRefusal, match="ledger"):
        H().verify_lock(out)


def _board_copy(toy, flow, name):
    dst = toy.base / name / toy.package_name / toy.run_name
    shutil.copytree(str(flow.out), str(dst))
    return dst


def test_f3_tune_and_lock_refuse_once_a_test_trace_exists(table_toy, table_flow):
    out = _board_copy(table_toy, table_flow, "_out_fix_trace")
    for p in (out / "picks.json", out / "picks.json.lock.json"):
        T.move_aside(p, table_toy.moved_root)                         # the 'lock moved aside' state
    with pytest.raises(H().HarnessRefusal, match="test-side files"):
        H().tune(out, resume=True, config=table_toy.config)
    with pytest.raises(H().HarnessRefusal, match="test-side files"):
        H().lock(out, config=table_toy.config)


def test_f3_lock_after_a_kill_redoes_and_the_ledger_guards_relocks(table_toy, table_flow):
    out = _board_copy(table_toy, table_flow, "_out_fix_relock")
    orig = T.read_json(out / "picks.json")
    for p in [out / "picks.json.lock.json", out / "scores"] + sorted(out.glob("lead_*")) \
            + sorted(out.glob("test_labels_opened_rivals_lead_*.json")) + sorted(out.glob("board*")):
        if p.name == "board.json":
            continue
        T.move_aside(p, table_toy.moved_root)
    led = out.parent.parent / "_ledger"
    led.mkdir(exist_ok=True)
    lf = led / ("%s.jsonl" % orig["run_fingerprint"])
    lf.write_text(json.dumps({"event": "test_labels_opened", "picks_content_sha256": "3" * 64}) + "\n")
    with pytest.raises(H().HarnessRefusal, match="ledger"):          # picks.json (no lock) is redone, then refused
        H().lock(out, config=table_toy.config)
    assert not (out / "picks.json.lock.json").exists()
    lf.write_text(json.dumps({"event": "test_labels_opened",
                              "picks_content_sha256": H().picks_content_sha(orig["picks"])}) + "\n")
    H().lock(out, config=table_toy.config)                           # reproduced picks: locked
    assert T.read_json(out / "picks.json")["picks"] == orig["picks"]
    rows = [json.loads(x) for x in lf.read_text().splitlines() if x.strip()]
    assert rows[-1]["event"] == "locked"


# ================================================================================================== F4
def _dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    import psutil
    return p.pid


def test_f4_unlock_moves_a_stale_lock_and_never_a_live_one(table_toy):
    from treeroute.runs import preflight, proc
    lockp = Path(table_toy.temp_dir) / preflight.HEAVY_LOCK_FILE
    assert not lockp.exists()
    pid, created = proc.own_identity()
    lockp.write_text(json.dumps({"pid": pid, "pid_created_ms": created}))
    try:
        with pytest.raises(H().HarnessRefusal, match="LIVE"):
            H().unlock(config=table_toy.config)
    finally:
        T.move_aside(lockp, table_toy.moved_root)
    lockp.write_text(json.dumps({"pid": _dead_pid(), "pid_created_ms": 1}))
    msg = H().unlock(config=table_toy.config)
    assert "moved aside" in msg and not lockp.exists()


def _clean_env():
    from treeroute.launch import foreign_environment
    env = dict(os.environ)
    for name in foreign_environment(env):
        env.pop(name, None)
    return env


def _cli(*args, timeout=600):
    return subprocess.run([sys.executable, "-B", "-m", "rivals.cli"] + [str(a) for a in args], cwd=str(T.BUILD_ROOT),
                          env=_clean_env(), capture_output=True, text=True, timeout=timeout)


def test_f4_cli_needs_config_and_prints_one_line_on_a_stale_lock(table_toy, table_flow):
    r = _cli("board", "--out", table_flow.out)
    assert r.returncode == 2, (r.returncode, r.stdout[-800:], r.stderr[-800:])
    from treeroute.runs import preflight
    lockp = Path(table_toy.temp_dir) / preflight.HEAVY_LOCK_FILE
    lockp.write_text(json.dumps({"pid": _dead_pid(), "pid_created_ms": 1}))
    try:
        r = _cli("board", "--out", table_flow.out, "--config", table_toy.config)
        assert r.returncode == 2 and "REFUSED" in r.stdout and "unlock" in r.stdout, (r.stdout[-1500:],
                                                                                      r.stderr[-1500:])
        assert "Traceback" not in r.stdout + r.stderr
        r = _cli("unlock", "--config", table_toy.config)
        assert r.returncode == 0 and "moved aside" in r.stdout, r.stdout + r.stderr
    finally:
        if lockp.exists():                                             # never leave a stale lock for later tests
            T.move_aside(lockp, table_toy.moved_root)
    assert not lockp.exists()
    # (a board made inside pytest is not re-run through the CLI here: its thread-pool record differs from a fresh
    # process's, which load_board refuses by design; test_cli covers a CLI-made board)
    r = _cli("status", "--out", table_flow.out)
    assert r.returncode == 0 and "picks locked: yes" in r.stdout, r.stdout + r.stderr


def test_f4_private_memory_does_not_count_memmap_pages(table_toy):
    path = table_toy.base / "fix_memmap_probe.f32"
    n = 64 << 20                                                       # 256 MiB of float32
    mm = np.memmap(str(path), dtype=np.float32, mode="w+", shape=(n,))
    mm[:] = 1.0
    mm.flush()
    del mm
    before, _ = H().process_tree_memory()
    r = np.memmap(str(path), dtype=np.float32, mode="r", shape=(n,))
    total = 0.0
    for a in range(0, n, 1 << 22):
        total += float(r[a:a + (1 << 22)].sum())
    after, resident = H().process_tree_memory()
    del r
    assert total == float(n)
    assert after - before < (96 << 20), "private memory rose %.0f MiB reading a memmap" % ((after - before) / 2 ** 20)
    T.move_aside(path, table_toy.moved_root)


def test_f4_rf_with_a_row_fraction_below_one_is_repeatable_and_predicts_few_rows(monkeypatch):
    M = T.rivals_models()
    monkeypatch.setattr(M, "RF_ROWS_PER_TREE", 50)
    rng = np.random.default_rng(0)                                    # test data only
    X = rng.standard_normal((400, 5)).astype(np.float32)
    y = X[:, 0] * 2.0 + rng.standard_normal(400)
    z0 = np.zeros(400)
    params = {"max_features": 0.5, "min_samples_leaf": 5}
    score = {"s": (X[:3], np.zeros(3))}
    a = T.fit_predict("rf", params, X, y, z0, "identity", None, None, (-1e9, 1e9), score, (M.RF_TREES,))
    b = T.fit_predict("rf", params, X, y, z0, "identity", None, None, (-1e9, 1e9), score, (M.RF_TREES,))
    assert M.rf_rows_per_tree(400) == 50 and a.info["rows_per_tree"] == 50 and a.info["n_fit"] == 400
    pa_, pb = a["s"][M.RF_TREES]["pre"], b["s"][M.RF_TREES]["pre"]
    assert np.asarray(pa_).shape == (3,) and np.asarray(pa_).tobytes() == np.asarray(pb).tobytes()


def test_f4_one_rf_method_per_board(table_flow):
    """Ruling Z2: the board records the out-of-core RF (no stride); every RF trial saw all its fit rows."""
    board = T.read_json(table_flow.out / "board.json")
    assert "rf_stride" not in board and board["rf"]["method"] == T.rivals_models().RF_METHOD
    tjs = list((table_flow.out / "trials" / "rf").glob("*/trial.json"))
    assert tjs
    for tj in tjs:
        rec = T.read_json(tj)
        assert "rf_stride" not in rec
        info = rec["fit_info"]
        assert info["method"] == board["rf"]["method"] and info["trees"] == T.rivals_models().RF_TREES
        assert info["rows_per_tree"] == min(T.rivals_models().RF_ROWS_PER_TREE, info["n_fit"])


def test_f4_the_fit_set_copy_checks_disk_and_moves_a_killed_temp_file_aside(table_toy, table_export, monkeypatch):
    out = T.h_init(table_toy, table_export.dirs[0], table_toy.base / "_out_fix_disk", ())
    mdir = out / "materialized"
    mdir.mkdir(exist_ok=True)
    tmp = mdir / "lead_0_tune.f32.tmp_99999"
    tmp.write_bytes(b"\0" * 1024)
    import collections
    Usage = collections.namedtuple("Usage", "total used free")
    monkeypatch.setattr(H().shutil, "disk_usage", lambda p: Usage(10, 10, 0))
    with pytest.raises(H().HarnessRefusal, match="free"):
        H().tune(out, resume=True, config=table_toy.config)
    assert not tmp.exists(), "the killed copy's temp file was not moved aside"


def test_f4_ours_is_tied_to_the_runs_own_scores(table_flow):
    chk = T.read_json(table_flow.out / "scores" / "lead_0_ours_check.json")
    assert str(chk["result"]).startswith("pass"), chk


def test_f4_a_lead_guard_reads_the_runs_saved_trees_off_when_it_exists(table_toy, table_flow):
    for L in table_toy.leads:
        if L == 0:
            continue
        for dj in (table_flow.out / ("lead_%d" % L)).glob("done_*.json"):
            src = T.read_json(dj)["comparator_source"]
            assert "saved guard_preds" in src or "rebuilt" in src, src


def test_f4_a_hard_killed_tune_resumes_after_unlock_and_ends_byte_equal(table_toy, table_export, table_flow):
    """Robustness review 1 and 14: a real kill (taskkill /F /T) of a CLI tune, then the stale-lock refusal (one
    line, exit 2), unlock, resume; the picks and every trial prediction equal an uninterrupted board's."""
    out_root = table_toy.base / "_out_fix_kill"
    r = _cli("init", "--run", table_toy.run, "--export", table_export.dirs[0], "--out", out_root,
             "--extra-learners", "hgb_l1", "--config", table_toy.config)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    out = out_root / table_toy.package_name / table_toy.run_name
    p = subprocess.Popen([sys.executable, "-B", "-m", "rivals.cli", "tune", "--out", str(out), "--resume",
                          "--config", str(table_toy.config)], cwd=str(T.BUILD_ROOT), env=_clean_env(),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log = out / "rivals.log"
    t0 = time.time()
    while time.time() - t0 < 300:
        if log.is_file() and log.read_text(encoding="utf-8").count("| trial |") >= 3:
            break
        if p.poll() is not None:
            break
        time.sleep(0.5)
    assert p.poll() is None, "the tune finished before it could be killed"
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    p.wait(timeout=60)
    finished = len(list((out / "trials").glob("*/*/trial.json")))
    assert finished >= 1
    r = _cli("tune", "--out", out, "--resume", "--config", table_toy.config)
    assert r.returncode == 2 and "stale heavy-job lock" in r.stdout and "unlock" in r.stdout, r.stdout + r.stderr
    assert "Traceback" not in r.stdout + r.stderr
    r = _cli("unlock", "--config", table_toy.config)
    assert r.returncode == 0, r.stdout + r.stderr
    r = _cli("tune", "--out", out, "--resume", "--config", table_toy.config)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert log.read_text(encoding="utf-8").count("skipped (finished, same config hash)") >= finished
    r = _cli("lock", "--out", out, "--config", table_toy.config)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    a, b = T.read_json(out / "picks.json"), T.read_json(table_flow.out / "picks.json")
    assert H().picks_content_sha(a["picks"]) == H().picks_content_sha(b["picks"])
    fa = sorted(x.relative_to(out) for x in T.trial_pred_files(out))
    fb = sorted(x.relative_to(table_flow.out) for x in T.trial_pred_files(table_flow.out))
    assert fa == fb and fa
    diff = [str(x) for x in fa if (out / x).read_bytes() != (table_flow.out / x).read_bytes()]
    assert not diff, diff[:5]
