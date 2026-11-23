"""Unit tests for the legacy-harness tools (pure helpers only; nothing heavy runs).

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine"
    py -3.9 -m pytest legacy_harness/tests -q

The engine's own suite (`py -3.9 -m pytest`, testpaths = tests) does not collect these.
"""
import json
import os
import subprocess
import sys

import pytest

HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HARNESS)

import goldens as G  # noqa: E402
import launch_pinned as L  # noqa: E402
import rooted_copy as R  # noqa: E402

OUT = "D:/treeroute/golden/fire_smoke"


def test_paths_under_scope():
    assert L.strictly_under("D:/treeroute/golden/fire_smoke", L.SCOPE)
    assert L.strictly_under("d:\\TREEROUTE\\golden\\x\\y", L.SCOPE)
    assert not L.strictly_under("D:/treeroute/golden", L.SCOPE)
    assert not L.strictly_under("D:/treeroute/golden_other", L.SCOPE)
    assert not L.strictly_under("D:/adaptation/x", L.SCOPE)
    assert L.is_under("D:/adaptation/fire/_preds.npz", "D:/adaptation")
    assert not L.is_under("D:/adaptation2/x", "D:/adaptation")


def test_split_argv_needs_separator():
    with pytest.raises(L.LaunchRefused):
        L.split_argv(["--script", "x.py", "--out-dir", "D:/treeroute/golden/a"])
    opts, args = L.split_argv(["--script", "x.py", "--", "--problem=fire", "--"])
    assert opts == ["--script", "x.py"] and args == ["--problem=fire", "--"]


def test_parse_options_refuses_unknown_and_missing():
    with pytest.raises(L.LaunchRefused):
        L.parse_options(["--script", "x.py", "--out-dir", "D:/treeroute/golden/a", "--workers", "8"])
    with pytest.raises(L.LaunchRefused):
        L.parse_options(["--script", "x.py"])
    o = L.parse_options(["--script", "x.py", "--out-dir", "D:/treeroute/golden/a",
                         "--redirect-prefix", "D:/fire/A_", "--redirect-prefix", "D:/fire/pool_",
                         "--env", "A=1", "--min-avail-gb", "8.5", "--watch", "D:/fire"])
    assert o["redirect"] == ["D:/fire/A_", "D:/fire/pool_"] and o["min_avail_gb"] == 8.5
    assert o["scratch"] == L.DEFAULT_SCRATCH and o["watch"] == ["D:/fire"]
    assert o["check_only"] is False


def test_parse_options_check_only_is_a_flag():
    o = L.parse_options(["--check-only", "--script", "x.py", "--out-dir", "D:/treeroute/golden/a"])
    assert o["check_only"] is True and o["script"] == "x.py"


@pytest.mark.parametrize("pair", ["OMP_NUM_THREADS=16", "openblas_num_threads=2", "MKL_CBWR=AUTO",
                                  "KMP_AFFINITY=x", "JOBLIB_TEMP_FOLDER=D:/treeroute/golden/j",
                                  "ADAPTATION_OUT_ROOT=D:/adaptation",
                                  "ADAPTATION_OUT_ROOT=D:/treeroute/golden",
                                  # the retry trap: inside the scope, but an EARLIER run's folder
                                  "ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke_old",
                                  "ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smok",
                                  "ADAPTATION_OUT_ROOT=../fire_smoke", "ADAPTATION_OUT_ROOT=\\\\srv\\x",
                                  "NOEQUALS", "1BAD=x"])
def test_parse_env_refusals(pair):
    with pytest.raises(L.LaunchRefused):
        L.parse_env([pair], OUT)


def test_parse_env_accepts_paths_inside_out_dir_and_plain_values():
    env = L.parse_env(["ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke", "FLAG=abc",
                       "SUB=d:\\treeroute\\golden\\fire_smoke\\x"], OUT)
    assert env["ADAPTATION_OUT_ROOT"] == "D:/treeroute/golden/fire_smoke" and env["FLAG"] == "abc"
    with pytest.raises(L.LaunchRefused):          # same value, but --out-dir changed on a retry
        L.parse_env(["ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke"], OUT + "_2")


