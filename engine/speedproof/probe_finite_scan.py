"""Why threaded tree prediction does not speed up inside pm25_adaptation (SPEEDPROOF_REPORT.md, finding 1).

Builds the real PM2.5 smoke rows with the shipped modules (8 donors / 3 test, 40 cells), fits a 400-tree
bank with the shipped recipe (8 donors x 50 trees, seeds 7000 + e*17 + j and 700 + j), and times one
12,288-row block laid out exactly as the script lays it out (pandas .values -> float32 -> vstack, which is
FORTRAN-ordered, so each row block is non-contiguous). Four ways, each at 1 and 8 threads, each checked
byte for byte against the shipped serial loop:
    shipped    t.predict(V) per tree (sklearn's input checks, incl. daal4py's finiteness scan)
    shipped_C  the same on a C-contiguous copy of the block
    af         finiteness scan ONCE per block, trees under sklearn's thread-local assume_finite
    af_C       af on a C-contiguous copy
Then profiles 100 shipped predict() calls. Writes nothing but a temp pool in D:/treeroute/speedproof/tmp,
deleted at the end.   Run:  py -3.9 probe_finite_scan.py        (about 2-5 minutes, mostly the pool)

GUARD CHECKS (added 2026-09-28 after review; what an engine guard test for option (a) would assert):
    G-a  the once-per-block path is byte-identical to the shipped per-tree predict (the table above);
    G-b  an inf injected into the block makes the ONCE-PER-BLOCK scan raise, as the shipped per-tree
         predict does -- and a predict under assume_finite alone does NOT raise, which is why the scan
         must never be skipped;
    G-c  a NaN behaves the same way in both paths (both raise, or both pass), and the library versions
         the result depends on are printed (sklearn's private _assert_all_finite /
         _support_missing_values and its thread-local config, as patched by sklearnex/daal4py).
The pool is named pool_probe_<pid>.f32, so the speedproof copy's orphan check (tmp/pool_*.f32) sees a
live probe and refuses to start beside it; the probe likewise refuses to start while any matrix or pool
file sits in tmp/ or D:/pm25.
"""
import io
import os
import sys
import time
import cProfile
import pstats

_PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT)
sys.argv = ["pm25_adaptation.py", "--smoke"]
import pm25_adaptation as M            # noqa: E402  module-level imports only (the script's process state)
import numpy as np                     # noqa: E402
import pandas as pd                    # noqa: E402
import sklearn                         # noqa: E402
import sklearn.utils.validation as skval   # noqa: E402
from concurrent.futures import ThreadPoolExecutor   # noqa: E402

import glob                            # noqa: E402

PA, SPLIT = M.PA, M.SPLIT
TMP = "D:/treeroute/speedproof/tmp"
_stale = sorted(glob.glob(TMP + "/A_*.f32") + glob.glob(TMP + "/pool_*.f32")
                + glob.glob("D:/pm25/A_*.f32") + glob.glob("D:/pm25/pool_*.f32"))
if _stale:
    raise SystemExit("probe_finite_scan: refusing to start, matrix/pool files exist (a run may be "
                     "alive):\n  " + "\n  ".join(_stale))
os.makedirs(TMP, exist_ok=True)
# pool_* so the copy's orphan glob (TMP_DIR/pool_*.f32) matches a live probe
PA.POOL = TMP + "/pool_probe_%d.f32" % os.getpid()
donors, tests = list(SPLIT.DONORS)[:8], list(SPLIT.TEST)[:3]
PA.N_CELLS = 40
try:
    mm, nrows, feat, meta = PA.build_pool(n_cells=40, regions=donors + tests)
    meta["cell"] = pd.factorize(meta.cell_id.values)[0].astype(np.int64)
    don = PA.gather(mm, feat, meta, np.flatnonzero(meta.reg.isin(donors).values
                                                  & (meta.year.values <= 2019)))
    hist = PA.gather(mm, feat, meta, np.flatnonzero(meta.reg.isin(tests).values
                                                   & (meta.year.values <= 2019)))
    del mm
finally:
    PA.cleanup()
don = don.sort_values(["cell", "t"]).reset_index(drop=True)
hist = hist.sort_values(["cell", "t"]).reset_index(drop=True)
don["ecoid"] = don.reg.map({r: i for i, r in enumerate(donors)})
Vd = don[feat].fillna(0).values.astype(np.float32)
yd = don.y.values.astype(np.float64)
trees = []
for e, g in don.groupby("ecoid"):
    gi = np.flatnonzero(don.ecoid.values == e)
    n = len(gi)
    take = max(30, int(0.5 * n))
    for j in range(50):
        idx = np.random.RandomState(7 * 1000 + int(e) * 17 + j).choice(n, size=take, replace=True)
        trees.append(M.DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.1,
                                             random_state=700 + j).fit(Vd[gi][idx], yd[gi][idx]))
