"""Smoke of the ridge loader scripts/ridge_shap.py. Writes only smoke/ridge_<label>/: its synthetic boards, exports,
samples and registers, the outputs, logs and smoke_report.json. It never writes the analysis' SAMPLE_REGISTER.txt,
sample/, out/, rebuild/ or logs/: every ridge_shap.py run gets --out-root and --log-dir under the smoke folder (checked
before it starts), and the compare and env children and rival_shap.py's in-process runs log under the smoke folder.

  py -3.9 -I -B smoke_ridge.py [--label smoke] [--step all|synthetic|fire|compare|coral|others] [--fresh]
        [--problems pm25 defo ndvi]

  synthetic  no real data (under 0.5 GB, about a minute): S1-S7 below (with S4b and S5b)
  fire       real (R1, R2): --exactness-only on every fire lead-0 test row; the full run on the registered fire sample
             into the smoke folder, again (skipped); out/fire/lead_0 unchanged
  compare    real (R3): compare_shap.py (a child, 1 thread, 200 draws) on the smoke's fire models root, with copies of
             out/fire/lead_0's other pieces; only structured fields are read (per_lead.json models, links,
             declined_by_guard, main_set; pairs.parquet pair_label), never a statistic; ridge_shap.py afterwards:
             skipped, no REMINDER; then the smoke's compare/ folder is removed
  coral      real (R4): --exactness-only; the full run against coral's finished piece (keys, phi, base, eta bit for
             bit); a copy of that piece: nothing to do, a stale copy refused, --exactness-only refused, an S-ENV stop
             (a doctored board copy) and an S-SAMPLE stop (an empty register) that write nothing; out/coral unchanged
  others     real (R5): --exactness-only on PM2.5, defo and NDVI (--problems), the guard checked before each

Each step refuses when its own output folders exist, unless --fresh, which removes only those folders (before any
guard check). Each real step checks the heavy-job guard at its start and again before each child and the copies made
for it (no lock file D:/treeroute/tmp/treeroute_heavy_job.lock or engine_tmp/treeroute_heavy_job.lock, no SHAP
process of the owner: no command line naming run_shap, tr_rebuild, tr_shap, rival_shap, compare_shap, make_sample,
ridge_shap or bardl_shap; at least 6 GiB of free RAM). When a check fails, the step stops there (exit 4); a guard
that cannot run counts as failed. Each real step ends with the privacy scan of the whole smoke folder with
C.private_names() (the account and host names, and the accounts in the runs' recorded machine paths), or with this
machine's names only after a guard stop. A crash inside a real step's function is scanned too (with the recorded
names only if a guard check has passed in that step), the outcome is logged, and the crash goes on. The synthetic
step reads no real data and needs 3 GiB free. Exit 1 when a check fails.

Synthetic checks. Every synthetic board is made by the board's own code (rivals/models.py fit_predict); its link-space
output, the f argument of its _to_y call, is captured; the saved raw is the engine's clip_to_legal of the saved pre
(harness.py:1298-1299); the saved rows are in another order than the test set (the key join). ridge_shap.main() runs
in this process on synthetic board folders, with the export and run readers (H.ExportLead, H.Run) replaced by small
fakes that serve the synthetic test set and refit rows; rival_shap.py's own load_context runs on them.
  S1  exactness() on a 91,440-row world (65,536 + 25,904 rows; 12 columns with NaN, a constant, an all-NaN column and
      one constant on its values but with NaN): pre and raw on every row; the loader's link-space output equals the
      board's captured one bit for bit; both blocks stored column by column; the row-by-row copy (information) is
      rival_shap.py's way exactly and misses rows; a C-ordered X changes nothing; mutations caught in link space
      (one call for the whole test set, 50,000-row blocks, 1 BLAS thread) whether or not pre still passes; a
      coefficient scaled by 1 + 1e-12 fails with where_rows_differ; one saved raw value moved by 1 ulp fails raw
      only; no flags (70,000 rows): row-ordered blocks and rival_shap.py's way passes; an identity-link world
      (NDVI-like) and a log_c world with c 1.5 and an open upper bound (PM2.5-like) pass on pre and raw with clipped
      rows; an infinite coefficient is an S-EXACT refusal, not a crash
  S2  ridge_shap.main() on a 7-player world (a merged c__ctx:top5 copy, a flag on x only and on one b only, a dropped
      constant, a player equal on every b, an equal normal): exit 0; phi at both levels within 1e-12 of brute-force
      Shapley values; additivity; S-ZERO; eta_model is the board's link value and pre the saved pre, bit for bit; both
      evaluator maxima are numbers within 1e-12; meta and done record as designed; rival_shap.py's exactness.json
      untouched; the same through the identity-link and the open-bound worlds (their link keys)
  S3  main() on the 91,440-row world (50 explained rows) with --n left out (the registered N): every file; a rerun
      with --n 50 skipped with no file changed; --exactness-only into a fresh root writes ridge_shap_exactness.json only
  S4  gates (exit 3): S-EXACT (a scaled coefficient, a doctored raw value, a wrong preds_sha256, an export refusal, an
      infinite coefficient, a test set that changes before load_context reads it, a repeat scoring that differs);
      S-ENV (a wrong version, 1 BLAS thread, numpy's pool missing from threadpool_info) and S-SAMPLE before the
      piece's identity is known (an unregistered sample, a wrong --n beside a finished piece): nothing written, the
      finished piece kept, no data reader called; S-SAMPLE in load_context (a sample row that is not a test row) and
      S-BG: the done record removed; S-EVAL (a background value moved by 1e-6; a design row moved by 1 ulp)
  S4b --exactness-only: a stop in this script's own folder removes its done record; a pass removes this script's
      FAILED.json of an earlier S-EXACT stop at stage inputs or bits and no other: another script's record, this
      script's S-SAMPLE and S-EXACT reread records, and a real writer stop's record (S-EVAL) all stay
  S5  refusals (exit 1, nothing written): the drift guard, no ridge pick, a heavy-job lock, another SHAP step running
      (a planted process), an unreadable done record; busy_processes on a constructed process list (Python processes
      naming a SHAP script count; an editor, the smoke and this process's own line do not); own_lineage when psutil's
      walk fails (the direct parent, the py launcher, is skipped) and when it works (a recorded parent id is not
      added); another script's piece:
      current -> exit 0 and nothing written; stale -> exit 1; --exactness-only -> exit 1; S-ENV and S-SAMPLE stops
      there write nothing (exit 3); --rows without --out-root -> exit 2
  S5b rival_shap.py's own main() in this process (its log under the smoke): its finished ridge piece on a no-flag
      board -> ridge_shap.py 'nothing to do', exit 0, nothing written (rs_identity against rival_shap.py's own
      identity, not against itself); a rival_shap.py re-run beside ridge_shap.py's piece on the flagged 91,440-row
      board -> exit 3 at its S-EXACT, only exactness.json written; ridge_shap.py then skipped, no file changed
  S6  the compare reminder: a skip beside a comparison that does not list rival_ridge logs a REMINDER; compare_shap.py
      (a child, 1 thread) picks rival_ridge up by its folder name, labels it declined by its guard (D6) and keeps it
      out of the main set; a skip beside that comparison logs no REMINDER
  S7  hygiene: the copied-source hashes; no account or host name in the smoke folder; no __pycache__ under scripts/
      or smoke/; no analysis log written or changed
"""
import argparse
import copy
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
import shapv1_common as C  # noqa: E402   (standard library only at import: numpy loads inside the steps)

THIS = os.path.abspath(__file__)
RIDGE = os.path.join(SCRIPTS, "ridge_shap.py")
LOCKS = ("D:/treeroute/tmp/treeroute_heavy_job.lock", os.path.join(C.ROOT, "engine_tmp", "treeroute_heavy_job.lock"))
OWNER_RX = re.compile(r"run_shap|tr_rebuild|tr_shap|rival_shap|compare_shap|make_sample|ridge_shap|bardl_shap")
MIN_FREE_GIB = 6.0
MIN_FREE_SYNTH_GIB = 3.0
STEPS = ("synthetic", "fire", "compare", "coral", "others")
FIRE_OTHERS = ("treeroute", "rival_lgbm", "rival_lgbm_tweedie", "rival_rf")
STEP_DIRS = {"synthetic": ["synthetic"], "fire": ["fire_exact", "fire_models"],
             "compare": [os.path.join("fire_models", m) for m in FIRE_OTHERS + ("compare",)],
             "coral": ["coral_exact", "coral_models", "coral_foreign", "coral_board_doctored", "coral_register"],
             "others": ["exact_pm25", "exact_defo", "exact_ndvi"]}
WATCH_LOGS = ("ridge_shap_", "smoke_ridge", "compare_fire_lead0", "rival_shap_fire_lead0", "compare_coral_lead0",
              "rival_shap_coral_lead0")
VERSION_KEYS = ("lightgbm", "numpy", "pandas", "pyarrow", "scikit-learn", "scikit-learn-intelex", "threadpoolctl")
NUMPY_POOL_ROW = ["blas", "openblas", "libscipy_openblas", 8]
CF = 0.012987012987012988                     # fire's c at lead 0
EXPECT_TEST_ROWS = {"fire": 96000, "coral": 2312, "pm25": 91440, "defo": 369096, "ndvi": 95184}
REPORT = {}
FAIL = []
WORLDS = {}                                    # synthetic worlds by their run and export folders (the fake readers)
GUARD = {"passed": False}                      # whether a heavy-job guard check has passed in the current step


