"""Shared safety helpers. Import this at the top of every script that touches the SST table.

WHY THIS FILE EXISTS. Three scripts in this project froze the machine hard enough to require a power
cycle. The cause was not CPU load and not a bug in the maths -- it was this line, used on the 57
million row SST table:

    s["key"] = s.site_lat.round(4).astype(str) + "|" + s.site_lon.round(4).astype(str)

57 million Python strings at roughly 70 bytes each is about 4 GB, and the concatenation holds several
temporaries live at once. This machine has 15.8 GB of RAM and its page file is D:\\pagefile.sys on a
MECHANICAL ST500LM021 -- so once the working set exceeds RAM, Windows pages to a spinning disk at
random-4K speeds and the entire system stops responding rather than the process simply dying. There
is no crash dump because nothing crashed; it just stopped.

THE RULES THIS FILE ENFORCES.
  1. site_key() encodes a site as ONE int64 instead of a string. 8 bytes per row, no object array,
     no temporaries. Use it everywhere a per-site key is needed.
  2. guard() aborts the process cleanly while free memory is still healthy, so a runaway allocation
     raises instead of freezing the desktop. Call it inside any loop over a large table.
  3. cap_threads() limits BLAS and joblib to a few of the 16 logical cores. n_jobs=-1 is banned:
     saturating every core on this notebook chassis is what turned a slow job into an unusable one.

None of this changes any result. It changes only how the work is held in memory.
"""
import ctypes
import os


def cap_threads(n=4):
    """Call BEFORE importing numpy/pandas/sklearn. 4 of 16 leaves the machine usable."""
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[v] = str(n)
    return n


class _MEM(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_gb():
    s = _MEM()
    s.dwLength = ctypes.sizeof(_MEM)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    return s.ullAvailPhys / 1e9, s.ullTotalPhys / 1e9


def mem_str():
    a, t = free_gb()
    return "free %.1f/%.1f GB" % (a, t)


def guard(limit_gb=2.5, where=""):
    """Abort while the desktop is still responsive.

    Below roughly 2.5 GB free this machine starts paging to the mechanical D: drive, and from there
    it does not recover in usable time. Raising here costs a re-run; not raising costs a power cycle.
    """
    a, t = free_gb()
    if a < limit_gb:
        raise MemoryError("ABORT at %.1f GB free (limit %.1f) %s -- refusing to page onto the HDD%s"
                          % (a, limit_gb, where, _hogs()))
    return a


def _hogs(n=3):
    """Name the biggest memory consumers in the abort message.

    Without this the abort reads as "the script leaked" and sends you debugging the wrong thing.
    The 2026-08 stage-3c abort was Opera holding 7.7 GB while the pipeline itself used 1.1 GB, and
    that took a profiling run to establish. Best-effort only: never let the diagnostic raise and
    mask the real MemoryError.
    """
    try:
        import os
        import psutil
        me = os.getpid()
        agg = {}
        for p in psutil.process_iter(["name", "memory_info", "pid"]):
            try:
                agg[p.info["name"]] = agg.get(p.info["name"], 0) + p.info["memory_info"].rss
            except Exception:
                pass
        top = sorted(agg.items(), key=lambda x: -x[1])[:n]
        mine = psutil.Process(me).memory_info().rss / 1e9
        return ("\n  this process holds %.2f GB; biggest consumers overall: %s"
                "\n  if none of these is this script, close them and re-run -- it is resumable"
                % (mine, ", ".join("%s %.2f GB" % (k, v / 1e9) for k, v in top)))
    except Exception:
        return ""


def site_key(lat, lon, dp=4):
    """One int64 per site instead of a string. 8 bytes/row and no object array.

    Scales to 1e-4 degrees (~11 m, finer than the 5 km pixel) and offsets to keep both halves
    positive so the composite stays monotonic and collision-free within +-180.
    """
    import numpy as np
    s = 10 ** dp
    a = np.rint((np.asarray(lat, dtype="float64") + 90.0) * s).astype("int64")
    b = np.rint((np.asarray(lon, dtype="float64") + 180.0) * s).astype("int64")
    return a * (360 * s + 1) + b
