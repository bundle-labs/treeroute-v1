"""Speedup-3 gate launcher (APP_PLAN.md 4.5 "Gates"; SPEEDPROOF_REPORT.md section 3).

Runs the UNPATCHED shipped pm25_adaptation.py -- its own file, executed by runpy, not a copy -- with
every BLAS library pinned to ONE thread for the whole process. The plan's speedup-3 gate is: the copy's
router on 8 workers at BLAS 1 must match THIS run byte for byte. If it does, the gap between the copy
and the shipped script as normally launched is the BLAS thread count and nothing else.

WHY A LAUNCHER, NOT AN ENVIRONMENT VARIABLE. The shipped script imports numpy (its line 106) before
fire_architecture's cap_threads(4) overwrites OPENBLAS_NUM_THREADS, and scipy's own OpenBLAS loads
after that. A shell OPENBLAS_NUM_THREADS=1 therefore pins numpy's BLAS but leaves scipy's at 4. Here
numpy and scipy.linalg are imported FIRST, so both OpenBLAS copies are loaded, and threadpoolctl then
pins both to 1 for the process lifetime. The BLAS state is recorded before and after the run, and the
run is declared INVALID (exit 3) if any BLAS library is not at 1 thread at the end (for example a BLAS
library loaded later, which the limit never reached).

sklearn is deliberately NOT imported early. That would load OpenMP (vcomp) before cap_threads(4) sets
OMP_NUM_THREADS, moving OpenMP from the shipped 4 threads to 16. Nothing the run computes is expected to
depend on OpenMP, but the launcher changes only the one thing the gate is about.

PLUMBING THAT CANNOT MOVE A RESULT. The shipped script hard-codes its temp files to D:/pm25 (the pool
through pm25_architecture.POOL, the tree matrices inside columns()). This task may write on D: only
under D:/treeroute/speedproof. So the file NAME of any path under D:/pm25/ is redirected to
D:/treeroute/speedproof/tmp/ in exactly two places: the `open` that numpy's memmap module uses (a name
shadowed in that one module's globals, so np.memmap stays numpy's own class), and os.remove (so the
shipped cleanup deletes the redirected files). The bytes written and read are unchanged. Every
redirect is printed and recorded. The shipped pre-flight still checks D:/pm25; this launcher also
checks tmp/ and refuses to start while either holds a matrix or pool file.

    cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper\\engine\\speedproof"
    py -3.9 -u run_shipped_blas1.py --smoke --npd 400 --links identity,log,logc --run-dir D:/treeroute/speedproof/wide_golden_blas1

Every argument is passed to the shipped script unchanged. --run-dir is REQUIRED, must lie under
D:/treeroute/speedproof/ (the shipped default would write into D:/pm25_adapt, a protected root) and must
not already hold anything; --force is refused. After the run, <run-dir>/launcher.json records the shipped
file's sha256, the BLAS state at three points, every redirect and the exit code. Nothing else is written.
"""
import glob
import hashlib
import json
import os
import runpy
import sys
import time
import traceback

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHIPPED = os.path.join(PROJECT, "pm25_adaptation.py")
SCOPE = "D:/treeroute/speedproof/"
TMP_DIR = "D:/treeroute/speedproof/tmp"
SHIPPED_TMP = "D:/pm25/"
_LIMITER = []           # the threadpool_limits object, kept alive for the process lifetime
REDIRECTS = []


def _norm(p):
    return os.path.abspath(p).replace("\\", "/")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _redirect(p):
    """A path under D:/pm25/ -> the same file name under TMP_DIR. Anything else is returned as is."""
    if isinstance(p, (str, os.PathLike)):
        s = os.fspath(p)
        if isinstance(s, str) and _norm(s).lower().startswith(SHIPPED_TMP.lower()):
            new = TMP_DIR + "/" + _norm(s)[len(SHIPPED_TMP):]
            if (s, new) not in REDIRECTS:
                REDIRECTS.append((s, new))
                print("[launcher] redirect %s -> %s" % (s, new), flush=True)
            return new
    return p


def _snapshot(threadpool_info):
    return [{k: d.get(k) for k in ("user_api", "internal_api", "prefix", "version", "num_threads",
                                   "filepath")} for d in threadpool_info()]