class GuardStop(Exception):
    pass


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="smoke")
    ap.add_argument("--step", default="all", choices=("all",) + STEPS + ("compare-child", "env-child"))
    ap.add_argument("--fresh", action="store_true", help="remove the step's own folders first")
    ap.add_argument("--problems", nargs="*", default=["pm25", "defo", "ndvi"], help="others: the problems to check")
    ap.add_argument("--child-root", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--child-sample", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--child-register", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--child-export", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--child-board", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--child-problem", default="fire", help=argparse.SUPPRESS)
    ap.add_argument("--child-extra", nargs="*", default=[], help=argparse.SUPPRESS)
    a = ap.parse_args()
    if not re.match(r"^[A-Za-z0-9_-]{1,40}$", a.label):
        raise SystemExit("REFUSED: --label must be letters, digits, _ or -")
    bad = [p for p in a.problems if p not in C.PROBLEMS]
    if bad:
        raise SystemExit("REFUSED: unknown problems %s" % bad)
    if not a.problems:
        raise SystemExit("REFUSED: --problems needs at least one problem")
    return a


def check(name, ok, value):
    REPORT[name] = {"pass": bool(ok), "value": value}
    print("%-100s %s  %s" % (name[:100], "PASS" if ok else "FAIL", str(value)[:300]), flush=True)
    if not ok:
        FAIL.append(name)


def guard():
    """(ok, record): no heavy-job lock (either place), no SHAP process of the owner (a ridge_shap.py or bardl_shap.py
    run of the owner included), enough free RAM. smoke_ridge.py itself does not match the pattern, and its own
    ridge_shap.py children run one after another, never while the guard is checked."""
    import psutil
    locks = [p for p in LOCKS if os.path.exists(p)]
    own = 0
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cl = " ".join(p.info.get("cmdline") or [])
        except Exception:
            continue
        if OWNER_RX.search(cl):
            own += 1
    free = psutil.virtual_memory().available / 2 ** 30
    ok = (not locks) and own == 0 and free >= MIN_FREE_GIB
    return ok, {"lock_files": len(locks), "shap_processes": own, "available_gib": round(free, 2)}


def need_guard(what, log):
    g = None
    try:
        ok, g = guard()
        log("heavy-job guard before %s: %s" % (what, g))
    except Exception as exc:                          # a guard that cannot run (or log) counts as a failed guard
        ok = False
        g = {"guard_error": type(exc).__name__} if g is None else dict(g, log_error=type(exc).__name__)
    if not ok:
        REPORT.setdefault("_guard_stops", []).append({"before": what, "guard": g})
        raise GuardStop("the heavy-job guard failed before %s: %s" % (what, g))
    GUARD["passed"] = True


def py_cmd():
    return [sys.executable, "-I", "-B"]


def clean_env():
    """The environment without thread pins (each child sets its own before numpy loads)."""
    return {k: v for k, v in os.environ.items() if not k.upper().startswith(("OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_",
                                                                              "BLIS_", "VECLIB_"))}


def run_child(cmd, log, what):
    t0 = time.time()
    rc = subprocess.call(cmd, env=clean_env())
    log("%s: exit %d in %.1f s" % (what, rc, time.time() - t0))
    return rc


def ridge_cmd(W, problem, out_root, *extra):
    """A ridge_shap.py child whose outputs and log stay under the smoke folder (asserted before it starts)."""
    logs = os.path.join(W, "logs")
    for p in (out_root, logs):
        if not C.norm(p).startswith(C.norm(W) + "/"):
            raise SystemExit("REFUSED: %s is not under the smoke folder" % p)
    return py_cmd() + [RIDGE, "--problem", problem, "--lead", "0", "--out-root", out_root, "--log-dir", logs] + list(
        extra)


def logs_state():
    """Size and time of the analysis' log files this smoke could touch by mistake (they must not change)."""
    out = {}
    if os.path.isdir(C.LOGS):
        for f in sorted(os.listdir(C.LOGS)):
            if f.startswith(WATCH_LOGS):
                st = os.stat(os.path.join(C.LOGS, f))
                out[f] = [st.st_size, st.st_mtime_ns]
    return out


def tree_state(folder):
    """{relative path: SHA-256} of every file under folder (empty when it does not exist)."""
    out = {}
    if not os.path.isdir(folder):
        return out
    for d, _, files in os.walk(folder):
        for f in files:
            p = os.path.join(d, f)
            out[os.path.relpath(p, folder).replace("\\", "/")] = C.sha256_file(p)
    return out


def prepare(W, step, fresh, log):
    ex = [os.path.join(W, d) for d in STEP_DIRS[step] if os.path.exists(os.path.join(W, d))]
    if ex and not fresh:
        raise SystemExit("REFUSED: %s exists from an earlier smoke; pass --fresh to remove the step's own folders" % ex)
    for d in ex:
        shutil.rmtree(C.assert_writable(d))
        log("--fresh: removed %s" % d)


def failed_gate(folder):
    """The gate a FAILED.json names (its gate field, or the writer's failed checks), or None."""
    f = os.path.join(folder, "FAILED.json")
    if not os.path.isfile(f):
        return None
    rec = C.read_json(f)
    return rec.get("gate") or [k for k, v in (rec.get("checks_passed") or {}).items() if not v]


def smoke_log_class(W):
    Base = C.Log

    class SmokeLog(Base):
        def __init__(self, name, folder=None):
            Base.__init__(self, name, os.path.join(W, "logs"))
    return SmokeLog


def last_run_lines(W, problem="fire"):
    """The log lines of the latest ridge_shap.py run of the problem (lead 0) in the smoke's log folder."""
    p = os.path.join(W, "logs", "ridge_shap_%s_lead0.log" % problem)
    if not os.path.isfile(p):
        return []
    with open(p, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    starts = [i for i, ln in enumerate(lines) if "] ridge SHAP %s lead 0" % problem in ln]
    return lines[starts[-1]:] if starts else lines


GATE_TEXTS = ("a heavy job holds", "another SHAP step is running", "psutil cannot be imported")


def own_refusal(lines, text):
    """The latest run's log shows its own refusal text and no refusal by ridge_shap.py's heavy-job gate."""
    return any(text in ln for ln in lines) and not any(g in ln for ln in lines for g in GATE_TEXTS)


def local_names():
    """The account and host names of this machine (the privacy scan's names; read at run time, never written)."""
    names = {os.path.basename(os.path.expanduser("~")), os.environ.get("COMPUTERNAME") or ""}
    return sorted(n for n in names if n and len(n) >= 3 and n != "~")


def privacy_check(tag, W, real_names=True):
    """The privacy scan of the whole smoke folder at the end of a real step (it writes logs, reports and byte copies
    of board records there): with C.private_names() (this machine's account and host names and the accounts in the
    five runs' recorded machine paths, read from their manifests), or with this machine's names only after a guard
    stop (nothing more is read then). Only the number of names is reported, never a name."""
    names = C.private_names() if real_names else local_names()
    bad, eng = C.privacy_scan(W, names=names)
    ok = not bad and eng == 0
    check("%s: privacy: no account or host name in the smoke folder (%s)" % (
        tag, "the runs' recorded names too" if real_names else "this machine's names; a guard stop"),
        ok, {"files": bad[:5], "engine": eng, "names": len(names)})
    return ok


def crash_scan(s, W, log, exc):
    """The privacy scan after a real step's function crashed: with the runs' recorded names when a heavy-job guard
    check has passed in this step, otherwise (for example Ctrl+C during the first check) with this machine's names
    only, so nothing more is read. No report entry is written after a crash, so the scan's outcome is logged. A scan
    that raises an Exception is logged and never replaces the crash; an interrupt during the scan does."""
    try:
        ok = privacy_check("%s step (crashed: %s)" % (s, type(exc).__name__), W, real_names=bool(GUARD["passed"]))
        log("privacy scan after the crash of step %s: %s" % (s, "clean" if ok else "NAMES FOUND (see the console)"))
    except Exception as scan_exc:
        try:
            log("privacy scan after the crash of step %s could not run: %s" % (s, type(scan_exc).__name__))
        except Exception:
            pass


# ---------------------------------------------------------------------------------------------------------------
# the synthetic boards (no real data)
class FakeRun(object):
    """H.Run for a synthetic world: the links only."""

    def __init__(self, folder):
        w = WORLDS[C.norm(folder)]
        w.calls["run"] += 1
        self.folder, self.links = folder, list(w.links)


class FakeExport(object):
    """H.ExportLead for a synthetic world: the test set (whole, in its read order) and the refit rows of the
    background pool, as the real reader returns them."""

    def __init__(self, folder, lead, run):
        w = WORLDS[C.norm(folder)]
        w.calls["export"] += 1
        if w.flags.get("refuse_export"):
            raise w.H.HarnessRefusal("synthetic: export %s lists a file that is not on disk" % folder)
        self.dir, self.lead, self.run, self.w = folder, int(lead), run, w
        self.features = list(w.feats)
        self.groups = ["g_all"]
        self.content_sha, self.manifest_sha = w.content_sha, w.manifest_sha

    def files_sha(self, part=None):
        return self.w.files_sha

    def read_set(self, name):
        w = self.w
        if name != "test":
            raise w.H.HarnessRefusal("synthetic: only the test set is served")
        w.calls["read_test"] += 1
        X = w.Xt
        if w.flags.get("mutate_reread") and w.calls["read_test"] > w.flags["mutate_reread"]:
            X = w.np.array(w.Xt, order="F", copy=True)
            X[0, 0] = w.np.float32(X[0, 0] + w.np.float32(1.0)) if w.np.isfinite(X[0, 0]) else w.np.float32(1.0)
        return w.K.copy(), None, X, {k: v.copy() for k, v in w.nm.items()}

    def read_table(self, part, stem, columns=None):
        return self.w.train[list(columns)].copy() if columns is not None else self.w.train.copy()


class Patched(object):
    """C.PROBLEMS['fire'] pointed at a synthetic board, the fake readers in, the lock list and the list of other SHAP
    processes replaced (the owner's real runs never enter a synthetic test; all restored on exit)."""

    def __init__(self, S, patch, locks=(), busy=()):
        self.S, self.patch, self.locks, self.busy = S, patch, tuple(locks), list(busy)

    def __enter__(self):
        S = self.S
        self.keep = C.PROBLEMS["fire"]
        self.kr, self.ke, self.kl, self.kb = S.H.Run, S.H.ExportLead, S.RL.LOCKS, S.RL.busy_processes
        C.PROBLEMS["fire"] = dict(self.keep, **self.patch)
        S.H.Run, S.H.ExportLead, S.RL.LOCKS = FakeRun, FakeExport, self.locks
        busy = list(self.busy)
        S.RL.busy_processes = lambda procs=None, skip=None: list(busy)
        return self

    def __exit__(self, *exc):
        S = self.S
        C.PROBLEMS["fire"] = self.keep
        S.H.Run, S.H.ExportLead, S.RL.LOCKS, S.RL.busy_processes = self.kr, self.ke, self.kl, self.kb
        return False


def run_main(S, argv, patch, locks=(), busy=()):
    """ridge_shap.main(argv) in this process on a synthetic board; the exit code."""
    with Patched(S, patch, locks, busy):
        try:
            rc = S.RL.main(list(argv))
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 1
    return rc


def board_fit(S, params, fit, tst, alpha):
    """The board's own fit and scoring (M.fit_predict), its link-space output captured from its _to_y call."""
    M, np = S.M, S.np
    got = []
    orig = M._to_y

    def spy(learner, prm, z0, f):
        got.append(np.array(f, dtype=np.float64, copy=True))
        return orig(learner, prm, z0, f)
    M._to_y = spy
    try:
        res = M.fit_predict("ridge", params, fit, [tst], (alpha,))
    finally:
        M._to_y = orig
    if len(got) != 1:
        raise RuntimeError("the board's scoring called _to_y %d times (one expected)" % len(got))
    return res, got[0]


def make_X(S, n, p, nan_cols=(), const_cols=(), allnan_cols=(), constnan_cols=()):
    np, rng = S.np, S.rng
    scales = np.logspace(-2, 2, p)
    X = (rng.standard_normal((n, p)) * scales[None, :] + rng.standard_normal(p) * scales).astype(np.float32)
    for j in nan_cols:
        X[rng.random(n) < 0.15, j] = np.nan
    for j in const_cols:
        X[:, j] = np.float32(3.5)
    for j in allnan_cols:
        X[:, j] = np.nan
    for j in constnan_cols:                     # constant on its values, NaN elsewhere: value dropped, flag kept
        X[:, j] = np.float32(3.25)
        X[rng.random(n) < 0.2, j] = np.nan
    return np.asfortranarray(X)


def normals_and_y(S, kind, n, signal):
    """(normal in y units, y, link params, legal, links) of a world kind: 'fire' (log_c, c 0.013, ub 1, legal [0, 1]),
    'identity' (NDVI-like: identity, ub 1, legal [-0.2, 1]), 'pm25' (log_c, c 1.5, open upper bound)."""
    np, rng = S.np, S.rng
    s = np.tanh(signal / (np.std(signal) + 1e-12))
    if kind == "fire":
        ny = rng.uniform(0.0, 0.3, n)
        y = np.clip(ny + 0.05 * s + 0.01 * rng.standard_normal(n), 0.0, 1.0)
        return ny, y, {"link": "log_c", "c": CF, "ub": 1.0}, (0.0, 1.0), ["identity", "log_c", "arcsine"]
    if kind == "identity":
        ny = rng.uniform(-0.15, 0.98, n)
        y = np.clip(ny + 0.08 * s + 0.02 * rng.standard_normal(n), -0.2, 1.0)
        return ny, y, {"link": "identity", "c": None, "ub": 1.0}, (-0.2, 1.0), ["identity"]
    ny = rng.uniform(0.0, 40.0, n)
    y = np.maximum(0.0, ny + 5.0 * s + 2.0 * rng.standard_normal(n))
    return ny, y, {"link": "log_c", "c": 1.5, "ub": None}, (0.0, float("inf")), ["identity", "log_c"]


def link_normals(np, params, links, ny):
    out = {}
    for l in links:
        if l == "identity":
            out[l] = np.asarray(ny, np.float64)
        elif l == "log_c":
            out[l] = np.log(np.asarray(ny, np.float64) + float(params["c"]))
        else:
            out[l] = np.arcsin(np.sqrt(np.clip(np.asarray(ny, np.float64), 0.0, 1.0)))
    return out


def test_keys(S, m, units):
    np, pd = S.np, S.pd
    i = np.arange(m)
    u = i % units
    K = pd.DataFrame({"unit": ["u%04d" % k for k in u], "group": ["g%d" % (k % 4) for k in u],
                      "time": (24229 + i // units).astype(np.int64)})
    K["issue"] = K["time"].to_numpy(np.int64)
    K["lead"] = np.zeros(m, np.int64)
    return K


def finish_world(S, w, res, f, ny_t):
    """The board's saved records of a fitted world: the saved pre and raw (in the saved order: rows reversed), the
    model through JSON, the pick, the fit info."""
    np = S.np
    w.pre = np.asarray(res["test"][w.alpha]["pre"], np.float64)
    w.raw = S.clip(np.asarray(w.pre, np.float64), w.legal, False)[0]
    w.f = f
    w.mj = json.loads(json.dumps(res.model, allow_nan=False))
    w.info = dict(res.info)
    w.label = S.H.ck_label(float(w.alpha))
    order = np.arange(len(w.K))[::-1]
    P = w.K.iloc[order].reset_index(drop=True).copy()
    P["pre__rival_ridge"] = w.pre[order]
    P["arm__rival_ridge_raw"] = w.raw[order]
    P["arm__rival_ridge"] = w.raw[order]
    P["guard_passed"] = False
    w.preds = P
    w.ny_t = ny_t
    return w


def fit_world(S, name, m_test, n_fit, p, nan_cols, const_cols, allnan_cols, constnan_cols, alpha, kind, units=240):
    np, M = S.np, S.M
    feats = ["x__f%02d" % j for j in range(p)]
    Xf = make_X(S, n_fit, p, nan_cols, const_cols, allnan_cols, constnan_cols)
    Xt = make_X(S, m_test, p, nan_cols, const_cols, allnan_cols, constnan_cols)
    wsig = S.rng.standard_normal(p) / np.logspace(-2, 2, p)
    sig = np.nan_to_num(Xf.astype(np.float64)) @ wsig
    nyf, y, params, legal, links = normals_and_y(S, kind, n_fit, sig)
    ny_t = normals_and_y(S, kind, m_test, np.nan_to_num(Xt.astype(np.float64)) @ wsig)[0]
    nmf, nmt = link_normals(np, params, links, nyf), link_normals(np, params, links, ny_t)
    fit = M.FitData(name="fit", X=Xf, columns=tuple(feats), y=y, normal=nmf)
    tst = M.ScoreData(name="test", X=Xt, normal=nmt)
    res, f = board_fit(S, params, fit, tst, alpha)
    w = SimpleNamespace(name=name, kind=kind, feats=feats, Xt=Xt, K=test_keys(S, m_test, units), nm=nmt,
                        params=params, legal=legal, links=links, alpha=alpha, wsig=wsig, np=np, H=S.H,
                        calls={"run": 0, "export": 0, "read_test": 0}, flags={})
    return finish_world(S, w, res, f, ny_t)


def add_pool(S, w, n_pool, n_expl, per_row):
    """A background pool of refit rows and a sample of explained rows with per_row background rows each."""
    np, pd, rng = S.np, S.pd, S.rng
    p = len(w.feats)
    nan_cols = [j for j in range(p) if np.isnan(w.Xt[:, j]).any()]
    Xb = make_X(S, n_pool, p, [j for j in nan_cols if not np.isnan(w.Xt[:, j]).all()], [], [], [])
    for j in range(p):                           # constant and all-NaN columns as in the test set
        col = w.Xt[:, j]
        fin = col[np.isfinite(col)]
        if fin.size == 0:
            Xb[:, j] = np.nan
        elif np.all(fin == fin[0]):
            Xb[:, j] = np.where(rng.random(n_pool) < 0.2, np.nan, fin[0]).astype(np.float32) \
                if np.isnan(col).any() else fin[0]
    w.Xb = np.asfortranarray(Xb)
    ny_b = normals_and_y(S, w.kind, n_pool, np.nan_to_num(Xb.astype(np.float64)) @ w.wsig)[0]
    w.nmb = link_normals(np, w.params, w.links, ny_b)
    w.epos = np.sort(rng.choice(len(w.K), size=n_expl, replace=False)).astype(np.int64)
    w.bg = [np.sort(rng.choice(n_pool, size=per_row, replace=False)).astype(np.int64) for _ in range(n_expl)]
    return pool_frames(S, w)


def pool_frames(S, w):
    """The refit-row table of the pool (keys, flags, y, features, normals) and the sample and background frames."""
    np, pd = S.np, S.pd
    n_pool = w.Xb.shape[0]
    T = pd.DataFrame({"unit": ["p%04d" % k for k in range(n_pool)], "group": ["g%d" % (k % 4) for k in range(n_pool)],
                      "time": (24000 + np.arange(n_pool)).astype(np.int64)})
    T["issue"] = T["time"].to_numpy(np.int64)
    T["lead"] = np.zeros(n_pool, np.int64)
    for fl in S.H.FLAGS:
        T[fl] = np.zeros(n_pool, bool)
    T["r_refit"] = np.ones(n_pool, bool)
    T["y"] = np.zeros(n_pool)
    for j, c in enumerate(w.feats):
        T[c] = w.Xb[:, j]
    for l, v in w.nmb.items():
        T["nfit__" + l] = v
    w.train = T
    Ke = w.K.iloc[w.epos].reset_index(drop=True)
    w.S_df = pd.DataFrame({"row": np.arange(len(w.epos), dtype=np.int64), "unit": Ke["unit"].to_numpy(),
                           "group": Ke["group"].to_numpy(), "time": Ke["time"].to_numpy(np.int64),
                           "year": (2020 + (Ke["time"].to_numpy(np.int64) - 24229) // 12).astype(np.int64)})
    rows = []
    for i, lst in enumerate(w.bg):
        for q in lst:
            rows.append((i, T["unit"].iloc[q], int(T["time"].iloc[q])))
    w.B_df = pd.DataFrame(rows, columns=["row", "unit", "time"])
    w.B_df["row"] = w.B_df["row"].astype(np.int64)
    w.B_df["time"] = w.B_df["time"].astype(np.int64)
    return w


def small_world(S, name, kind):
    """The 7-player world (rival_shap.py's T5 cases) for brute force through main()."""
    np, M, rng = S.np, S.M, S.rng
    feats = ["x__a_lag1", "x__a_lag2", "x__b", "x__c", "c__ctx:top5:b", "x__k", "x__z"]
    sc = np.array([1.0, 2.0, 0.5, 3.0, 1.0, 0.1, 1.0])

    def X_of(n):
        X = (rng.standard_normal((n, 7)) * sc).astype(np.float32)
        X[:, 6] = np.float32(2.0)                          # constant: dropped by the fit
        X[rng.random(n) < 0.2, 1] = np.nan                 # the flags of x__a_lag2 and x__c
        X[rng.random(n) < 0.2, 3] = np.nan
        X[:, 4] = X[:, 2]                                  # the exact copy of x__b
        return X
    nf, nt, nb = 3000, 400, 80
    Xf, Xt, Xb = X_of(nf), X_of(nt), X_of(nb)
    wsig = np.array([0.3, -0.2, 0.5, 0.1, 0.0, 0.4, 0.0])
    nyf, y, params, legal, links = normals_and_y(S, kind, nf, np.nan_to_num(Xf.astype(np.float64)) @ wsig)
    ny_t = normals_and_y(S, kind, nt, np.nan_to_num(Xt.astype(np.float64)) @ wsig)[0]
    ny_b = normals_and_y(S, kind, nb, np.nan_to_num(Xb.astype(np.float64)) @ wsig)[0]
    epos = np.array([3, 17, 42, 99, 150, 222, 301, 377], np.int64)
    free = list(rng.permutation(nb))
    bg = []
    for k in (5, 6, 7, 8, 9, 5, 6, 7):                    # disjoint background rows per explained row
        bg.append(np.sort(np.asarray(free[:k], np.int64)))
        free = free[k:]
    Xt[epos[0], 1], Xt[epos[0], 3] = np.float32(0.7), np.float32(-0.4)     # row 0: all finite on x and its b
    for q in bg[0]:
        Xb[q, 1], Xb[q, 3] = np.float32(0.1), np.float32(0.2)
    Xt[epos[1], 1] = np.nan                                                 # row 1: a flag on x only
    for q in bg[1]:
        if np.isnan(Xb[q, 1]):
            Xb[q, 1] = np.float32(0.3)
    Xt[epos[2], 3] = np.float32(1.5)                                        # row 2: a flag on one b only
    Xb[bg[2], 3] = np.float32(0.25)
    Xb[bg[2][0], 3] = np.nan
    for q in bg[3]:                                                         # row 3: x__b and its copy equal on every b
        Xb[q, 2] = Xb[q, 4] = Xt[epos[3], 2]
    for q in bg[4]:                                                         # row 4: the normal equal on every b
        ny_b[q] = ny_t[epos[4]]
    nmf, nmt, nmb = (link_normals(np, params, links, v) for v in (nyf, ny_t, ny_b))
    fit = M.FitData(name="fit", X=np.asfortranarray(Xf), columns=tuple(feats), y=y, normal=nmf)
    tst = M.ScoreData(name="test", X=np.asfortranarray(Xt), normal=nmt)
    res, f = board_fit(S, params, fit, tst, 1.0)
    w = SimpleNamespace(name=name, kind=kind, feats=feats, Xt=np.asfortranarray(Xt), K=test_keys(S, nt, 40), nm=nmt,
                        params=params, legal=legal, links=links, alpha=1.0, wsig=wsig, np=np, H=S.H,
                        calls={"run": 0, "export": 0, "read_test": 0}, flags={})
    finish_world(S, w, res, f, ny_t)
    w.Xb, w.nmb, w.epos, w.bg = np.asfortranarray(Xb), nmb, epos, bg
    return pool_frames(S, w)


def write_sample(S, sroot, S_df, B_df, n, register=True):
    C.makedirs(sroot)
    sp = C.write_parquet(os.path.join(sroot, "sample.parquet"), S_df)
    bp = C.write_parquet(os.path.join(sroot, "background_lead_0.parquet"), B_df)
    C.write_json(os.path.join(sroot, "sample_manifest.json"), {"problem": "fire", "n": int(n), "n_asked": int(n),
                                                               "defo_regions": 0, "tag": "smoke"})
    reg = os.path.join(sroot, "SAMPLE_REGISTER.txt")
    line = "%s problem=fire tag=smoke leads=0 n=%d defo_regions=0 sample=%s background_lead_0.parquet=%s\n" % (
        datetime.datetime.now().isoformat(timespec="seconds"), int(n), C.sha256_file(sp), C.sha256_file(bp))
    with open(C.assert_writable(reg), "w", encoding="utf-8") as fh:
        fh.write(line if register else "")
    return reg


def synth_board(S, base, w, guard_passed=False, change=None, sample=None):
    """A synthetic board tree for ridge_shap.main(): board.json, picks.json, lead_0 records (done, model, preds,
    export.json), an export lead manifest with one test file (compare_shap.py's global_columns reads it), a run
    folder, the sample with its own register; every record consistent unless change(name, record) alters one.
    Returns (the PROBLEMS patch, the sample root, the register)."""
    np = S.np
    if os.path.isdir(base):
        shutil.rmtree(C.assert_writable(base))
    change = change or (lambda what, rec: rec)
    bdir, run_dir = C.makedirs(os.path.join(base, "board")), C.makedirs(os.path.join(base, "run"))
    edir = C.makedirs(os.path.join(base, "export", "lead_0"))
    w.content_sha, w.files_sha, w.manifest_sha = ("synthetic-%s-%s" % (k, w.name) for k in ("content", "files",
                                                                                             "manifest"))
    tcols = w.K[["unit", "time"]].copy()
    for j, c in enumerate(w.feats):
        tcols[c] = w.Xt[:, j]
    C.write_parquet(os.path.join(edir, "test", "g_all.parquet"), tcols)
    C.write_json(os.path.join(edir, "export_manifest.json"), change("export_manifest", {
        "lead": 0, "files": [{"part": "test", "group": "g_all", "path": "test/g_all.parquet", "sha256": "synthetic"}]}))
    WORLDS[C.norm(run_dir)] = w
    WORLDS[C.norm(edir)] = w
    have = C.versions()
    legal_rec = [w.legal[0], None if w.legal[1] == float("inf") else w.legal[1]]
    board = {"format": "rivals-board/1", "harness_code_sha256": S.H.harness_code_sha(),
             "engine": {"live_file_sha": S.H.engine_file_sha()}, "versions": {k: have[k] for k in VERSION_KEYS},
             "threads": 8, "threadpool_info": [list(NUMPY_POOL_ROW), ["openmp", "openmp", "vcomp", 8]],
             "run": {"c": {"0": w.params["c"]}, "ub": w.params["ub"], "legal": legal_rec, "links": list(w.links)},
             "export": {"lead_0": {"dir": edir, "content_sha256": w.content_sha, "files_sha256": w.files_sha,
                                   "manifest_sha256": w.manifest_sha}}}
    C.write_json(os.path.join(bdir, "board.json"), change("board", board))
    pick = {"checkpoint": repr(float(w.alpha)), "extended": False, "extension_trials": [], "flags": [],
            "link": w.params["link"], "setting": {}, "trial_id": "ridge__%s__alphas" % w.params["link"]}
    C.write_json(os.path.join(bdir, "picks.json"), change("picks", {"picks": {"ridge": pick}}))
    ldir = C.makedirs(os.path.join(bdir, "lead_0"))
    C.write_json(os.path.join(ldir, "model_ridge.json"), change("model", copy.deepcopy(w.mj)))
    pp = C.write_parquet(os.path.join(ldir, "preds_ridge.parquet"), change("preds", w.preds.copy()))
    C.write_json(os.path.join(ldir, "export.json"), change("export.json", {
        "lead": 0, "export_dir": edir, "export_content_sha256": w.content_sha, "export_files_sha256": w.files_sha,
        "picks_sha256": "synthetic"}))
    names = list(w.mj["names"])
    C.write_json(os.path.join(ldir, "done_ridge.json"), change("done", {
        "hash": "synthetic", "lead": 0, "learner": "ridge", "model_file": "model_ridge.json", "pick": pick,
        "pinned": w.label, "preds_sha256": C.sha256_file(pp), "test_rows": int(len(w.K)),
        "fit_info": {"design_columns": len(names), "flag_columns": len([n for n in names if n.startswith("missing__")]),
                     "dropped_columns": list(w.mj["dropped"]), "n_fit": int(w.info.get("n_fit", 0))},
        "guard": {"passed": bool(guard_passed), "rows": 1, "comparator": "synthetic", "rival_mae": 1.0,
                  "comparator_mae": 1.0, "source": "synthetic"}}))
    S_df, B_df = (sample if sample is not None else (w.S_df, w.B_df))
    sroot = os.path.join(base, "sample")
    reg = write_sample(S, sroot, S_df, B_df, len(S_df))
    return {"board": bdir, "run": run_dir, "export": os.path.dirname(edir)}, sroot, reg


def argv_of(W, sroot, reg, models, n, *extra):
    """ridge_shap.py's arguments on a synthetic board (n None leaves --n out: the registered N)."""
    return (["--problem", "fire", "--lead", "0"] + ([] if n is None else ["--n", str(n)])
            + ["--sample-root", sroot, "--register", reg, "--out-root", models, "--log-dir", os.path.join(W, "logs")]
            + list(extra))


def nbits(np, a, b):
    a, b = np.ascontiguousarray(a, np.float64), np.ascontiguousarray(b, np.float64)
    return int(np.count_nonzero(a.view(np.uint64) != b.view(np.uint64)))


def rival_way(S, w, ar):
    """rival_shap.py:339-345 (its own ridge_design, one row-ordered array, then 65,536-row slices)."""
    np, M = S.np, S.M
    cf = SimpleNamespace(ex=SimpleNamespace(features=w.feats))
    Z, _ = S.RS.ridge_design(cf, w.mj, w.Xt, ar.scn)
    outv = np.empty(Z.shape[0])
    for a0 in range(0, Z.shape[0], M.RIDGE_BLOCK_ROWS):
        b0 = min(Z.shape[0], a0 + M.RIDGE_BLOCK_ROWS)
        outv[a0:b0] = ar.tbar + Z[a0:b0] @ ar.coef
    return outv, bool(Z.flags["C_CONTIGUOUS"])


def exact_of(S, w, mj=None, X=None, preds=None, threads=8):
    return S.RL.exactness(w.mj if mj is None else mj, w.params, w.label, w.legal, threads, w.feats, w.K,
                          w.Xt if X is None else X, w.nm, w.preds if preds is None else preds, also_c=True)


# ---------------------------------------------------------------------------------------------------------------
def s1_exactness(S, log):
    np, M, RL, RS = S.np, S.M, S.RL, S.RS
    import threadpoolctl
    w = fit_world(S, "w1", 91440, 70000, 40, list(range(0, 24, 2)), [30], [31], [32], 10.0, "fire")
    S.w1 = w
    m = len(w.K)
    rec, ar = exact_of(S, w)
    check("S1 board's scoring reproduces pre and raw on every row (91,440; 2 blocks; key-joined)",
          rec["pass"] and rec["bit_equal_rows"] == m and rec["raw"]["bit_equal_rows"] == m
          and rec["keys_only_saved"] == 0 and rec["keys_only_test"] == 0,
          {k: rec.get(k) for k in ("bit_equal_rows", "rows_finite", "pass", "design_columns", "flags", "dropped")})
    check("S1 the loader's link-space output = the board's own (its _to_y f), bit for bit",
          RL.same_bits(ar.out, w.f), {"rows_differing": nbits(np, ar.out, w.f)})
    blocks = rec["blocks"]
    check("S1 blocks [0, 65536) and [65536, 91440), both stored column by column (F)",
          [b["rows"] for b in blocks] == [[0, 65536], [65536, 91440]] and all(b["F"] and not b["C"] for b in blocks),
          [(b["rows"], b["C"], b["F"]) for b in blocks])
    outv, zc = rival_way(S, w, ar)
    out2, out_c, _, _ = RL.board_scores(ar.d, ar.mu, ar.tbar, ar.coef, w.Xt, ar.scn, also_c=True)
    rv = RS.bit_check(np.asarray(M._to_y("ridge", w.params, ar.sz0, outv), np.float64), w.pre)
    rb = rec["row_by_row_copy"]
    check("S1 the row-by-row copy (information) is rival_shap.py's way exactly and misses rows",
          zc and RL.same_bits(out_c, outv) and rb["bit_equal_rows"] == rv["bit_equal_rows"] and rb["bit_equal_rows"] < m
          and not rb["pass"], {"row_by_row_bit_equal": rb["bit_equal_rows"], "rival_shap_way": rv["bit_equal_rows"],
                               "link_space_rows_differing": rb["link_space_rows_differing_from_the_board_way"]})
    rc2, ar2 = exact_of(S, w, X=np.ascontiguousarray(w.Xt))
    check("S1 a C-ordered X gives the same link-space output", rc2["pass"] and RL.same_bits(ar2.out, ar.out),
          nbits(np, ar2.out, ar.out))
    keep = M.RIDGE_BLOCK_ROWS
    for name, rows in (("one call for the whole test set", m), ("50,000-row blocks", 50000)):
        M.RIDGE_BLOCK_ROWS = rows
        try:
            r3, a3 = exact_of(S, w)
        finally:
            M.RIDGE_BLOCK_ROWS = keep
        nd = nbits(np, a3.out, w.f)
        check("S1 mutation caught in link space: %s" % name, nd > 0,
              {"link_space_rows_differing": nd, "pre_still_passes": r3["pass"]})
    with threadpoolctl.threadpool_limits(limits=1, user_api="blas"):
        r4, a4 = exact_of(S, w, threads=1)
    nd = nbits(np, a4.out, w.f)
    pos = np.flatnonzero(np.ascontiguousarray(a4.out).view(np.uint64) != np.ascontiguousarray(w.f).view(np.uint64))
    check("S1 mutation caught in link space: 1 BLAS thread", nd > 0,
          {"link_space_rows_differing": nd, "pre_still_passes": r4["pass"], "first_rows": pos[:8].tolist()})
    mj2 = copy.deepcopy(w.mj)
    mj2["coef"][w.label] = [v * (1.0 + 1e-12) for v in mj2["coef"][w.label]]
    r5, _ = exact_of(S, w, mj=mj2)
    wd = r5.get("where_rows_differ") or {}
    check("S1 a coefficient vector scaled by 1 + 1e-12 fails, with where_rows_differ",
          not r5["pass"] and wd.get("rows_differing", 0) > 0 and len(wd.get("first", [])) > 0,
          {"bit_equal_rows": r5["bit_equal_rows"], "rows_differing": wd.get("rows_differing")})
    p6 = w.preds.copy()
    k = p6.index[7]
    p6.loc[k, "arm__rival_ridge_raw"] = np.nextafter(float(p6.loc[k, "arm__rival_ridge_raw"]), np.inf)
    r6, _ = exact_of(S, w, preds=p6)
    check("S1 one saved raw value moved by 1 ulp fails raw only",
          not r6["pass"] and r6["bit_equal_rows"] == m and not r6["raw"]["pass"]
          and r6["raw"]["bit_equal_rows"] == m - 1, {"pre": r6["bit_equal_rows"], "raw": r6["raw"]["bit_equal_rows"]})
    w2 = fit_world(S, "w2", 70000, 20000, 30, [], [7], [], [], 1.0, "fire")
    S.w2 = w2                                    # S5b: rival_shap.py's own piece on a no-flag board
    r7, a7 = exact_of(S, w2)
    outv2, _ = rival_way(S, w2, a7)
    rv2 = RS.bit_check(np.asarray(M._to_y("ridge", w2.params, a7.sz0, outv2), np.float64), w2.pre)
    check("S1 no flags: blocks stored row by row (C), and rival_shap.py's way passes (coral's case)",
          r7["pass"] and r7["flags"] == 0 and all(b["C"] for b in r7["blocks"]) and rv2["pass"]
          and RL.same_bits(a7.out, w2.f), {"blocks": [(b["rows"], b["C"], b["F"]) for b in r7["blocks"]],
                                           "rival_shap_way_bit_equal": rv2["bit_equal_rows"]})
    for kind, tag in (("identity", "identity link, ub 1, legal [-0.2, 1] (NDVI-like)"),
                      ("pm25", "log_c, c 1.5, legal [0, open] (PM2.5-like)")):
        wk = fit_world(S, "w_" + kind, 70000, 30000, 24, [0, 3, 5, 9], [11], [], [13], 100.0, kind)
        rk, ak = exact_of(S, wk)
        check("S1 %s: pre and raw on every row, link space equal, rows clipped" % tag,
              rk["pass"] and rk["raw"]["pass"] and RL.same_bits(ak.out, wk.f) and rk["rows_clipped"] > 0
              and all(b["F"] for b in rk["blocks"]), {"rows": rk["rows"], "rows_clipped": rk["rows_clipped"],
                                                      "legal": rk["legal"]})
    mj8 = copy.deepcopy(w.mj)
    mj8["coef"][w.label][0] = float("inf")
    with np.errstate(all="ignore"):
        r8, a8 = exact_of(S, w, mj=mj8)
    check("S1 an infinite coefficient: an S-EXACT refusal recorded (stage bits), not a crash",
          not r8["pass"] and r8.get("stage") == "bits" and "refusal" in r8 and a8 is None, r8.get("refusal"))


def brute_check(S, w, rows, meta):
    """phi and phiv of rows.parquet against brute-force Shapley values of the model's own function (the design block
    of each hybrid row, its offset included), at both levels; (max |phi - bf|, max |phiv - bf|)."""
    np, M, TS, RL = S.np, S.M, S.TS, S.RL
    d, mu, _ = RL.design_of(w.feats, w.mj)
    coef = np.asarray(w.mj["coef"][w.label], np.float64)
    tbar = float(w.mj["intercept"])
    p = len(w.feats)
    link = w.params["link"]
    players, variables, vmap = meta["players"], meta["variables"], meta["variable_map"]
    merged = meta.get("duplicates_merged") or {}
    poc = np.asarray([players.index(merged.get(f, f)) for f in w.feats] + [players.index("normal")], np.int64)
    pocv = np.asarray([variables.index(vmap[players[q]]) for q in poc], np.int64)

    def f(R):
        R = np.asarray(R, np.float64)
        z = R[:, p]
        Z = M.RidgeDesign.block(d, R[:, :p], z) - mu[None, :]
        return z + (tbar + Z @ coef)
    wf = wv = 0.0
    for i in range(len(w.epos)):
        x = np.r_[w.Xt[w.epos[i]].astype(np.float64), w.nm[link][w.epos[i]]]
        lst = w.bg[i]
        BG = np.c_[w.Xb[lst].astype(np.float64), w.nmb[link][lst]]
        wts = np.full(len(lst), 1.0 / len(lst))
        bf = TS.brute_force(f, x, BG, wts, poc, len(players))
        bfv = TS.brute_force(f, x, BG, wts, pocv, len(variables))
        r = rows[rows["row"] == i]
        wf = max(wf, float(np.abs(bf - r[["phi__" + q for q in players]].to_numpy(np.float64)[0]).max()))
        wv = max(wv, float(np.abs(bfv - r[["phiv__" + v for v in variables]].to_numpy(np.float64)[0]).max()))
    return wf, wv


def piece(S, folder):
    pq = S.RS.pq
    return (pq.read_table(os.path.join(folder, "rows.parquet")).to_pandas(),
            C.read_json(os.path.join(folder, "meta.json")), C.read_json(os.path.join(folder, "rows.parquet.done.json")))


def s2_main(S, W, root, log):
    np, RL = S.np, S.RL
    w = small_world(S, "w5", "fire")
    S.w5 = w
    patch, sroot, reg = synth_board(S, os.path.join(root, "s2", "board_fire"), w, guard_passed=False)
    S.s2 = (patch, sroot, reg)
    models = os.path.join(root, "s2", "models")
    out = os.path.join(models, "rival_ridge")
    C.write_json(os.path.join(out, "exactness.json"), {"bit_equal_rows": 395, "pass": False, "rows": 400,
                                                       "rows_finite": 400, "note": "planted: rival_shap.py's record"})
    planted = C.sha256_file(os.path.join(out, "exactness.json"))
    calls0 = dict(w.calls)
    rc = run_main(S, argv_of(W, sroot, reg, models, len(w.epos)), patch)
    files = sorted(os.listdir(out))
    check("S2 main() exit 0 and every file written", rc == 0 and files == sorted([
        "background_keys.parquet", "exactness.json", "meta.json", "ridge_shap_exactness.json", "rows.parquet",
        "rows.parquet.done.json"]), [rc, files])
    if rc != 0:
        return
    rows, meta, done = piece(S, out)
    wf, wv = brute_check(S, w, rows, meta)
    check("S2 phi within 1e-12 of brute-force Shapley values, feature and variable level", wf <= 1e-12 and wv <= 1e-12,
          {"feature": wf, "variable": wv})
    check("S2 additivity <= 1e-12 at both levels; 0 S-ZERO violations; the copy merged into one player",
          meta["max_abs_additivity_error"] <= 1e-12 and meta["max_abs_additivity_error_variable"] <= 1e-12
          and meta["structural_zero_violations"] == 0 and meta.get("duplicates_merged") == {"c__ctx:top5:b": "x__b"}
          and "c__ctx:top5:b" not in meta["players"],
          {k: meta.get(k) for k in ("max_abs_additivity_error", "max_abs_additivity_error_variable",
                                    "structural_zero_violations", "duplicates_merged")})
    link = w.params["link"]
    z0e = w.nm[link][w.epos]
    em = rows.sort_values("row")["eta_model"].to_numpy(np.float64)
    pr = rows.sort_values("row")["pre"].to_numpy(np.float64)
    check("S2 eta_model = the board's link value at the explained rows; pre = the saved pre, bit for bit",
          RL.same_bits(em, z0e + w.f[w.epos]) and RL.same_bits(pr, w.pre[w.epos]),
          {"eta_model_rows_differing": nbits(np, em, z0e + w.f[w.epos]), "pre_rows_differing": nbits(np, pr,
                                                                                                    w.pre[w.epos])})
    ev, evb = meta.get("max_abs_evaluator_minus_model"), meta.get("max_abs_background_evaluator_minus_model")
    check("S2 both evaluator maxima are numbers <= 1e-12 (explained and background)",
          isinstance(ev, float) and isinstance(evb, float) and ev <= 1e-12 and evb <= 1e-12, [ev, evb])
    phi_z = rows["phi__x__z"].to_numpy(np.float64)
    r3 = rows[rows["row"] == 3]
    r4 = rows[rows["row"] == 4]
    check("S2 S-ZERO cases: the dropped constant, x__b equal on every b, the equal normal: exactly 0",
          bool((phi_z == 0).all()) and float(r3["phi__x__b"].iloc[0]) == 0.0
          and float(r4["phi__normal"].iloc[0]) == 0.0, [float(abs(phi_z).max()), float(r3["phi__x__b"].iloc[0]),
                                                        float(r4["phi__normal"].iloc[0])])
    ex = C.read_json(os.path.join(out, "ridge_shap_exactness.json"))
    check("S2 meta: link key, guard declined, method, script, model value, exactness record",
          meta.get("link_key") == "log_c|c=0.012987012987|ub=1" and meta["guard"]["passed"] is False
          and meta.get("method") == "exact linear SHAP; a missing flag folds into its column"
          and meta.get("script") == "ridge_shap.py" and meta.get("exactness_file") == "ridge_shap_exactness.json"
          and meta.get("exactness", {}).get("pass") is True and ex.get("pass") is True
          and meta.get("explained_design_equal_board_blocks") is True and "model_value" in meta,
          {k: meta.get(k) for k in ("link_key", "script", "exactness_file")})
    check("S2 the done record names the script and the sample; rival_shap.py's exactness.json untouched",
          done.get("script") == "ridge_shap.py" and done.get("sample_sha256") == meta["sample_sha256"]
          and C.sha256_file(os.path.join(out, "exactness.json")) == planted
          and ex.get("rival_shap_exactness_json", {}).get("bit_equal_rows") == 395,
          {"script": done.get("script"), "rival_shap_record": ex.get("rival_shap_exactness_json")})
    check("S2 the real load_context ran on the fake readers (export opened twice, the test set read twice)",
          w.calls["export"] - calls0["export"] == 2 and w.calls["read_test"] - calls0["read_test"] == 2,
          {k: w.calls[k] - calls0[k] for k in w.calls})
    for kind, key in (("identity", "identity|c=-|ub=1"), ("pm25", "log_c|c=1.5|ub=-")):
        wk = small_world(S, "w5_" + kind, kind)
        pk, sk, rk = synth_board(S, os.path.join(root, "s2", "board_" + kind), wk, guard_passed=True)
        mk = os.path.join(root, "s2", "models_" + kind)
        rck = run_main(S, argv_of(W, sk, rk, mk, len(wk.epos)), pk)
        ok = rck == 0
        val = [rck]
        if ok:
            rws, mt, _ = piece(S, os.path.join(mk, "rival_ridge"))
            bf = brute_check(S, wk, rws, mt)
            pr = rws.sort_values("row")["pre"].to_numpy(np.float64)
            ok = (mt.get("link_key") == key and max(bf) <= 1e-12 and RL.same_bits(pr, wk.pre[wk.epos])
                  and mt["guard"]["passed"] is True)
            val = {"link_key": mt.get("link_key"), "brute": bf}
        check("S2 %s world through main(): exit 0, link key %s, brute force, pre = saved pre" % (kind, key), ok, val)


def s3_big(S, W, root, log):
    np = S.np
    w = add_pool(S, S.w1, 200, 50, 4)
    patch, sroot, reg = synth_board(S, os.path.join(root, "s3", "board"), w, guard_passed=True)
    S.s3 = (patch, sroot, reg)                   # S5b: a rival_shap.py re-run beside this script's piece
    models = os.path.join(root, "s3", "models")
    out = os.path.join(models, "rival_ridge")
    rc = run_main(S, argv_of(W, sroot, reg, models, None), patch)
    files = sorted(os.listdir(out)) if os.path.isdir(out) else []
    lines = last_run_lines(W)
    check("S3 main() on the 91,440-row world (50 explained rows, --n left out): exit 0, every file, registered N used",
          rc == 0 and files == sorted(["background_keys.parquet", "meta.json", "ridge_shap_exactness.json",
                                       "rows.parquet", "rows.parquet.done.json"])
          and any("sample: registered (tag smoke, N 50)" in ln for ln in lines), [rc, files])
    if rc != 0:
        return
    rows, meta, _ = piece(S, out)
    em = rows.sort_values("row")["eta_model"].to_numpy(np.float64)
    link = w.params["link"]
    check("S3 checks passed; eta_model the board's value; evaluator maxima <= 1e-12",
          meta["pass"] and RL_same(S, em, w.nm[link][w.epos] + w.f[w.epos])
          and meta["max_abs_evaluator_minus_model"] <= 1e-12
          and meta["max_abs_background_evaluator_minus_model"] <= 1e-12,
          {k: meta.get(k) for k in ("max_abs_evaluator_minus_model", "max_abs_background_evaluator_minus_model",
                                    "players_nonzero")})
    t0 = tree_state(out)
    rc2 = run_main(S, argv_of(W, sroot, reg, models, 50), patch)
    lines = last_run_lines(W)
    check("S3 a rerun with --n 50 (the registered N) is skipped and changes no file", rc2 == 0 and tree_state(out) == t0
          and any("skipped" in ln for ln in lines) and any("--n equal" in ln for ln in lines), [rc2] + lines[-2:])
    fresh = os.path.join(root, "s3", "exact_only")
    rc3 = run_main(S, argv_of(W, sroot, reg, fresh, 50, "--exactness-only"), patch)
    got = tree_state(fresh)
    check("S3 --exactness-only into a fresh root writes ridge_shap_exactness.json only",
          rc3 == 0 and sorted(got) == ["rival_ridge/ridge_shap_exactness.json"], [rc3, sorted(got)])


def RL_same(S, a, b):
    return S.RL.same_bits(S.np.asarray(a, S.np.float64), S.np.asarray(b, S.np.float64))


def good_piece(S, W, models, patch, sroot, reg, n):
    """A finished piece of this script in models (for the stop tests that must remove, or keep, its done record)."""
    rc = run_main(S, argv_of(W, sroot, reg, models, n), patch)
    return rc == 0 and os.path.isfile(os.path.join(models, "rival_ridge", "rows.parquet.done.json"))


def s4_gates(S, W, root, log):
    np, RL, RS, H = S.np, S.RL, S.RS, S.H
    import threadpoolctl
    w = S.w5
    patch, sroot, reg = S.s2
    n = len(w.epos)
    base = os.path.join(root, "s4")

    def case(name, change=None, sample=None, gp=False):
        return synth_board(S, os.path.join(base, "board_" + name), w, guard_passed=gp, change=change, sample=sample)

    def stop_case(title, name, gate, change=None, argv_extra=(), sample=None, need_done_gone=True, stage=None,
                  pre=None, reg_override=None):
        pk, sk, rk = case(name, change=change, sample=sample)
        models = os.path.join(base, "models_" + name)
        had = good_piece(S, W, models, patch, sroot, reg, n)
        if pre is not None:
            pre()
        try:
            rc = run_main(S, argv_of(W, sk, reg_override or rk, models, n, *argv_extra), pk)
        finally:
            w.flags.clear()
        out = os.path.join(models, "rival_ridge")
        got = failed_gate(out)
        ok = rc == 3 and (got == gate or (isinstance(got, list) and gate in got))
        done_gone = not os.path.isfile(os.path.join(out, "rows.parquet.done.json"))
        ok = ok and had and (done_gone or not need_done_gone)
        val = {"exit": rc, "gate": got, "done_record_removed": done_gone, "had_piece": had}
        if stage is not None:
            ex = C.read_json(os.path.join(out, "ridge_shap_exactness.json"))
            val["stage"] = ex.get("stage")
            ok = ok and ex.get("stage") == stage and ex.get("pass") is False
        check("S4 %s: exit 3, FAILED.json %s%s, no done record" % (title, gate, (", stage " + stage) if stage else ""),
              ok, val)
        return val

    def scale(what, rec):
        if what == "model":
            rec["coef"][w.label] = [v * (1.0 + 1e-12) for v in rec["coef"][w.label]]
        return rec
    stop_case("S-EXACT, a coefficient vector scaled by 1 + 1e-12", "scaled", "S-EXACT", scale, stage="bits")

    def raw_ulp(what, rec):
        if what == "preds":
            k = rec.index[3]
            rec.loc[k, "arm__rival_ridge_raw"] = np.nextafter(float(rec.loc[k, "arm__rival_ridge_raw"]), np.inf)
        return rec
    stop_case("S-EXACT, a saved raw value moved by 1 ulp", "raw_ulp", "S-EXACT", raw_ulp, stage="bits")

    def bad_sha(what, rec):
        if what == "done":
            rec["preds_sha256"] = "0" * 64
        return rec
    stop_case("S-EXACT, a wrong preds_sha256 in done_ridge.json", "bad_sha", "S-EXACT", bad_sha, stage="inputs")
    stop_case("S-EXACT, the export refuses (HarnessRefusal)", "export_refusal", "S-EXACT", stage="inputs",
              pre=lambda: w.flags.update(refuse_export=True))

    def inf_coef(what, rec):
        if what == "model":
            rec["coef"][w.label][0] = float("inf")
        return rec
    with np.errstate(all="ignore"):
        stop_case("S-EXACT, an infinite coefficient (the engine's refusal)", "inf_coef", "S-EXACT", inf_coef,
                  stage="bits")
    stop_case("S-EXACT, the test set changes before load_context reads it", "reread", "S-EXACT", stage="reread",
              pre=lambda: w.flags.update(mutate_reread=w.calls["read_test"] + 1))
    orig_scores = RL.board_scores
    for mode, title, gate, stage in (("repeat", "S-EXACT, a repeat scoring that differs in one row", "S-EXACT",
                                      "repeat"),
                                     ("kept", "S-EVAL, a board design row moved by 1 ulp", "S-EVAL", None),
                                     ("bg", "S-EVAL, a background model value moved by 1e-6", "S-EVAL", None)):
        calls = {"n": 0}

        def patched(*args, **kw):
            calls["n"] += 1
            o, oc, bl, kp = orig_scores(*args, **kw)
            if mode == "repeat" and calls["n"] == 2:
                o = o.copy()
                o[0] = np.nextafter(o[0], np.inf)
            if mode == "kept" and calls["n"] == 2 and kp is not None:
                kp = kp.copy()
                kp[0, 0] = np.nextafter(kp[0, 0], np.inf)
            if mode == "bg" and calls["n"] == 3:
                o = o + 1e-6
            return o, oc, bl, kp

        def arm(p=patched, c=calls):
            c["n"] = 0
            RL.board_scores = p
        try:
            stop_case(title, "scores_" + mode, gate, stage=stage, pre=arm)
        finally:
            RL.board_scores = orig_scores
    # S-ENV: nothing written, the folder's done record kept, no data reader called
    loads = {"n": 0}
    orig_load = RS.load_context

    def counted(a, log):
        loads["n"] += 1
        return orig_load(a, log)
    RS.load_context = counted
    try:
        for title, change, limit in (
                ("a wrong library version", lambda what, rec: (dict(rec, versions=dict(rec["versions"], numpy="0.0.0"))
                                                               if what == "board" else rec), False),
                ("1 BLAS thread (threadpoolctl)", None, True),
                ("numpy's pool missing from board.json threadpool_info",
                 lambda what, rec: (dict(rec, threadpool_info=[["openmp", "openmp", "vcomp", 8]]) if what == "board"
                                    else rec), False)):
            name = "env_" + re.sub(r"[^a-z0-9]+", "_", title.lower())[:20]
            pk, sk, rk = case(name, change=change)
            models = os.path.join(base, "models_" + name)
            had = good_piece(S, W, models, patch, sroot, reg, n)
            t0 = tree_state(models)
            c0, l0 = dict(w.calls), loads["n"]
            if limit:
                with threadpoolctl.threadpool_limits(limits=1, user_api="blas"):
                    rc = run_main(S, argv_of(W, sk, rk, models, n), pk)
            else:
                rc = run_main(S, argv_of(W, sk, rk, models, n), pk)
            lines = last_run_lines(W)
            check("S4 S-ENV, %s: exit 3, nothing written (done record kept), no data reader called" % title,
                  had and rc == 3 and tree_state(models) == t0 and w.calls == c0 and loads["n"] == l0
                  and any("STOP S-ENV" in ln for ln in lines),
                  {"exit": rc, "unchanged": tree_state(models) == t0, "readers": {k: w.calls[k] - c0[k] for k in c0},
                   "load_context": loads["n"] - l0})
    finally:
        RS.load_context = orig_load
    # S-SAMPLE before the piece's identity is known: nothing written, the finished piece kept, no data reader called
    empty = os.path.join(base, "empty_register.txt")
    C.write_text(empty, "")
    for title, name, extra, reg_o in (("an unregistered sample (an empty register)", "unregistered", (), empty),
                                      ("a wrong --n beside a finished piece", "wrong_n", ("--n", "7"), None)):
        pk, sk, rk = case(name)
        models = os.path.join(base, "models_" + name)
        had = good_piece(S, W, models, patch, sroot, reg, n)
        t0 = tree_state(models)
        c0 = dict(w.calls)
        rc = run_main(S, argv_of(W, sk, reg_o or rk, models, n, *extra), pk)
        lines = last_run_lines(W)
        check("S4 S-SAMPLE, %s: exit 3, nothing written (the finished piece kept), no data reader called" % title,
              had and rc == 3 and tree_state(models) == t0 and w.calls == c0
              and any("STOP S-SAMPLE" in ln and "nothing written" in ln for ln in lines),
              {"exit": rc, "unchanged": tree_state(models) == t0, "readers": {k: w.calls[k] - c0[k] for k in c0},
               "done_record_kept": os.path.isfile(os.path.join(models, "rival_ridge", "rows.parquet.done.json"))})
    s_bad = w.S_df.copy()
    s_bad.loc[0, "time"] = 99999
    stop_case("S-SAMPLE, a sample row that is not a test row (load_context's refusal)", "not_test", "S-SAMPLE",
              sample=(s_bad, w.B_df))
    b_bad = w.B_df.copy()
    b_bad.loc[0, "time"] = 99998
    stop_case("S-BG, a background key that is not a refit row (load_context's stop)", "bg_key", "S-BG",
              sample=(w.S_df, b_bad))


def s4b_exact_only(S, W, root, log):
    """--exactness-only in this script's own folder: a stop removes its done record; a pass removes this script's own
    FAILED.json of an earlier S-EXACT stop at stage inputs or bits, and no other FAILED.json."""
    RL = S.RL
    w = S.w5
    patch, sroot, reg = S.s2
    n = len(w.epos)
    base = os.path.join(root, "s4b")
    models = os.path.join(base, "models")
    out = os.path.join(models, "rival_ridge")
    done = os.path.join(out, "rows.parquet.done.json")
    failed = os.path.join(out, "FAILED.json")
    had = good_piece(S, W, models, patch, sroot, reg, n)

    def scale(what, rec):
        if what == "model":
            rec["coef"][w.label] = [v * (1.0 + 1e-12) for v in rec["coef"][w.label]]
        return rec
    pk, sk, rk = synth_board(S, os.path.join(base, "board_scaled"), w, change=scale)
    rc = run_main(S, argv_of(W, sk, rk, models, n, "--exactness-only"), pk)
    stage = ((C.read_json(failed).get("exactness") or {}).get("stage")) if os.path.isfile(failed) else None
    check("S4b --exactness-only, S-EXACT stop in this script's own folder: exit 3, FAILED.json, done record removed",
          had and rc == 3 and failed_gate(out) == "S-EXACT" and stage == "bits" and not os.path.isfile(done),
          {"exit": rc, "gate": failed_gate(out), "stage": stage, "done_record_removed": not os.path.isfile(done)})
    rc2 = run_main(S, argv_of(W, sroot, reg, models, n, "--exactness-only"), patch)
    gone = not os.path.isfile(failed)
    check("S4b a passing --exactness-only run removes this script's FAILED.json of an S-EXACT stop (stage bits)",
          rc2 == 0 and gone, {"exit": rc2, "own_removed": gone})
    kept = {}
    for tag, rec in (("another script's S-EXACT record", {"gate": "S-EXACT", "exactness": {"stage": "bits"}}),
                     ("this script's S-SAMPLE record", {"gate": "S-SAMPLE", "script": "ridge_shap.py"}),
                     ("this script's S-EXACT reread record", {"gate": "S-EXACT", "script": "ridge_shap.py",
                                                              "exactness": {"stage": "reread"}})):
        C.write_json(failed, dict(rec, note="planted", **{"pass": False}))
        h0 = C.sha256_file(failed)
        rc3 = run_main(S, argv_of(W, sroot, reg, models, n, "--exactness-only"), patch)
        kept[tag] = {"exit": rc3, "kept": os.path.isfile(failed) and C.sha256_file(failed) == h0}
    check("S4b a passing --exactness-only run keeps another script's record and this script's S-SAMPLE and S-EXACT "
          "reread records", all(v["exit"] == 0 and v["kept"] for v in kept.values()), kept)
    # a real writer stop (S-EVAL: the background model value moved by 1e-6), then a passing --exactness-only run
    mw = os.path.join(base, "models_writer")
    fw = os.path.join(mw, "rival_ridge", "FAILED.json")
    orig = RL.board_scores
    calls = {"n": 0}

    def shifted(*args, **kw):
        calls["n"] += 1
        o, oc, bl, kp = orig(*args, **kw)
        return (o + 1e-6 if calls["n"] == 3 else o), oc, bl, kp
    RL.board_scores = shifted
    try:
        rcw = run_main(S, argv_of(W, sroot, reg, mw, n), patch)
    finally:
        RL.board_scores = orig
    rw = C.read_json(fw) if os.path.isfile(fw) else {}
    hw = C.sha256_file(fw) if os.path.isfile(fw) else None
    rcx = run_main(S, argv_of(W, sroot, reg, mw, n, "--exactness-only"), patch)
    check("S4b a writer's S-EVAL stop record (this script's, no gate field) survives a passing --exactness-only run",
          rcw == 3 and rw.get("script") == "ridge_shap.py" and rw.get("gate") is None
          and (rw.get("checks_passed") or {}).get("S-EVAL") is False and rcx == 0 and os.path.isfile(fw)
          and C.sha256_file(fw) == hw, {"writer_stop_exit": rcw, "checks_passed": rw.get("checks_passed"),
                                        "exactness_only_exit": rcx, "kept": os.path.isfile(fw)})


def s5_refusals(S, W, root, log):
    np, RL = S.np, S.RL
    w = S.w5
    patch, sroot, reg = S.s2
    n = len(w.epos)
    base = os.path.join(root, "s5")

    def refused(title, rc, models, t0, extra=None):
        lines = last_run_lines(W)
        ok = rc == 1 and tree_state(models) == t0 and any("REFUSED" in ln for ln in lines)
        check("S5 %s: exit 1, nothing written" % title, ok, dict({"exit": rc, "unchanged": tree_state(models) == t0},
                                                               **(extra or {})))
    models = os.path.join(base, "models_drift")
    c0 = dict(w.calls)
    keep = RL.COPIED_SOURCES
    RL.COPIED_SOURCES = dict(keep, run_ridge="0" * 64)
    try:
        rc = run_main(S, argv_of(W, sroot, reg, models, n), patch)
    finally:
        RL.COPIED_SOURCES = keep
    refused("the drift guard (a changed run_ridge source)", rc, models, {}, {"readers": {k: w.calls[k] - c0[k]
                                                                                         for k in c0}})
    pk, sk, rk = synth_board(S, os.path.join(base, "board_nopick"), w, change=lambda what, rec: (
        {"picks": {}} if what == "picks" else rec))
    models = os.path.join(base, "models_nopick")
    refused("no ridge pick", run_main(S, argv_of(W, sk, rk, models, n), pk), models, {})
    lock = C.write_text(os.path.join(base, "locks", "treeroute_heavy_job.lock"), "synthetic lock")
    models = os.path.join(base, "models_lock")
    refused("a heavy-job lock", run_main(S, argv_of(W, sroot, reg, models, n), patch, locks=(lock,)), models, {})
    models = os.path.join(base, "models_busy")
    c0 = dict(w.calls)
    rc = run_main(S, argv_of(W, sroot, reg, models, n), patch, busy=[("run_shap.py", 4242)])
    lines = last_run_lines(W)
    refused("another SHAP step running (a planted run_shap.py process)", rc, models, {})
    check("S5 that refusal names the other step by script and process id, and comes before any reader",
          any("another SHAP step is running (run_shap.py pid 4242)" in ln for ln in lines) and w.calls == c0,
          {"readers": {k: w.calls[k] - c0[k] for k in c0}})
    procs = [(101, "python.exe", "C:/py/python.exe -I -B D:/a/scripts/run_shap.py --problem pm25"),
             (102, "py.exe", "py -3.9 -I -B D:/a/scripts/tr_rebuild.py --problem pm25"),
             (103, "notepad.exe", "notepad.exe D:/a/scripts/run_shap.py"),
             (104, "python.exe", "C:/py/python.exe -I -B D:/a/scripts/tests/smoke_ridge.py --label smoke"),
             (105, "python.exe", "C:/py/python.exe -I -B D:/a/scripts/ridge_shap.py --problem fire --lead 0"),
             (106, "pythonw.exe", "pythonw.exe D:/a/scripts/bardl_shap.py --problem ndvi"),
             (107, "python.exe", "")]
    got = RL.busy_processes(procs, skip={105})
    got_all = RL.busy_processes(procs, skip=set())
    live = RL.busy_processes()
    check("S5 busy_processes: Python processes naming a SHAP script count; an editor, the smoke and this process's "
          "own line do not; the live call works", got == [("bardl_shap.py", 106), ("run_shap.py", 101),
                                                          ("tr_rebuild.py", 102)]
          and ("ridge_shap.py", 105) in got_all and isinstance(live, list) and all(p != os.getpid() for _, p in live),
          {"constructed": got, "live_other_shap_processes (information)": None if live is None else len(live)})
    # own_lineage: the direct parent's recorded id is used only when psutil's walk fails
    import psutil
    keep_parents, keep_ppid = psutil.Process.parents, os.getppid
    pid_self, pid_parent = os.getpid(), os.getppid()
    line_py = (pid_parent, "py.exe", "py -3.9 -I -B D:/a/scripts/ridge_shap.py")

    def walk_fails(self):
        raise psutil.AccessDenied(self.pid)
    try:
        psutil.Process.parents = walk_fails
        lin_fail = RL.own_lineage()
        hits_fail = RL.busy_processes([line_py])
        hits_noskip = RL.busy_processes([line_py], skip=set())
        psutil.Process.parents = lambda self: []
        os.getppid = lambda: 4343
        lin_ok = RL.own_lineage()
        hits_ok = RL.busy_processes([(4343, "python.exe", "C:/py/python.exe -I -B D:/a/scripts/run_shap.py")])
    finally:
        psutil.Process.parents, os.getppid = keep_parents, keep_ppid
    check("S5 own_lineage: when psutil's walk fails, the direct parent (the py launcher) is skipped",
          lin_fail == {pid_self, pid_parent} and hits_fail == [] and hits_noskip == [("ridge_shap.py", pid_parent)],
          {"lineage_size": len(lin_fail), "hits": hits_fail, "hits_without_skip": hits_noskip})
    check("S5 own_lineage: when the walk works, a recorded parent id is not added (a reused id still counts)",
          lin_ok == {pid_self} and hits_ok == [("run_shap.py", 4343)], {"lineage_size": len(lin_ok), "hits": hits_ok})
    models = os.path.join(base, "models_unreadable")
    C.write_text(os.path.join(models, "rival_ridge", "rows.parquet.done.json"), "{not json")
    t0 = tree_state(models)
    refused("an unreadable done record", run_main(S, argv_of(W, sroot, reg, models, n), patch), models, t0)
    # another script's piece (rival_shap.py's: a done record without 'script')
    own = os.path.join(base, "models_own")
    if not good_piece(S, W, own, patch, sroot, reg, n):
        check("S5 a finished piece to copy as another script's", False, own)
        return
    fdir = os.path.join(base, "models_foreign", "rival_ridge")
    C.makedirs(fdir)
    for f in ("rows.parquet", "meta.json", "background_keys.parquet"):
        shutil.copyfile(os.path.join(own, "rival_ridge", f), C.assert_writable(os.path.join(fdir, f)))
    C.write_json(os.path.join(fdir, "exactness.json"), {"pass": True, "note": "planted: rival_shap.py's record"})
    with Patched(S, patch):
        a = RL.parse(argv_of(W, sroot, reg, os.path.dirname(fdir), n))
        bd = RL.board_records(a, lambda m: None)
        ident = C.sample_identity("fire", sroot, reg, lead=0)
        rs_in = RL.rs_identity(a, bd, ident)
    C.mark_done(os.path.join(fdir, "rows.parquet"), rs_in, {"seconds": 0.1, "sample_sha256": ident["sample_sha256"],
                                                            "background_keys_sha256": "synthetic"})
    fmodels = os.path.dirname(fdir)
    t0 = tree_state(fmodels)
    rc = run_main(S, argv_of(W, sroot, reg, fmodels, n), patch)
    lines = last_run_lines(W)
    check("S5 another script's current piece: exit 0, 'nothing to do', nothing written",
          rc == 0 and tree_state(fmodels) == t0 and any("nothing to do" in ln for ln in lines), [rc] + lines[-1:])
    pk, sk, rk = synth_board(S, os.path.join(base, "board_env_bad"), w, change=lambda what, rec: (
        dict(rec, versions=dict(rec["versions"], numpy="0.0.0")) if what == "board" else rec))
    rc = run_main(S, argv_of(W, sroot, reg, fmodels, n), pk)
    check("S5 another script's piece, S-ENV stop (a wrong version): exit 3, nothing written, no FAILED.json",
          rc == 3 and tree_state(fmodels) == t0 and not os.path.isfile(os.path.join(fdir, "FAILED.json")), rc)
    empty = C.write_text(os.path.join(base, "empty_register.txt"), "")
    rc = run_main(S, argv_of(W, sroot, empty, fmodels, n), patch)
    check("S5 another script's piece, S-SAMPLE stop (an unregistered sample): exit 3, nothing written",
          rc == 3 and tree_state(fmodels) == t0 and not os.path.isfile(os.path.join(fdir, "FAILED.json")), rc)
    refused("another script's piece, --exactness-only", run_main(S, argv_of(W, sroot, reg, fmodels, n,
                                                                            "--exactness-only"), patch), fmodels, t0)
    rec = C.read_json(os.path.join(fdir, "rows.parquet.done.json"))
    rec["inputs"] = "0" * 64
    C.write_json(os.path.join(fdir, "rows.parquet.done.json"), rec)
    t1 = tree_state(fmodels)
    refused("another script's stale piece", run_main(S, argv_of(W, sroot, reg, fmodels, n), patch), fmodels, t1)
    try:
        RL.parse(["--problem", "fire", "--lead", "0", "--rows", "5"])
        code = 0
    except SystemExit as exc:
        code = exc.code
    check("S5 --rows without --out-root: exit 2 (argparse)", code == 2, code)


def rs_main(S, W, argv, patch):
    """rival_shap.py's own main() in this process on a synthetic board (the fake readers; its log under the smoke's
    logs/, never the analysis' logs/): its exit code."""
    keep_argv, keep_log = sys.argv, C.Log
    C.Log = smoke_log_class(W)
    sys.argv = ["rival_shap.py"] + list(argv)
    try:
        with Patched(S, patch):
            try:
                S.RS.main()
                return 0
            except SystemExit as exc:
                return exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv, C.Log = keep_argv, keep_log


def rs_argv(sroot, reg, models):
    return ["--problem", "fire", "--lead", "0", "--learners", "ridge", "--sample-root", sroot, "--register", reg,
            "--out-root", models]


def s5b_rival_shap(S, W, root, log):
    """rival_shap.py's own main() beside this script: its finished ridge piece on a no-flag board must be recognised
    by rs_identity (an independent test of rival_shap.py:539-544: S5 builds its foreign record with rs_identity
    itself); a rival_shap.py re-run (as run_shap.py's rivals step makes one) beside this script's piece on the flagged
    board must stop at its own S-EXACT and touch only its exactness.json."""
    base = os.path.join(root, "s5b")
    w2 = add_pool(S, S.w2, 200, 50, 4)
    p2, s2r, r2 = synth_board(S, os.path.join(base, "board_noflag"), w2, guard_passed=True)
    m2 = os.path.join(base, "models_rival_shap")
    rc = rs_main(S, W, rs_argv(s2r, r2, m2), p2)
    dpath = os.path.join(m2, "rival_ridge", "rows.parquet.done.json")
    drec = C.read_json(dpath) if os.path.isfile(dpath) else {}
    t0 = tree_state(m2)
    rc2 = run_main(S, argv_of(W, s2r, r2, m2, None), p2)
    lines = last_run_lines(W)
    check("S5b rival_shap.py's own piece (no flags, its real main()): ridge_shap.py 'nothing to do', exit 0, nothing "
          "written", rc == 0 and bool(drec) and "script" not in drec and rc2 == 0 and tree_state(m2) == t0
          and any("nothing to do" in ln for ln in lines),
          {"rival_shap_exit": rc, "its_done_record_names_a_script": "script" in drec, "ridge_shap_exit": rc2,
           "unchanged": tree_state(m2) == t0})
    patch, sroot, reg = S.s3
    m1 = os.path.join(base, "models_flagged")
    f1 = os.path.join(m1, "rival_ridge")
    rc_a = run_main(S, argv_of(W, sroot, reg, m1, None), patch)
    before = tree_state(f1)
    rc_b = rs_main(S, W, rs_argv(sroot, reg, m1), patch)
    after = tree_state(f1)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    ep = os.path.join(f1, "exactness.json")
    ex = C.read_json(ep) if os.path.isfile(ep) else {}
    check("S5b a rival_shap.py re-run beside this script's piece (flags): exit 3 at its S-EXACT, only exactness.json "
          "written", rc_a == 0 and rc_b == 3 and changed == ["exactness.json"] and ex.get("pass") is False,
          {"ridge_shap_exit": rc_a, "rival_shap_exit": rc_b, "changed": changed,
           "rival_shap_bit_equal": [ex.get("bit_equal_rows"), ex.get("rows_finite")]})
    rc_c = run_main(S, argv_of(W, sroot, reg, m1, None), patch)
    lines = last_run_lines(W)
    check("S5b ridge_shap.py afterwards: skipped, no file changed, rival_shap.py's failed check reported",
          rc_c == 0 and tree_state(f1) == after and any("skipped" in ln for ln in lines)
          and any("exactness.json, kept" in ln and "FAIL" in ln for ln in lines), [rc_c] + lines[-2:])


def s6_compare(S, W, root, log, a):
    np, pq = S.np, S.RS.pq
    patch, sroot, reg = S.s2
    w = S.w5
    n = len(w.epos)
    models = os.path.join(root, "s2", "models")
    cdir = os.path.join(models, "compare")
    C.write_json(os.path.join(cdir, "per_lead.json"), {"models": ["rival_lgbm"], "draws": 1})
    rc = run_main(S, argv_of(W, sroot, reg, models, n), patch)
    lines = last_run_lines(W)
    check("S6 a skip beside a comparison that does not list rival_ridge logs a REMINDER",
          rc == 0 and any("skipped" in ln for ln in lines) and any("REMINDER" in ln for ln in lines), lines[-1:])
    shutil.rmtree(C.assert_writable(cdir))
    src, dst = os.path.join(models, "rival_ridge"), C.makedirs(os.path.join(models, "rival_ridgecopy"))
    for f in ("rows.parquet", "rows.parquet.done.json", "background_keys.parquet"):
        shutil.copyfile(os.path.join(src, f), C.assert_writable(os.path.join(dst, f)))
    meta = C.read_json(os.path.join(src, "meta.json"))
    meta["guard"] = dict(meta.get("guard") or {}, passed=True)
    meta["model"] = "rival_ridgecopy"
    C.write_json(os.path.join(dst, "meta.json"), meta)
    rc = run_child(py_cmd() + [THIS, "--step", "compare-child", "--label", a.label, "--child-root", models,
                               "--child-sample", sroot, "--child-register", reg, "--child-export", patch["export"],
                               "--child-problem", "fire"], log, "compare_shap.py on the synthetic models root (child)")
    per_path = os.path.join(cdir, "per_lead.json")
    if rc != 0 or not os.path.isfile(per_path):
        check("S6 compare_shap.py (child) exit 0", False, rc)
        return
    per = C.read_json(per_path)
    key = "log_c|c=0.012987012987|ub=1"
    labels = pq.read_table(os.path.join(cdir, "pairs.parquet"), columns=["model_a", "model_b",
                                                                         "pair_label"]).to_pandas()
    lab = sorted(set(labels["pair_label"]))
    check("S6 compare_shap.py picks rival_ridge up, declined by its guard (D6), out of the main set",
          per.get("models") == ["rival_ridge", "rival_ridgecopy"] and per.get("declined_by_guard") == ["rival_ridge"]
          and (per.get("links") or {}).get("rival_ridge") == key and per.get("main_set") == ["rival_ridgecopy"]
          and lab == ["same-link; raw model, declined by its guard: rival_ridge"],
          {k: per.get(k) for k in ("models", "declined_by_guard", "main_set", "links")})
    rc = run_main(S, argv_of(W, sroot, reg, models, n), patch)
    lines = last_run_lines(W)
    check("S6 a skip beside the comparison made from its rows: no REMINDER",
          rc == 0 and any("skipped" in ln for ln in lines) and not any("REMINDER" in ln for ln in lines), lines[-1:])


def s7_hygiene(S, W, root, log, logs0):
    RL = S.RL
    rec = RL.drift_guard(lambda m: None)
    check("S7 the copied-source hashes are current (drift guard)", all(v["equal"] for v in rec.values()),
          {k: [v["lines"], v["sha256"][:16]] for k, v in rec.items()})
    bad, eng = C.privacy_scan(W, names=local_names())
    check("S7 privacy: no account or host name in the smoke folder", not bad and eng == 0, {"files": bad[:5],
                                                                                           "engine": eng})
    caches = []
    for top in (C.SCRIPTS, os.path.join(C.ROOT, "smoke")):
        for d, dirs, _ in os.walk(top):
            caches += [os.path.join(d, x) for x in dirs if x == "__pycache__"]
    check("S7 no __pycache__ under scripts/ or smoke/", not caches, [C.redact(c) for c in caches[:5]])
    check("S7 no analysis log written or changed", logs_state() == logs0, sorted(logs_state()))
    peak = C.rss_gb()
    check("S7 the synthetic step's peak working set stays under 1 GB", peak is not None and peak < 1.0, peak)


def step_synthetic(W, log, a):
    import psutil
    free = psutil.virtual_memory().available / 2 ** 30
    if free < MIN_FREE_SYNTH_GIB:
        raise GuardStop("%.2f GiB free: the synthetic step needs %.1f GiB" % (free, MIN_FREE_SYNTH_GIB))
    import ridge_shap as RL                         # the boards' pins (8) before numpy loads
    S = SimpleNamespace(RL=RL, RS=RL.RS, np=RL.np, pd=RL.pd, M=RL.M, H=RL.H, TS=RL.TS, clip=RL.clip_to_legal,
                        rng=RL.np.random.default_rng(20261113))
    root = C.makedirs(os.path.join(W, "synthetic"))
    logs0 = logs_state()
    t0 = time.time()
    s1_exactness(S, log)
    log("S1 done in %.1f s" % (time.time() - t0))
    s2_main(S, W, root, log)
    s3_big(S, W, root, log)
    s4_gates(S, W, root, log)
    s4b_exact_only(S, W, root, log)
    s5_refusals(S, W, root, log)
    s5b_rival_shap(S, W, root, log)
    s6_compare(S, W, root, log, a)
    s7_hygiene(S, W, root, log, logs0)
    REPORT["_synthetic"] = {"seconds": round(time.time() - t0, 1), "peak_rss_gb": C.rss_gb(),
                            "available_gib_at_start": round(free, 2)}


# ---------------------------------------------------------------------------------------------------------------
# real steps (each re-checks the heavy-job guard first)
def read_parquet(path, columns=None):
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=columns).to_pandas()


def exact_checks(tag, W, problem, root, rc, log, want_layout):
    out = os.path.join(root, "rival_ridge")
    files = sorted(os.listdir(out)) if os.path.isdir(out) else []
    rec = C.read_json(os.path.join(out, "ridge_shap_exactness.json")) if "ridge_shap_exactness.json" in files else {}
    m = EXPECT_TEST_ROWS.get(problem)
    raw = rec.get("raw") or {}
    check("%s: exit 0, only ridge_shap_exactness.json written" % tag,
          rc == 0 and files == ["ridge_shap_exactness.json"], [rc, files])
    check("%s: pre and raw bit for bit on every test row (%s)" % (tag, m),
          rec.get("pass") is True and rec.get("bit_equal_rows") == m and raw.get("bit_equal_rows") == m
          and rec.get("keys_only_saved") == 0 and rec.get("keys_only_test") == 0,
          {"pre": rec.get("bit_equal_rows"), "raw": raw.get("bit_equal_rows"), "rows": rec.get("rows")})
    blocks = rec.get("blocks") or []
    check("%s: every block stored %s" % (tag, want_layout), bool(blocks) and all(
        (b["F"] and not b["C"]) if want_layout == "F" else b["C"] for b in blocks),
        [(b["rows"], b["C"], b["F"]) for b in blocks])
    REPORT.setdefault("_exact", {})[problem] = {
        "row_by_row_copy": (rec.get("row_by_row_copy") or {}).get("bit_equal_rows"), "rows": rec.get("rows"),
        "blocks": len(blocks), "blas": (rec.get("env") or {}).get("numpy_blas_pool"),
        "board_code_reproduced": (rec.get("board_code_reproduced") or {}).get("reproduced_with"),
        "seconds": rec.get("seconds"), "peak_rss_gb": rec.get("peak_rss_gb")}
    return rec


def step_fire(W, log, a):
    need_guard("the fire exactness check", log)
    C.pin_threads(8)
    logs0 = logs_state()
    real = C.out_dir("fire", 0)
    real0 = tree_state(real)
    root = os.path.join(W, "fire_exact")
    rc = run_child(ridge_cmd(W, "fire", root, "--exactness-only"), log, "ridge_shap.py fire --exactness-only")
    rec = exact_checks("R1 fire exact", W, "fire", root, rc, log, "F")
    rs = C.read_json(os.path.join(real, "rival_ridge", "exactness.json"))
    rb = (rec.get("row_by_row_copy") or {}).get("bit_equal_rows")
    check("R1 fire exact: blocks [0, 65536) and [65536, 96000)", [b["rows"] for b in rec.get("blocks") or []] == [
        [0, 65536], [65536, 96000]], [b["rows"] for b in rec.get("blocks") or []])
    check("R1 fire exact: the row-by-row copy = rival_shap.py's own count (its exactness.json)",
          rb == rs.get("bit_equal_rows") == 95711, [rb, rs.get("bit_equal_rows")])
    check("R1 fire exact: numpy's BLAS pool [blas, openblas, libscipy_openblas, 8]",
          (rec.get("env") or {}).get("numpy_blas_pool") == [NUMPY_POOL_ROW], (rec.get("env") or {}).get(
              "numpy_blas_pool"))
    bc = rec.get("board_code_reproduced") or {}
    check("R1 fire exact: the board's code hash reproduced with the kept pre-legal-fix harness.py",
          bc.get("recorded", "").startswith("71457aa9") and "preLegalFix" in str(bc.get("reproduced_with")),
          bc.get("reproduced_with"))
    need_guard("the fire full run", log)
    models = os.path.join(W, "fire_models")
    rc = run_child(ridge_cmd(W, "fire", models), log, "ridge_shap.py fire (full)")
    out = os.path.join(models, "rival_ridge")
    if rc != 0 or not os.path.isfile(os.path.join(out, "rows.parquet.done.json")):
        check("R2 fire full: exit 0 and a finished piece", False, rc)
        return
    meta = C.read_json(os.path.join(out, "meta.json"))
    done = C.read_json(os.path.join(out, "rows.parquet.done.json"))
    check("R2 fire full: 1,000 rows, every check passed, guard declined, link key",
          meta.get("rows") == 1000 and meta.get("pass") is True and all(meta.get("checks_passed", {}).values())
          and (meta.get("guard") or {}).get("passed") is False
          and meta.get("link_key") == "log_c|c=0.012987012987|ub=1",
          {k: meta.get(k) for k in ("rows", "pass", "checks_passed", "link_key")})
    ev, evb = meta.get("max_abs_evaluator_minus_model"), meta.get("max_abs_background_evaluator_minus_model")
    check("R2 fire full: both evaluator maxima are numbers <= 1e-12", isinstance(ev, float) and isinstance(evb, float)
          and ev <= 1e-12 and evb <= 1e-12, [ev, evb])
    import numpy as np
    rows = read_parquet(os.path.join(out, "rows.parquet"), ["row", "unit", "time", "pre"])
    pr = read_parquet(os.path.join(C.PROBLEMS["fire"]["board"], "lead_0", "preds_ridge.parquet"),
                      ["unit", "time", "lead", "pre__rival_ridge"])
    pr = pr[pr["lead"].to_numpy(np.int64) == 0]
    j = rows.assign(unit=rows["unit"].astype(str), time=rows["time"].to_numpy(np.int64)).merge(
        pr.assign(unit=pr["unit"].astype(str), time=pr["time"].to_numpy(np.int64)), on=["unit", "time"], how="left")
    same = np.ascontiguousarray(j["pre"].to_numpy(np.float64)).view(np.uint64) == np.ascontiguousarray(
        j["pre__rival_ridge"].to_numpy(np.float64)).view(np.uint64)
    check("R2 fire full: pre bit-equal to the board's pre__rival_ridge at every explained row",
          len(j) == 1000 and bool(same.all()), int(same.sum()))
    bk = read_parquet(os.path.join(out, "background_keys.parquet")).astype(str).sort_values(
        ["row", "unit", "time"]).reset_index(drop=True)
    bt = read_parquet(os.path.join(real, "treeroute", "background_keys.parquet")).astype(str).sort_values(
        ["row", "unit", "time"]).reset_index(drop=True)
    check("R2 fire full: background keys = treeroute's (content)", bk.equals(bt), [len(bk), len(bt)])
    check("R2 fire full: the done record names the script and the registered sample",
          done.get("script") == "ridge_shap.py" and str(done.get("sample_sha256", "")).startswith("1edbc3d1"),
          {"script": done.get("script"), "sample": str(done.get("sample_sha256"))[:16]})
    t0 = tree_state(out)
    need_guard("the fire rerun", log)
    rc = run_child(ridge_cmd(W, "fire", models), log, "ridge_shap.py fire again")
    lines = last_run_lines(W, "fire")
    check("R2 fire full: a rerun is skipped with no file changed", rc == 0 and tree_state(out) == t0
          and any("skipped" in ln for ln in lines), [rc] + lines[-2:])
    check("R2 fire: out/fire/lead_0 unchanged; no analysis log changed", tree_state(real) == real0
          and logs_state() == logs0, len(real0))


def step_compare(W, log, a):
    need_guard("the fire comparison", log)
    C.pin_threads(8)
    models = os.path.join(W, "fire_models")
    real = C.out_dir("fire", 0)
    if not os.path.isfile(os.path.join(models, "rival_ridge", "rows.parquet.done.json")):
        check("R3 compare: the fire step's finished ridge piece exists", False, models)
        return
    real0, logs0 = tree_state(real), logs_state()
    for m in FIRE_OTHERS:
        dst = C.makedirs(os.path.join(models, m))
        for f in ("rows.parquet", "rows.parquet.done.json", "meta.json", "background_keys.parquet"):
            shutil.copyfile(os.path.join(real, m, f), C.assert_writable(os.path.join(dst, f)))
    rc = run_child(py_cmd() + [THIS, "--step", "compare-child", "--label", a.label, "--child-root", models,
                               "--child-problem", "fire"], log, "compare_shap.py on the smoke's fire models (child)")
    per_path = os.path.join(models, "compare", "per_lead.json")
    if rc != 0 or not os.path.isfile(per_path):
        check("R3 compare: compare_shap.py exit 0", False, rc)
        return
    per = C.read_json(per_path)
    check("R3 compare: models, declined_by_guard, the ridge link key, main set (structured fields only)",
          per.get("models") == ["rival_lgbm", "rival_lgbm_tweedie", "rival_rf", "rival_ridge", "treeroute"]
          and per.get("declined_by_guard") == ["rival_ridge"] and per.get("main_set") == ["treeroute"]
          and (per.get("links") or {}).get("rival_ridge") == "log_c|c=0.012987012987|ub=1",
          {k: per.get(k) for k in ("models", "declined_by_guard", "main_set")})
    lab = read_parquet(os.path.join(models, "compare", "pairs.parquet"), ["model_a", "model_b", "pair_label"])
    rl = lab[(lab["model_a"] == "rival_ridge") | (lab["model_b"] == "rival_ridge")]["pair_label"]
    check("R3 compare: every pair with ridge is labelled 'raw model, declined by its guard: rival_ridge'",
          len(rl) > 0 and all(str(x).endswith("raw model, declined by its guard: rival_ridge") for x in rl),
          sorted(set(rl))[:3])
    REPORT["_compare"] = {lv: {"players": (per.get(lv) or {}).get("players"), "active": (per.get(lv) or {}).get(
        "active"), "structural_zero": len((per.get(lv) or {}).get("structural_zero") or [])}
        for lv in ("variable", "feature")}
    need_guard("ridge_shap.py after the comparison", log)
    rc = run_child(ridge_cmd(W, "fire", models), log, "ridge_shap.py fire after the comparison")
    lines = last_run_lines(W, "fire")
    check("R3 compare: ridge_shap.py afterwards: skipped, no REMINDER", rc == 0 and any("skipped" in ln for ln in lines)
          and not any("REMINDER" in ln for ln in lines), [rc] + lines[-1:])
    shutil.rmtree(C.assert_writable(os.path.join(models, "compare")))
    check("R3 compare: the smoke's compare/ removed; out/fire/lead_0 unchanged; no analysis log changed",
          not os.path.exists(os.path.join(models, "compare")) and tree_state(real) == real0 and logs_state() == logs0,
          len(real0))


def step_coral(W, log, a):
    need_guard("the coral exactness check", log)
    C.pin_threads(8)
    import numpy as np
    logs0 = logs_state()
    real = C.out_dir("coral", 0)
    real0 = tree_state(real)
    root = os.path.join(W, "coral_exact")
    rc = run_child(ridge_cmd(W, "coral", root, "--exactness-only"), log, "ridge_shap.py coral --exactness-only")
    rec = exact_checks("R4a coral exact", W, "coral", root, rc, log, "C")
    check("R4a coral exact: one block; the row-by-row copy passes too (no flags)",
          len(rec.get("blocks") or []) == 1 and (rec.get("row_by_row_copy") or {}).get("bit_equal_rows") == 2312,
          (rec.get("row_by_row_copy") or {}).get("bit_equal_rows"))
    need_guard("the coral full run", log)
    models = os.path.join(W, "coral_models")
    rc = run_child(ridge_cmd(W, "coral", models), log, "ridge_shap.py coral (full, into the smoke)")
    out = os.path.join(models, "rival_ridge")
    if rc == 0 and os.path.isfile(os.path.join(out, "rows.parquet")):
        new = read_parquet(os.path.join(out, "rows.parquet")).sort_values("row").reset_index(drop=True)
        old = read_parquet(os.path.join(real, "rival_ridge", "rows.parquet")).sort_values("row").reset_index(drop=True)
        cols = ([c for c in ("row", "unit", "group", "time", "year") if c in old.columns]
                + [c for c in old.columns if c.startswith(("phi__", "phiv__"))]
                + ["base", "eta", "resid", "gap", "add_err", "resid_flag"])
        same = all(c in new.columns and new[c].astype(str).equals(old[c].astype(str)) if c in ("unit", "group") else
                   (c in new.columns and np.array_equal(np.ascontiguousarray(new[c].to_numpy()).view(np.uint8),
                                                        np.ascontiguousarray(old[c].to_numpy()).view(np.uint8)))
                   for c in cols)
        check("R4b coral full: keys, phi, phiv, base, eta, resid, gap, add_err, resid_flag bit-equal to its piece",
              same and list(new.columns) == list(old.columns), len(cols))
        em_n, em_o = new["eta_model"].to_numpy(np.float64), old["eta_model"].to_numpy(np.float64)
        pn, po = new["pre"].to_numpy(np.float64), old["pre"].to_numpy(np.float64)
        de, dp = em_n != em_o, pn != po
        check("R4b coral full: eta_model differs by at most 1e-12; pre differs only where eta_model does",
              float(np.abs(em_n - em_o).max()) <= 1e-12 and not bool((dp & ~de).any()),
              {"eta_model_rows_differing": int(de.sum()), "pre_rows_differing": int(dp.sum()),
               "max_abs": float(np.abs(em_n - em_o).max())})
        pr = read_parquet(os.path.join(C.PROBLEMS["coral"]["board"], "lead_0", "preds_ridge.parquet"),
                          ["unit", "time", "lead", "pre__rival_ridge"])
        pr = pr[pr["lead"].to_numpy(np.int64) == 0]
        j = new.assign(unit=new["unit"].astype(str), time=new["time"].to_numpy(np.int64)).merge(
            pr.assign(unit=pr["unit"].astype(str), time=pr["time"].to_numpy(np.int64)), on=["unit", "time"],
            how="left")
        eq = np.ascontiguousarray(j["pre"].to_numpy(np.float64)).view(np.uint64) == np.ascontiguousarray(
            j["pre__rival_ridge"].to_numpy(np.float64)).view(np.uint64)
        check("R4b coral full: the new pre = the board's saved pre on every explained row", bool(eq.all()),
              int(eq.sum()))
        bk = [read_parquet(os.path.join(d, "background_keys.parquet")).astype(str).sort_values(
            ["row", "unit", "time"]).reset_index(drop=True) for d in (out, os.path.join(real, "rival_ridge"))]
        check("R4b coral full: background keys equal the finished piece's", bk[0].equals(bk[1]), len(bk[0]))
    else:
        check("R4b coral full: exit 0", False, rc)
    # (c) a copy of the finished piece: another script's piece
    need_guard("the coral copy runs", log)
    fmodels = os.path.join(W, "coral_foreign")
    fdir = C.makedirs(os.path.join(fmodels, "rival_ridge"))
    for f in os.listdir(os.path.join(real, "rival_ridge")):
        shutil.copyfile(os.path.join(real, "rival_ridge", f), C.assert_writable(os.path.join(fdir, f)))
    t0 = tree_state(fmodels)
    rc = run_child(ridge_cmd(W, "coral", fmodels), log, "ridge_shap.py coral on a copy of its piece")
    lines = last_run_lines(W, "coral")
    check("R4c coral copy: exit 0, nothing to do, no file changed", rc == 0 and tree_state(fmodels) == t0
          and any("nothing to do" in ln for ln in lines), [rc] + lines[-1:])
    need_guard("the coral copy --exactness-only run", log)
    rc = run_child(ridge_cmd(W, "coral", fmodels, "--exactness-only"), log, "coral copy --exactness-only")
    lines = last_run_lines(W, "coral")
    check("R4c coral copy: --exactness-only refused (exit 1) by its own rule, not the gate; no file changed",
          rc == 1 and tree_state(fmodels) == t0 and own_refusal(lines, "--exactness-only never writes into it"),
          [rc] + lines[-1:])
    need_guard("the coral copy run with an empty register", log)
    empty = C.write_text(os.path.join(W, "coral_register", "empty_register.txt"), "")
    rc = run_child(ridge_cmd(W, "coral", fmodels, "--register", empty), log, "coral copy with an empty register")
    check("R4c coral copy: S-SAMPLE stop (an unregistered sample): exit 3, nothing written",
          rc == 3 and tree_state(fmodels) == t0, rc)
    need_guard("the coral copy run with a doctored board version", log)
    bdoc = os.path.join(W, "coral_board_doctored")
    src = C.PROBLEMS["coral"]["board"]
    b = C.read_json(os.path.join(src, "board.json"))
    b["versions"] = dict(b.get("versions") or {}, numpy="0.0.0")
    C.write_json(os.path.join(bdoc, "board.json"), b)
    shutil.copyfile(os.path.join(src, "picks.json"), C.assert_writable(os.path.join(bdoc, "picks.json")))
    C.makedirs(os.path.join(bdoc, "lead_0"))
    for f in ("done_ridge.json", "model_ridge.json", "preds_ridge.parquet", "export.json"):
        shutil.copyfile(os.path.join(src, "lead_0", f), C.assert_writable(os.path.join(bdoc, "lead_0", f)))
    rc = run_child(py_cmd() + [THIS, "--step", "env-child", "--label", a.label, "--child-root", fmodels,
                               "--child-board", bdoc, "--child-problem", "coral"], log,
                   "ridge_shap.py coral on its copy with a doctored board version (child)")
    check("R4c coral copy: S-ENV stop (a doctored board version): exit 3, nothing written, no FAILED.json",
          rc == 3 and tree_state(fmodels) == t0, rc)
    need_guard("the coral stale-copy run", log)
    done = C.read_json(os.path.join(fdir, "rows.parquet.done.json"))
    done["inputs"] = "0" * 64
    C.write_json(os.path.join(fdir, "rows.parquet.done.json"), done)
    t1 = tree_state(fmodels)
    rc = run_child(ridge_cmd(W, "coral", fmodels), log, "ridge_shap.py coral on a stale copy")
    lines = last_run_lines(W, "coral")
    check("R4c coral copy: a stale copy refused (exit 1) by its own rule, not the gate; no file changed",
          rc == 1 and tree_state(fmodels) == t1
          and own_refusal(lines, "that is not current under rival_shap.py's own identity"), [rc] + lines[-1:])
    check("R4: out/coral/lead_0 unchanged; no analysis log changed", tree_state(real) == real0
          and logs_state() == logs0, len(real0))


def step_others(W, log, a):
    need_guard("the R5 exactness checks", log)
    logs0 = logs_state()
    for p in a.problems:
        need_guard("the %s exactness check" % p, log)
        root = os.path.join(W, "exact_%s" % p)
        rc = run_child(ridge_cmd(W, p, root, "--exactness-only"), log, "ridge_shap.py %s --exactness-only" % p)
        exact_checks("R5 %s exact" % p, W, p, root, rc, log, "F")
    check("R5: no analysis log changed", logs_state() == logs0, sorted(logs_state()))


# ---------------------------------------------------------------------------------------------------------------
def child_compare(W, a):
    """compare_shap.py itself (1 thread), logging under the smoke; a synthetic export root patched in when given."""
    C.Log = smoke_log_class(W)
    if a.child_export:
        C.PROBLEMS[a.child_problem] = dict(C.PROBLEMS[a.child_problem], export=a.child_export)
    sys.argv = ["compare_shap.py", "--problem", a.child_problem, "--lead", "0", "--models-root", a.child_root,
                "--draws", "200", "--out", os.path.join(a.child_root, "compare")]
    if a.child_sample:
        sys.argv += ["--sample-root", a.child_sample]
    if a.child_register:
        sys.argv += ["--register", a.child_register]
    import compare_shap
    compare_shap.main()


def child_env(W, a):
    """ridge_shap.py on a models root with the problem's board pointed at a doctored copy of its records."""
    C.PROBLEMS[a.child_problem] = dict(C.PROBLEMS[a.child_problem], board=a.child_board)
    import ridge_shap as RL
    return RL.main(["--problem", a.child_problem, "--lead", "0", "--out-root", a.child_root, "--log-dir",
                    os.path.join(W, "logs")] + list(a.child_extra))


def main():
    a = parse()
    W = os.path.join(C.ROOT, "smoke", "ridge_%s" % a.label)
    if a.step == "compare-child":
        return child_compare(W, a)
    if a.step == "env-child":
        sys.exit(child_env(W, a))
    C.makedirs(W)
    log = C.Log("smoke_ridge", os.path.join(W, "logs"))
    steps = list(STEPS) if a.step == "all" else [a.step]
    for s in steps:
        prepare(W, s, a.fresh, log)
    path = os.path.join(W, "smoke_report.json")
    report = C.read_json(path) if os.path.isfile(path) else {}
    code = 0
    for s in steps:
        REPORT.clear()
        del FAIL[:]
        t0 = time.time()
        log("smoke step %s (label %s)" % (s, a.label))
        guard_stop = None
        GUARD["passed"] = False
        try:
            {"synthetic": step_synthetic, "fire": step_fire, "compare": step_compare, "coral": step_coral,
             "others": step_others}[s](W, log, a)
        except GuardStop as exc:
            guard_stop = str(exc)
            try:
                log("STOPPED: %s" % exc)
            except Exception:                         # a broken log never skips the guard-stop scan below
                print("STOPPED: %s" % exc, flush=True)
        except BaseException as exc:                  # a crash: the privacy scan still runs, then the crash goes on
            if s != "synthetic":
                crash_scan(s, W, log, exc)
            raise
        if s != "synthetic":
            privacy_check("%s step" % s, W, real_names=guard_stop is None)
        report[s] = {"checks": dict(REPORT), "failed": list(FAIL), "guard_stop": guard_stop,
                     "seconds": round(time.time() - t0, 1), "finished": datetime.datetime.now().isoformat(
                         timespec="seconds"), "peak_rss_gb": C.rss_gb()}
        C.write_json(path, report)
        n = len([k for k in REPORT if not k.startswith("_")])
        log("smoke step %s: %d checks, %d failed%s, %.1f s" % (s, n, len(FAIL), "; guard stop" if guard_stop else "",
                                                                time.time() - t0))
        if guard_stop:
            code = 4
            break
        if FAIL:
            code = 1
    sys.exit(code)


if __name__ == "__main__":
    main()
