"""Check the rebuilt Python 3.9 against the old machine's run records (read only; writes nothing).

    py -3.9 -I -B check_env.py <manifest.json>                     libraries only
    py -3.9 -I -B check_env.py <manifest.json> --engine <path>     also start the engine's own launcher
    py -3.9 -I -B check_env.py <manifest.json> --boards <board>    also the rival boards' libraries and threads

<manifest.json> is a run manifest written on the old machine; it holds "python", "versions" and "launch".
With --engine, the engine package is imported from <path> (the old engine folder, reached through the
link) and treeroute.launch.pin_threads() runs in THIS process only: it sets the thread pins for this
process, loads sklearnex and the BLAS/OpenMP pools, and returns the launch record, which must equal the
manifest's "launch" block (the same comparison check_after_run.py makes). Importing the engine has no
side effects (treeroute/__init__.py, G-IMPORT), and -B plus sys.dont_write_bytecode keep .pyc files out
of the engine tree, which hash_tree.py checks file by file.
With --boards, <board> is a rival board.json written on the old machine; the library versions and the
thread pools are computed exactly as D:/treeroute/rivals_build/rivals/harness.py does at every board step
(library_versions, LIBRARIES at :96-97; thread_state at :405-415; models.THREADS = 8), and must be equal.
Each mode runs in its own process, as the engine and the boards do.

Prints one line per check, then RESULT: PASS (exit 0) or RESULT: FAIL (exit 1).
"""
import json
import os
import sys

sys.dont_write_bytecode = True

FAILS = []

# The engine launcher refuses to start if any of these is set (treeroute/launch.py FOREIGN_ENV_PREFIXES,
# FOREIGN_ENV_NAMES); the six thread pins must also be unset before it pins them (env_before_pins null).
FOREIGN_PREFIXES = ("OPENBLAS_", "GOTO", "OMP_", "KMP_", "MKL_", "BLIS_", "NUMEXPR_", "VECLIB_",
                    "SKLEARN", "SCIPY_", "NPY_", "DAAL", "ONEDAL", "TBB_")
FOREIGN_NAMES = ("PYTHONHASHSEED",)
# Not refused by the engine, but it switches oneTBB's thread manager (tcmlib) on; the old runs had none set.
EXTRA_PREFIXES = ("TCM_",)

# rivals/harness.py LIBRARIES (:96-97) and rivals/models.py THREADS (:38).
BOARD_LIBRARIES = ("lightgbm", "scikit-learn", "scikit-learn-intelex", "numpy", "pandas", "pyarrow",
                   "threadpoolctl")
BOARD_THREADS = 8


def report(ok, text):
    print(("OK    " if ok else "FAIL  ") + text)
    if not ok:
        FAILS.append(text)


def info(text):
    print("INFO  " + text)


def norm(path):
    return os.path.normcase(os.path.normpath(path))


def check_launch(engine, manifest):
    if not os.path.isfile(os.path.join(engine, "treeroute", "__init__.py")):
        report(False, "engine folder not found: %s" % engine)
        return
    sys.path.insert(0, engine)
    import treeroute
    from treeroute import launch

    where = norm(os.path.dirname(os.path.dirname(treeroute.__file__)))
    report(where == norm(engine), "engine imported from %s" % os.path.dirname(treeroute.__file__))
    try:
        record = launch.pin_threads()
    except Exception as exc:  # a LaunchError names the exact reason; report it as a FAIL line
        report(False, "the engine launcher refused: %s: %s" % (type(exc).__name__, exc))
        return
    old = manifest["launch"]
    for key in sorted(set(record) | set(old)):
        mine, theirs = record.get(key), old.get(key)
        if key == "threadpools":
            a = sorted(json.dumps(r, sort_keys=True) for r in (mine or []))
            b = sorted(json.dumps(r, sort_keys=True) for r in (theirs or []))
            same = a == b
            report(same, "launch record '%s' equals the old run's (%d pools)" % (key, len(theirs or [])))
        else:
            same = json.dumps(mine, sort_keys=True) == json.dumps(theirs, sort_keys=True)
            report(same, "launch record '%s' equals the old run's" % key)
        if not same:
            info("   this machine: %s" % (mine,))
            info("   old machine : %s" % (theirs,))