@pytest.mark.parametrize("p", ["D:/fire/", "D:/", "fire/A_", "D:/fire/A_*", "D:/treeroute/golden/x_"])
def test_check_prefixes_refusals(p):
    with pytest.raises(L.LaunchRefused):
        L.check_prefixes([p])


@pytest.mark.parametrize("w", ["fire", "D:/", "D:\\", "D:/treeroute/golden", OUT, OUT + "/sub",
                               "D:/treeroute/golden/_scratch", "D:/treeroute"])
def test_check_watch_refusals(w):
    with pytest.raises(L.LaunchRefused):
        L.check_watch([w], OUT, "D:/treeroute/golden/_scratch")


def test_check_watch_accepts_and_dedupes():
    got = L.check_watch(["D:/fire", "d:\\fire\\", "D:/joblib_tmp", "D:/treeroute/_absent_x"], OUT,
                        "D:/treeroute/golden/_scratch")
    assert got == ["D:/fire", "D:/joblib_tmp", "D:/treeroute/_absent_x"]


def test_redirect_target_maps_names_only():
    pre = L.check_prefixes(["D:/fire/A_", "D:/fire/pool_features_"])
    s = "D:/treeroute/golden/_scratch"
    assert L.redirect_target("D:/fire/A_adapt_raw_123.f16", pre, s) == s + "/A_adapt_raw_123.f16"
    assert L.redirect_target("d:\\fire\\pool_features_9.f32", pre, s) == s + "/pool_features_9.f32"
    assert L.redirect_target("D:/fire/A_*.f16", pre, s) == s + "/A_*.f16"
    assert L.redirect_target("D:/fire/target/*.parquet", pre, s) is None
    assert L.redirect_target("D:/fire/region_sizes.csv", pre, s) is None
    assert L.redirect_target(12, pre, s) is None


def test_diff_snapshots():
    d = L.diff_snapshots({"a": [1, 1], "b": [2, 2], "c": [3, 3]}, {"a": [1, 1], "b": [2, 5], "d": [4, 4]})
    assert d == {"added": ["d"], "removed": ["c"], "changed": ["b"]}


def test_watch_snapshot_sees_a_file_created_and_deleted(tmp_path):
    """A watched folder records folder mtimes, so a transient scratch file still shows."""
    w = tmp_path / "watched"
    (w / "sub").mkdir(parents=True)
    (w / "keep.txt").write_text("x")
    old = 1_000_000_000
    for p in (w, w / "sub", w / "keep.txt"):
        os.utime(str(p), (old, old))
    before = L.snapshot_tree([str(w)], with_dirs=True)
    files_only = L.snapshot_tree([str(w)])
    t = w / "sub" / "tmp.f32"
    t.write_bytes(b"0" * 16)
    t.unlink()
    d = L.diff_snapshots(before, L.snapshot_tree([str(w)], with_dirs=True))
    assert d["changed"] == [str(w / "sub").replace("\\", "/") + "/"]
    assert not any(L.diff_snapshots(files_only, L.snapshot_tree([str(w)])).values())
    assert L.snapshot_tree([str(tmp_path / "absent")], with_dirs=True) == {}


def _copy_fixture(tmp_path, other_line=None):
    src = tmp_path / "shipped.py"
    src.write_bytes(b"import os\r\n" + R.OLD + b"\r\nSEED = 7\r\n")
    dst = tmp_path / "rooted.py"
    body = b"import os\r\n" + R.NEW + b"\r\nSEED = 7\r\n"
    if other_line is not None:                     # a ONE-line edit, but not the OUT_ROOT line
        body = b"import os\r\n" + R.OLD + b"\r\n" + other_line + b"\r\n"
    dst.write_bytes(body)
    return str(src), str(dst)


def test_copy_check_accepts_only_the_out_root_edit(tmp_path):
    src, dst = _copy_fixture(tmp_path)
    ok = L.copy_check(src, dst)
    assert ok["ok"] and ok["changed_lines"] == [2] and ok["checked_by"] == "rooted_copy.check"
    b = tmp_path / "b"
    b.mkdir()
    src2, bad = _copy_fixture(b, other_line=b"SEED = 8")
    res = L.copy_check(src2, bad)
    assert not res["ok"] and res["changed_lines"] == [3]
    assert "not the expected OUT_ROOT change" in "; ".join(res["problems"])