def main():
    args = list(sys.argv[1:])
    if "--force" in args:
        raise SystemExit("run_shipped_blas1: --force is refused (it would move an earlier run aside).")
    if "--run-dir" not in args:
        raise SystemExit("run_shipped_blas1: --run-dir is required (the shipped default writes into "
                         "D:/pm25_adapt, a protected root).")
    run_dir = _norm(args[args.index("--run-dir") + 1]).rstrip("/")
    if not run_dir.lower().startswith(SCOPE.lower()) or run_dir.lower() + "/" == SCOPE.lower():
        raise SystemExit("run_shipped_blas1: --run-dir must be a sub-folder of %s, got %s"
                         % (SCOPE, run_dir))
    if os.path.isdir(run_dir) and os.listdir(run_dir):
        raise SystemExit("run_shipped_blas1: %s already holds files; pick a new folder." % run_dir)
    stale = sorted(glob.glob(TMP_DIR + "/A_*.f32") + glob.glob(TMP_DIR + "/pool_*.f32")
                   + glob.glob(SHIPPED_TMP + "A_*.f32") + glob.glob(SHIPPED_TMP + "pool_*.f32"))
    if stale:
        raise SystemExit("run_shipped_blas1: refusing to start, temp files exist:\n  "
                         + "\n  ".join(stale))
    if not os.path.isdir(SHIPPED_TMP):
        # the shipped build_pool() calls os.makedirs(dirname(POOL)) on the UNREDIRECTED name; with the
        # folder present that is a no-op, without it a new folder would appear outside this task's scope
        raise SystemExit("run_shipped_blas1: %s does not exist; the shipped build_pool would create "
                         "it. Stopping rather than writing outside D:/treeroute/speedproof." % SHIPPED_TMP)
    os.makedirs(TMP_DIR, exist_ok=True)
    sha_shipped = _sha(SHIPPED)
    rec = dict(launcher=_norm(__file__), launcher_sha256=_sha(os.path.abspath(__file__)),
               shipped=_norm(SHIPPED), shipped_sha256=sha_shipped, argv=args,
               started=time.strftime("%Y-%m-%d %H:%M:%S"),
               env_threads={v: os.environ.get(v) for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                                           "MKL_NUM_THREADS")})
    print("[launcher] shipped %s sha256 %s" % (SHIPPED, sha_shipped), flush=True)

    # 1. load BOTH OpenBLAS copies (numpy's and scipy's), then pin every BLAS library to 1 thread
    sys.path.insert(0, PROJECT)
    import numpy as np                      # noqa: F401
    import scipy.linalg                     # noqa: F401  (loads scipy's own OpenBLAS)
    from threadpoolctl import threadpool_info, threadpool_limits
    rec["blas_loaded_unpinned"] = _snapshot(threadpool_info)
    _LIMITER.append(threadpool_limits(limits=1, user_api="blas"))
    rec["blas_after_pin"] = _snapshot(threadpool_info)
    print("[launcher] after pin: %s" % [(d["prefix"], d["user_api"], d["num_threads"])
                                        for d in rec["blas_after_pin"]], flush=True)
    bad = [d for d in rec["blas_after_pin"] if d["user_api"] == "blas" and d["num_threads"] != 1]
    if bad or not any(d["user_api"] == "blas" for d in rec["blas_after_pin"]):
        raise SystemExit("run_shipped_blas1: BLAS not pinned to 1 thread: %s" % rec["blas_after_pin"])

    # 2. temp-file redirect, D:/pm25/* -> TMP_DIR/* (file names only)
    mm_globals = np.memmap.__new__.__globals__
    assert mm_globals["__name__"].endswith("memmap") and "open" not in mm_globals, \
        "numpy's memmap module is not laid out as this launcher expects; stopping"
    import builtins
    _open, _remove = builtins.open, os.remove
    mm_globals["open"] = lambda file, *a, **k: _open(_redirect(file), *a, **k)
    os.remove = lambda path, *a, **k: _remove(_redirect(path), *a, **k)

    # 3. the shipped script, unchanged, as __main__
    sys.argv = [SHIPPED] + args
    rc = None
    try:
        runpy.run_path(SHIPPED, run_name="__main__")
        rc = 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if not isinstance(e.code, (int, type(None))):
            print(e.code, flush=True)
    except BaseException:
        rc = 1
        traceback.print_exc()
    finally:
        del mm_globals["open"]
        os.remove = _remove
        rec["blas_at_end"] = _snapshot(threadpool_info)
        bad_end = [d for d in rec["blas_at_end"] if d["user_api"] == "blas" and d["num_threads"] != 1]
        rec.update(redirects=REDIRECTS, exit_code=rc, finished=time.strftime("%Y-%m-%d %H:%M:%S"),
                   blas_all_one_thread_at_end=not bad_end,
                   tmp_left=sorted(glob.glob(TMP_DIR + "/*")),
                   shipped_tmp_left=sorted(glob.glob(SHIPPED_TMP + "*")),
                   shipped_sha256_after=_sha(SHIPPED))
        os.makedirs(run_dir, exist_ok=True)
        out = os.path.join(run_dir, "launcher.json")
        if os.path.exists(out):                       # never overwrite
            out = os.path.join(run_dir, "launcher_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        print("[launcher] exit %s | BLAS at end %s | tmp left %s | written %s"
              % (rc, [(d["prefix"], d["num_threads"]) for d in rec["blas_at_end"]
                      if d["user_api"] == "blas"], rec["tmp_left"], out), flush=True)
    if rec["shipped_sha256_after"] != sha_shipped:
        print("[launcher] !! the shipped file changed during the run", flush=True)
        return 4
    if bad_end:
        print("[launcher] !! INVALID: a BLAS library is not at 1 thread at the end: %s" % bad_end,
              flush=True)
        return 3
    return rc


if __name__ == "__main__":
    sys.exit(main())