NT = len(trees)
Vm = np.vstack([hist[feat].fillna(0).values.astype(np.float32)] * 2)    # the script's layout
V_F = Vm[0:12288]
print("bank %d trees | block %s | C-contiguous %s | parent F-ordered %s | finiteness scan: %s"
      % (NT, V_F.shape, V_F.flags.c_contiguous, Vm.flags.f_contiguous,
         skval._assert_all_finite.__module__))


def run(Vsrc, nw, mode):
    buf = np.empty((len(Vsrc), NT), np.float32)
    t0 = time.time()
    V = np.ascontiguousarray(Vsrc) if mode.endswith("_C") else Vsrc
    af = mode.startswith("af")
    if af:
        skval._assert_all_finite(V, allow_nan=trees[0]._support_missing_values(V), input_name="X")

    def fill(lo, hi):
        if af:
            with sklearn.config_context(assume_finite=True):
                for j in range(lo, hi):
                    buf[:, j] = trees[j].predict(V).astype(np.float32)
        else:
            for j in range(lo, hi):
                buf[:, j] = trees[j].predict(V).astype(np.float32)
    cuts = [NT * i // nw for i in range(nw + 1)]
    if nw == 1:
        fill(0, NT)
    else:
        with ThreadPoolExecutor(nw) as ex:
            for f in [ex.submit(fill, cuts[i], cuts[i + 1]) for i in range(nw)]:
                f.result()
    return buf, time.time() - t0


ref, ref_t = run(V_F, 1, "shipped")
ALL_SAME = True
for mode in ("shipped", "shipped_C", "af", "af_C"):
    b1, t1 = run(V_F, 1, mode)
    b8, t8 = run(V_F, 8, mode)
    same = (np.array_equal(ref.view(np.uint32), b1.view(np.uint32))
            and np.array_equal(ref.view(np.uint32), b8.view(np.uint32)))
    print("%-10s 1 thread %.2f s | 8 threads %.2f s | threads %.1fx | vs shipped serial %.1fx | "
          "byte-identical: %s" % (mode, t1, t8, t1 / t8, ref_t / t8, same))
    ALL_SAME &= bool(same)

pr = cProfile.Profile()
pr.enable()
for t in trees[:100]:
    t.predict(V_F)
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(6)
print(s.getvalue()[:2500])


# ------------------------------------------------------------------ guard checks G-b / G-c
def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


def _scan(V):
    skval._assert_all_finite(V, allow_nan=trees[0]._support_missing_values(V), input_name="X")


def _assume_finite_predict(V):
    with sklearn.config_context(assume_finite=True):
        trees[0].predict(V)


GUARD_OK = ALL_SAME
for label, bad in (("inf", np.inf), ("nan", np.nan)):
    Vb = np.array(V_F, copy=True, order="F")          # the script's (Fortran) layout
    Vb[len(Vb) // 2, Vb.shape[1] // 3] = bad
    shipped_raises = _raises(lambda: trees[0].predict(Vb))
    scan_raises = _raises(lambda: _scan(Vb))
    af_raises = _raises(lambda: _assume_finite_predict(Vb))
    same = shipped_raises == scan_raises
    GUARD_OK &= same and (label != "inf" or scan_raises)
    print("guard %-3s injected: shipped per-tree predict raises %-5s | once-per-block scan raises %-5s"
          " | predict under assume_finite alone raises %-5s | scan matches shipped: %s"
          % (label, shipped_raises, scan_raises, af_raises, same))
import sklearnex                       # noqa: E402
try:
    from importlib.metadata import version as _ver
    _sx = _ver("scikit-learn-intelex")
except Exception:                      # noqa: BLE001
    _sx = getattr(sklearnex, "__version__", "?")
print("versions: scikit-learn %s | scikit-learn-intelex %s | numpy %s | scan function %s.%s"
      % (sklearn.__version__, _sx, np.__version__, skval._assert_all_finite.__module__,
         skval._assert_all_finite.__name__))
print("GUARD (byte-identity above + inf raises in the once-per-block scan + nan behaves as shipped): "
      "%s" % ("PASS" if GUARD_OK else "FAIL"))