def test_preflight_refuses_a_wrong_one_line_copy_before_anything_runs(tmp_path, monkeypatch):
    """The launcher itself refuses a one-line edit of a constant (it used to count lines only)."""
    src = os.path.join(L.PROJECT, "adaptation.py")
    with open(src, "rb") as f:
        lines = f.read().splitlines(keepends=True)
    i = next(k for k, ln in enumerate(lines) if ln.startswith(b"DELTA = "))
    eol = lines[i][len(lines[i].rstrip(b"\r\n")):]
    lines[i] = b"DELTA = 0.02" + eol
    bad = tmp_path / "adaptation_wrong.py"
    bad.write_bytes(b"".join(lines))
    assert L.copy_check(src, str(bad))["changed_lines"] == [i + 1]      # exactly one line differs
    monkeypatch.setattr(L, "NUMERIC_MODULES", ())
    monkeypatch.setattr(L, "other_python_processes", lambda: [])
    monkeypatch.setattr(L, "available_gb", lambda: 99.0)
    o = L.parse_options(["--script", str(bad), "--copy-of", src,
                         "--out-dir", "D:/treeroute/golden/_never_created_by_tests"])
    with pytest.raises(L.LaunchRefused) as e:
        L.preflight(o, [])
    assert "not the rooted copy" in str(e.value)
    assert not os.path.exists("D:/treeroute/golden/_never_created_by_tests")


def test_preflight_ram_check_is_last(monkeypatch):
    monkeypatch.setattr(L, "NUMERIC_MODULES", ())
    monkeypatch.setattr(L, "other_python_processes", lambda: [])
    monkeypatch.setattr(L, "available_gb", lambda: 1.0)
    o = L.parse_options(["--script", os.path.join(HARNESS, "adaptation_rooted.py"), "--copy-of",
                         os.path.join(L.PROJECT, "adaptation.py"), "--out-dir",
                         "D:/treeroute/golden/_never_created_by_tests", "--scratch",
                         "D:/treeroute/golden/_never_created_by_tests_scratch",
                         "--min-avail-gb", "8.5"])
    with pytest.raises(L.LaunchRefused) as e:
        L.preflight(o, [])
    assert "every other pre-flight check passed" in str(e.value)
    monkeypatch.setattr(L, "available_gb", lambda: 9.0)
    pf = L.preflight(o, [])
    assert pf["copy"]["ok"] and pf["copy"]["changed_lines"] == [139]


def test_heavy_job_markers():
    procs = [(1, "py -3.9 -u adaptation.py --problem=defo"), (2, "python -m pytest"),
             (3, "py -3.9 m0_input_hashes.py"), (4, "python pm25_adaptation_fast.py --smoke"),
             (5, "python some_editor_helper.py")]
    assert [p for p, _ in L.heavy_jobs(procs)] == [1, 3, 4]


def test_bad_pools():
    rows = [{"user_api": "blas", "num_threads": 1}, {"user_api": "openmp", "num_threads": 4}]
    assert L.bad_pools(rows) == []
    rows.append({"user_api": "blas", "num_threads": 4})
    assert L.bad_pools(rows) == [{"user_api": "blas", "num_threads": 4}]


def test_rooted_copy_is_one_line_change_of_the_shipped_file():
    res = R.check()                                   # read-only on both files
    assert res["ok"], res["problems"]
    assert [c["line"] for c in res["changed_lines"]] == [139]
    assert res["changed_lines"][0]["source"] == R.OLD.decode()
    assert res["changed_lines"][0]["copy"] == R.NEW.decode()


def test_rooted_copy_matches_the_newest_registry():
    reg, problems = R.check_registered(R.check())
    assert reg is not None and problems == []


def test_rooted_copy_make_never_overwrites(tmp_path):
    dst = tmp_path / "exists.py"
    dst.write_text("keep me")
    with pytest.raises(SystemExit):
        R.make(dst=str(dst))
    assert dst.read_text() == "keep me"