def check_boards(board_path):
    with open(board_path, encoding="utf-8") as f:
        board = json.load(f)
    from importlib import metadata
    versions = {}
    for dist in BOARD_LIBRARIES:
        try:
            versions[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            versions[dist] = None
    report(versions == board["versions"], "rival-board library versions equal the old board's")
    if versions != board["versions"]:
        info("   this machine: %s" % (versions,))
        info("   old board   : %s" % (board["versions"],))
    report(board.get("threads") == BOARD_THREADS, "the old board ran at %s threads" % (board.get("threads"),))
    # Thread pools exactly as harness.thread_state() computes them (first, in a clean process).
    import threadpoolctl
    import lightgbm  # noqa: F401  (loads its OpenMP pool)
    import sklearn.ensemble  # noqa: F401
    import sklearnex.ensemble  # noqa: F401
    threadpoolctl.threadpool_limits(BOARD_THREADS)
    rows = sorted([str(i.get("user_api")), str(i.get("internal_api")), str(i.get("prefix")),
                   int(i.get("num_threads"))] for i in threadpoolctl.threadpool_info())
    report(rows == board["threadpool_info"], "rival-board thread pools equal the old board's (%d pools)"
           % len(board["threadpool_info"]))
    if rows != board["threadpool_info"]:
        info("   this machine: %s" % (rows,))
        info("   old board   : %s" % (board["threadpool_info"],))
    # The other libraries that fire Part B and the post-hoc tools load (after the thread check, on purpose).
    import importlib
    for name in ("netCDF4", "h5py", "xarray"):
        try:
            importlib.import_module(name)
            report(True, "%s imports" % name)
        except Exception as exc:
            report(False, "%s does not import: %s: %s" % (name, type(exc).__name__, exc))


def main(argv):
    if len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] not in ("--engine", "--boards")):
        print(__doc__)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        manifest = json.load(f)
    engine = argv[2] if len(argv) == 3 and argv[1] == "--engine" else None
    boards = argv[2] if len(argv) == 3 and argv[1] == "--boards" else None

    # 1. Interpreter and flags.
    version = "%d.%d.%d" % sys.version_info[:3]
    report(version == manifest["python"], "Python %s (old machine %s)" % (version, manifest["python"]))
    report(sys.maxsize > 2 ** 32, "64-bit Python")
    report(bool(sys.flags.isolated) and bool(sys.flags.dont_write_bytecode),
           "started with -I -B (isolated, writes no .pyc files)")
    info("interpreter: %s" % sys.executable)

    # 2. Library versions, read from the installed metadata exactly as the engine's fingerprint does
    #    (treeroute/runs/fingerprint.py library_versions; nothing is imported here).
    from importlib import metadata
    for dist, want in sorted(manifest["versions"].items(), key=lambda kv: kv[0].lower()):
        try:
            have = metadata.version(dist)
        except metadata.PackageNotFoundError:
            have = "not installed"
        report(have == want, "%s %s (old machine %s)" % (dist, have, want))

    # 3. The environment.
    found = sorted(k for k in os.environ
                   if k.upper().startswith(FOREIGN_PREFIXES) or k.upper() in FOREIGN_NAMES)
    report(not found, "no thread or seed variables set in the environment%s"
           % ("" if not found else ": " + ", ".join(found)))
    extra = sorted(k for k in os.environ if k.upper().startswith(EXTRA_PREFIXES))
    report(not extra, "no oneTBB thread-manager (TCM_*) variables set%s"
           % ("" if not extra else ": " + ", ".join(extra)))

    # 4. No user site-packages: the fire Part B commands run without -I and would see it.
    user_site = os.path.join(os.environ.get("APPDATA", ""), "Python",
                             "Python%d%d" % sys.version_info[:2], "site-packages")
    has_user = False
    if os.path.isdir(user_site):
        with os.scandir(user_site) as entries:
            has_user = any(True for _ in entries)
    report(not has_user, "no packages in the user site-packages folder (%s)" % user_site)

    # 5. The engine's own launcher (only with --engine; it must run before numpy is imported), or the
    #    rival boards' libraries and thread pools (only with --boards).
    if engine:
        check_launch(engine, manifest)
    if boards:
        check_boards(boards)

    # 6. Where the main libraries load from (after the pins when --engine was given).
    import numpy
    import scipy.linalg  # noqa: F401  (loads scipy's own OpenBLAS)
    import sklearn
    import pandas
    import pyarrow
    site_packages = norm(os.path.join(sys.prefix, "Lib", "site-packages"))
    for mod in (numpy, sklearn, pandas, pyarrow):
        loc = norm(os.path.dirname(os.path.dirname(mod.__file__)))
        report(loc == site_packages, "%s loads from Python's own site-packages" % mod.__name__)

    if not engine and not boards:
        try:
            import sklearnex  # noqa: F401
            import daal4py  # noqa: F401
            report(True, "sklearnex and daal4py import")
        except Exception as exc:  # report it, never hide it
            report(False, "sklearnex/daal4py import failed: %s: %s" % (type(exc).__name__, exc))
        try:
            import sklearn.utils._openmp_helpers  # noqa: F401  (loads the OpenMP runtime, vcomp)
        except Exception as exc:
            info("could not load sklearn's OpenMP helper: %s" % (exc,))
        from threadpoolctl import threadpool_info
        have = [(d.get("internal_api"), d.get("prefix"), d.get("version")) for d in threadpool_info()]
        want = [(d.get("internal_api"), d.get("prefix"), d.get("version"))
                for d in manifest["launch"]["threadpools"]]
        missing = [w for w in want if w not in have]
        report(not missing, "BLAS/OpenMP libraries as on the old machine%s"
               % ("" if not missing else "; missing: %s" % (missing,)))

    print("RESULT: %s" % ("PASS" if not FAILS else "FAIL (%d)" % len(FAILS)))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
