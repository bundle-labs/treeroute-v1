"""Self-test target for launch_pinned.py (legacy harness; a few seconds, no data read).

It does, in miniature, what the shipped fire smoke relies on the launcher for:
  1. numpy is already loaded when it starts; it then overwrites the thread variables with 4, as the
     shipped cap_threads(4) does (coral_safe.py:29-34), and loads scipy and sklearn afterwards;
  2. it creates a float32 np.memmap at a name under --source-prefix (a folder that does NOT exist, so
     a failed redirect raises instead of writing), finds it with glob.glob and deletes it with
     os.remove, exactly the calls fire_architecture.py makes for its pool and tree matrices;
  3. it runs a numpy and a scipy Cholesky solve (BLAS work) and records the thread pools;
  4. it writes its results under --out (inside the launcher's --out-dir).

    py -3.9 -u launch_pinned.py --script selftest_target.py --out-dir D:/treeroute/golden/_launcher_selftest ^
        --scratch D:/treeroute/golden/_launcher_selftest_scratch ^
        --redirect-prefix D:/treeroute/_absent_selftest_source/tmp_ -- ^
        --source-prefix D:/treeroute/_absent_selftest_source/tmp_ --out D:/treeroute/golden/_launcher_selftest/target
"""
import glob
import json
import os
import sys

import numpy as np


def main():
    a = sys.argv[1:]
    src = a[a.index("--source-prefix") + 1]
    out = a[a.index("--out") + 1]
    report = {"numpy_loaded_before_start": True}

    # 1. what the shipped cap_threads(4) does, after numpy is loaded
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
              "VECLIB_MAXIMUM_THREADS"):
        os.environ[v] = "4"
    import scipy.linalg
    import sklearn.ensemble  # noqa: F401  (loads OpenMP after the overwrite, as the shipped code does)
    from threadpoolctl import threadpool_info

    # 2. memmap / glob / remove at a redirected name
    path = src + "%d.f32" % os.getpid()
    mm = np.memmap(path, np.float32, "w+", shape=(2048, 16))
    mm[:] = np.arange(16, dtype=np.float32)
    mm.flush()
    report["memmap_filename"] = str(mm.filename).replace("\\", "/")
    found = glob.glob(src + "*.f32")
    report["glob_found"] = [f.replace("\\", "/") for f in found]
    assert len(found) == 1, "glob did not find the memmap through the redirect: %s" % found
    del mm
    os.remove(path)
    report["glob_after_remove"] = glob.glob(src + "*.f32")
    assert not report["glob_after_remove"], "os.remove did not delete the redirected file"

    # 3. BLAS work in numpy and scipy
    rng = np.arange(1, 401, dtype=np.float64).reshape(20, 20) / 400.0
    spd = rng @ rng.T + 20.0 * np.eye(20)
    b = np.linspace(0.0, 1.0, 20)
    x1 = np.linalg.solve(np.linalg.cholesky(spd) @ np.linalg.cholesky(spd).T, b)
    x2 = scipy.linalg.cho_solve(scipy.linalg.cho_factor(spd), b)
    report["max_abs_solve_gap"] = float(np.max(np.abs(x1 - x2)))
    report["pools"] = [{k: d.get(k) for k in ("user_api", "prefix", "num_threads")}
                       for d in threadpool_info()]

    # 4. outputs
    os.makedirs(out, exist_ok=True)
    np.savez(os.path.join(out, "selftest_solve.npz"), x1=x1, x2=x2)
    with open(os.path.join(out, "selftest_report.json"), "x", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("[selftest] pools %s" % [(p["prefix"], p["user_api"], p["num_threads"])
                                   for p in report["pools"]], flush=True)
    print("[selftest] memmap at %s; OK" % report["memmap_filename"], flush=True)


if __name__ == "__main__":
    main()