def test_rooted_copy_make_on_a_fixture(tmp_path):
    src = tmp_path / "shipped.py"
    src.write_bytes(b"import os\r\n" + R.OLD + b"\r\nx = 1\r\n")
    dst = tmp_path / "rooted.py"
    res = R.make(src=str(src), dst=str(dst))
    assert res["ok"] and dst.read_bytes() == b"import os\r\n" + R.NEW + b"\r\nx = 1\r\n"


def test_importing_the_harness_loads_nothing_numeric():
    code = ("import sys; sys.path.insert(0, %r); import launch_pinned, rooted_copy, goldens; "
            "bad = [m for m in ('numpy', 'scipy', 'sklearn', 'pandas', 'threadpoolctl') "
            "if m in sys.modules]; print(bad)" % HARNESS)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"


def test_every_registry_version_is_consistent():
    """Every version: file entries have a path, a size and a 64-hex sha256; v2+ name what they supersede."""
    versions = G.registry_versions()
    assert versions and versions[0][0] == 1
    for n, path in versions:
        reg = json.load(open(path, encoding="utf-8"))
        assert reg.get("version", 1) == n
        if n >= 2:
            assert reg["supersedes"]["version"] == n - 1 and reg["changes"]
        cnt = 0
        for gid, g in reg["goldens"].items():
            for f in g.get("files", []):
                assert set(f) >= {"path", "size", "sha256"}, gid
                assert len(f["sha256"]) == 64 and int(f["sha256"], 16) >= 0, gid
                cnt += 1
        assert cnt > 0


def test_registry_versions_fail_loudly_on_a_gap(tmp_path):
    (tmp_path / "goldens.json").write_text("{}")
    assert G.latest_registry(str(tmp_path))[0] == 1
    (tmp_path / "goldens_v3.json").write_text("{}")
    with pytest.raises(SystemExit):
        G.registry_versions(str(tmp_path))
    (tmp_path / "goldens_v2.json").write_text("{}")
    assert G.latest_registry(str(tmp_path))[0] == 3


def test_fire_commands_keep_env_and_out_dir_equal():
    for gb in (G.FIRE_CAUTION_GB, G.FIRE_SHIPPED_GUARD_GB):
        c = G.fire_command(out_dir="D:/treeroute/golden/fire_smoke_2", min_gb=gb)
        assert "--out-dir D:/treeroute/golden/fire_smoke_2 --env ADAPTATION_OUT_ROOT=" \
               "D:/treeroute/golden/fire_smoke_2 " in c
        assert "--min-avail-gb %.1f -- --problem=fire --calib=strict --smoke=1" % gb in c
        assert "--watch D:/fire --watch D:/joblib_tmp" in c
    assert "--check-only --" in G.fire_command(check_only=True)


def _fake_run(tmp_path, **over):
    """A fire run folder with a launcher.json that passes check_fire_record."""
    run = tmp_path / "fire_smoke_2"
    (run / "fire_strict_smoke").mkdir(parents=True)
    outs = []
    for rel in G.FIRE_EXPECTED_REL:
        p = run / rel
        p.write_bytes(rel.encode())
        outs.append({"path": str(p).replace("\\", "/"), "size": p.stat().st_size,
                     "sha256": G.sha256_file(str(p))})
    fire = {"script_sha256": "a" * 64, "source_sha256": "b" * 64, "argv": G.FIRE_ARGV,
            "outputs_expected_relative": G.FIRE_EXPECTED_REL + ["launcher.json"]}
    lj = {"exit_code": 0, "pins_ok_at_end": True, "protected_roots_changed": {"added": []},
          "redirect_sources_changed": {}, "watched_changed": {"added": [], "changed": []},
          "watch": list(G.FIRE_WATCH), "redirect_prefixes": list(G.FIRE_PREFIXES),
          "argv": list(G.FIRE_ARGV), "env_script": {"ADAPTATION_OUT_ROOT": str(run)},
          "script_sha256": "a" * 64, "copy_of": {"source_sha256": "b" * 64, "ok": True},
          "scratch_left": [], "outputs": outs}
    lj.update(over)
    return str(run), lj, fire


def test_check_fire_record_accepts_a_clean_run(tmp_path):
    run, lj, fire = _fake_run(tmp_path)
    assert G.check_fire_record(lj, fire, run) == []


