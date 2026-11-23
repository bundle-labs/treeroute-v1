"""Launcher: pin every thread pool from the engine constants BEFORE numpy is imported.

Order (G-THREADS):
  1. refuse if numpy or any numeric backend is already imported (the pins would come too late),
     and refuse if any other variable the numeric libraries read is set (OPENBLAS_*, OMP_*, KMP_*,
     MKL_*, SKLEARN*, TBB_*, PYTHONHASHSEED, ...; see FOREIGN_ENV_PREFIXES);
  2. set the BLAS / OpenMP environment pins to the engine constants (overwriting any value the
     shell had: the environment is a closed door, plan 1.7);
  3. import sklearnex (required, C14; it loads numpy, scipy and sklearn) and pin the oneDAL thread
     count; fail loudly otherwise;
  4. apply threadpoolctl limits to every pool now loaded, and verify each BLAS and OpenMP pool;
  5. keep a launch record (pins, pools, versions, worker counts) for the run manifest;
  6. dispatch the Typer CLI.

Importing this module does nothing: every action happens inside ``pin_threads()`` / ``main()``
(G-IMPORT: importing the engine patches nothing and reads no argv).

Tree-prediction workers and router workers are not environment pins; the engine modules that run
them read ``TREE_PREDICT_WORKERS``, ``ROUTER_WORKERS`` and ``ROUTER_WORKER_BLAS_THREADS`` from
engine_constants. The launch record carries them so the manifest shows every pool.
"""

import os
import platform
import sys

from treeroute import engine_constants as K
from treeroute.errors import LaunchError

# Environment variables read by the BLAS / OpenMP runtimes at load time.
PIN_ENV_VARS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)

# Modules that start thread pools on import; none may be loaded before the pins.
NUMERIC_MODULES = ("numpy", "scipy", "sklearn", "sklearnex", "daal4py", "onedal", "pandas", "numexpr")

# Other environment variables that the numeric libraries (or the interpreter) read and that can
# change a number or a thread count. None may be set when the engine starts: the environment is a
# closed door (plan 1.7), and a variable that is neither pinned nor refused would reach no manifest
# and no fingerprint. Matched on the upper-cased name (Windows names are case-insensitive).
FOREIGN_ENV_PREFIXES = (
    "OPENBLAS_", "GOTO", "OMP_", "KMP_", "MKL_", "BLIS_", "NUMEXPR_", "VECLIB_", "SKLEARN",
    "SCIPY_", "NPY_", "DAAL", "ONEDAL", "TBB_",
)
FOREIGN_ENV_NAMES = ("PYTHONHASHSEED",)

_STATE = {"record": None, "limiter": None}


def _loaded_numeric_modules():
    return sorted(m for m in NUMERIC_MODULES if m in sys.modules)


def foreign_environment(environ=None):
    """{name: value} of set variables that a numeric library reads, other than the six pins."""
    environ = os.environ if environ is None else environ
    pins = set(PIN_ENV_VARS)
    out = {}
    for name, value in environ.items():
        upper = name.upper()
        if upper in pins:
            continue
        if upper in FOREIGN_ENV_NAMES or upper.startswith(FOREIGN_ENV_PREFIXES):
            out[name] = value
    return dict(sorted(out.items()))


def pin_environment():
    """Set every BLAS/OpenMP environment pin to the engine constant. Returns {var: previous value}.

    Refuses first if a numeric module is already loaded, or if any other variable that the numeric
    libraries read is set (``foreign_environment``)."""
    early = _loaded_numeric_modules()
    if early:
        raise LaunchError(
            "numeric modules were imported before the thread pins: %s. The launcher must run first "
            "(start the engine with 'py -3.9 -m treeroute')." % ", ".join(early))
    foreign = foreign_environment()
    if foreign:
        raise LaunchError(
            "environment variables that the numeric libraries read are set: %s. The engine allows "
            "only its own thread pins (engine constants), because any other setting would change "
            "numbers or threads without reaching the manifest or the fingerprint. Unset them in "
            "the shell and start again."
            % ", ".join("%s=%s" % (k, v) for k, v in foreign.items()))
    previous = {}
    for var in PIN_ENV_VARS:
        previous[var] = os.environ.get(var)
        want = K.FOREST_THREADS if var == "OMP_NUM_THREADS" else K.BLAS_THREADS
        os.environ[var] = str(want)
    return previous


def _pool_rows(info):
    keys = ("user_api", "internal_api", "prefix", "num_threads", "version")
    return [{k: d.get(k) for k in keys} for d in info]