@pytest.mark.parametrize("over,needle", [
    ({"exit_code": 1}, "exit code"),
    ({"pins_ok_at_end": False}, "pins"),
    ({"watched_changed": {"added": ["D:/fire/x"]}}, "leak (watched_changed)"),
    ({"watch": ["D:/fire"]}, "not watched"),
    ({"redirect_prefixes": ["D:/fire/A_"]}, "not redirected"),
    ({"argv": ["--problem=fire", "--calib=strict", "--smoke=1", "--arms=base"]}, "script arguments"),
    ({"env_script": {"ADAPTATION_OUT_ROOT": "D:/treeroute/golden/fire_smoke"}}, "ADAPTATION_OUT_ROOT"),
    ({"script_sha256": "c" * 64}, "different adaptation_rooted.py"),
    ({"copy_of": {"source_sha256": "b" * 64, "ok": False}}, "--copy-of check"),
    ({"scratch_left": ["pool_features_1.f32"]}, "scratch files"),
])
def test_check_fire_record_refusals(tmp_path, over, needle):
    run, lj, fire = _fake_run(tmp_path, **over)
    probs = G.check_fire_record(lj, fire, run)
    assert any(needle in p for p in probs), probs


def test_check_fire_record_rehashes_outputs(tmp_path):
    run, lj, fire = _fake_run(tmp_path)
    with open(os.path.join(run, "console.txt"), "ab") as f:
        f.write(b"!")
    assert any("changed since the run" in p for p in G.check_fire_record(lj, fire, run))
    del lj["outputs"][0]
    assert any("expected outputs missing" in p for p in G.check_fire_record(lj, fire, run))


def test_next_folds_a_fire_run_and_verify_reads_it(tmp_path, capsys):
    """Option A end to end, in a temp folder: copy version 1, fold a fake-but-valid fire run into
    version 2, then verify reads version 2 (write-once: a second fold is refused)."""
    import shutil
    here = tmp_path / "reg"
    here.mkdir()
    shutil.copyfile(G.REGISTRY, str(here / "goldens.json"))
    chk = R.check()
    run, lj, _fire = _fake_run(tmp_path, script_sha256=chk["copy_sha256"],
                               copy_of={"source_sha256": chk["source_sha256"], "ok": True})
    with open(os.path.join(run, "launcher.json"), "x", encoding="utf-8") as f:
        json.dump(lj, f)
    v2 = G.build_next("test fold", fire_run=run, here=str(here))
    assert v2.endswith("goldens_v2.json") and G.latest_registry(str(here))[0] == 2
    reg = json.load(open(v2, encoding="utf-8"))
    fire = reg["goldens"]["fire_smoke"]
    assert fire["status"].startswith("CAPTURED") and fire["run_dir"] == run.replace("\\", "/")
    assert len(fire["files"]) == len(G.FIRE_EXPECTED_REL) + 1
    assert reg["supersedes"]["version"] == 1 and "test fold" in reg["changes"]
    assert reg["goldens"]["defo_link_corrector"] == json.load(
        open(G.REGISTRY, encoding="utf-8"))["goldens"]["defo_link_corrector"]
    assert G.verify(here=str(here), golden=str(tmp_path)) == 0
    assert "FOLDED from" in capsys.readouterr().out
    with pytest.raises(SystemExit):                  # --fire-run is refused once folded
        G.verify(here=str(here), golden=str(tmp_path), fire_run=run)
    with open(os.path.join(run, "console.txt"), "ab") as f:
        f.write(b"!")
    assert G.verify(here=str(here), golden=str(tmp_path)) == 1


def test_next_refuses_to_fold_an_invalid_run(tmp_path):
    import shutil
    here = tmp_path / "reg"
    here.mkdir()
    shutil.copyfile(G.REGISTRY, str(here / "goldens.json"))
    run, lj, _fire = _fake_run(tmp_path, exit_code=1)
    with open(os.path.join(run, "launcher.json"), "x", encoding="utf-8") as f:
        json.dump(lj, f)
    with pytest.raises(SystemExit):
        G.build_next("bad", fire_run=run, here=str(here))
    assert G.latest_registry(str(here))[0] == 1