def apply_threadpool_limits():
    """Apply threadpoolctl limits to every loaded pool and verify each BLAS / OpenMP pool.

    Call after ``verify_sklearnex()`` so the pools that scipy and sklearn load are covered too.
    """
    import numpy  # noqa: F401  (imported here, after the environment pins, on purpose)
    import threadpoolctl

    limiter = threadpoolctl.threadpool_limits(limits={"blas": K.BLAS_THREADS,
                                                      "openmp": K.FOREST_THREADS})
    _STATE["limiter"] = limiter  # keep the controller alive for the life of the process
    pools = _pool_rows(threadpoolctl.threadpool_info())
    bad = []
    for row in pools:
        want = K.BLAS_THREADS if row["user_api"] == "blas" else K.FOREST_THREADS
        if row["num_threads"] != want:
            bad.append("%s/%s runs %s threads, engine constant says %s"
                       % (row["user_api"], row["internal_api"], row["num_threads"], want))
    if not any(row["user_api"] == "blas" for row in pools):
        bad.append("no BLAS pool found after importing numpy")
    if bad:
        raise LaunchError("thread pools are not pinned: " + "; ".join(bad))
    return pools


def verify_sklearnex():
    """sklearnex is required (C14). Import it, pin oneDAL's thread count, and fail loudly otherwise."""
    if not K.SKLEARNEX_REQUIRED:
        raise LaunchError("engine constant C14.sklearnex_required must be True")
    try:
        import sklearnex
        import daal4py
    except Exception as exc:  # any import failure is fatal: no silent fallback to plain sklearn
        raise LaunchError(
            "sklearnex is required (engine constant C14.sklearnex_required) but could not be "
            "imported: %s: %s" % (type(exc).__name__, exc)) from exc
    daal4py.daalinit(K.FOREST_THREADS)
    got = daal4py.num_threads()
    if got != K.FOREST_THREADS:
        raise LaunchError("oneDAL runs %s threads after daalinit(%s)" % (got, K.FOREST_THREADS))
    try:
        from importlib import metadata
        version = metadata.version("scikit-learn-intelex")
    except Exception as exc:
        raise LaunchError("cannot read the installed scikit-learn-intelex version: %s" % exc) from exc
    # OWNER RULING 2026-09-28 C (OWNER_RULINGS_2026-09-28.md): option (a), a global
    # sklearnex.patch_sklearn() here, after the pins, as the shipped runs did
    # (fire_architecture.py:66-68, coral_architecture.py:60-61). oneDAL does not equal stock sklearn at
    # the same seed, so an unpatched engine process would silently change numbers: refuse instead.
    # Only the launcher patches; importing treeroute never does (tests/test_import.py).
    sklearnex.patch_sklearn(verbose=False)
    if not sklearnex.sklearn_is_patched():
        raise LaunchError("sklearnex.patch_sklearn() ran but sklearn_is_patched() is False")
    return {"sklearnex_version": version, "onedal_threads": got,
            "sklearn_patched": bool(sklearnex.sklearn_is_patched())}


def pin_threads():
    """Run steps 1-5 once per process and return the launch record."""
    if _STATE["record"] is not None:
        return _STATE["record"]
    previous = pin_environment()
    backend = verify_sklearnex()
    pools = apply_threadpool_limits()
    record = {
        "python": platform.python_version(),
        "env_pins": {var: os.environ[var] for var in PIN_ENV_VARS},
        "env_before_pins": previous,
        "threadpools": pools,
        "backend": backend,
        "workers": {
            "forest_threads": K.FOREST_THREADS,
            "blas_threads": K.BLAS_THREADS,
            "tree_predict_workers": K.TREE_PREDICT_WORKERS,
            "router_workers": K.ROUTER_WORKERS,
            "router_worker_blas_threads": K.ROUTER_WORKER_BLAS_THREADS,
        },
    }
    _STATE["record"] = record
    return record


def record():
    """The launch record. Refuses if the engine was not started through the launcher."""
    if _STATE["record"] is None:
        raise LaunchError("the engine was not started through treeroute.launch (no thread pins)")
    return _STATE["record"]


def main(argv=None):
    """Pin, verify, then run the CLI. ``argv`` defaults to the process arguments (read here only)."""
    pin_threads()
    from treeroute import cli  # imported after the pins on purpose

    args = list(sys.argv[1:] if argv is None else argv)
    cli.app(args=args, prog_name="treeroute")
