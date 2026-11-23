"""Region replay gate (plan 4.4; M3 gate 'Defo replay = cached link_corrector arrays with matching row
counts'; owner ruling C 'Region-router threads': a 4-thread mode with a 1e-9 match tolerance against its
golden).

Outside the product: the engine never imports this file (G-IMPORT). It may name problems, years and
drives; the engine may not.

WHAT IT PROVES
  The engine's region solver (treeroute.route.region: region_gram, region_ridge, region_predict), run in
  LEGACY mode -- no normal column, the shipped row linspace cap, the shipped lambda -- on the defo
  nowcast's SHIPPED banks reproduces the cached link_corrector arrays that add_linkcorr.py wrote into
  D:/adaptation/defo/<region>_c4000.npz (keys link_corrector and inner_link_corrector), with matching
  row counts, within GATE_TOLERANCE (1e-9, y units), with BLAS at the engine's BLAS_THREADS (4).
  The inputs are built by the SHIPPED CODE ITSELF, cut out of the shipped files as text (their sha256
  are recorded; add_linkcorr.py's must equal the golden registry's) and executed in an isolated
  namespace, never re-typed:
      defo_train.py      load_split, feature_cols, extra_cols, load_region (D:/defo_matrix, read-only)
      defo_corrector.py  bpath (the pair-bank names; D:/defo_corrector/banks, read-only)
      add_linkcorr.py    stack, form, LINK_G, LINK_I, the constants line, the donor block and the row
                         block of main() (ti with the linspace cap, te, i_fit, i_sc and its two asserts)
  ONE SOURCE IS NOT TODAY'S TEXT: defo_train.load_region. The caches were written on 2026-09-13
  (D:/adaptation/defo/_addarm.log; the files' times); defo_train.py was edited on 2026-09-22 to mask
  the panel's NoData sentinels inside load_region (import panel_sentinel; _ps.mask(d);
  panel_sentinel.py dates from 2026-09-23). Today's load_region therefore feeds the trees other X
  values than the run that wrote the caches (measured: max |engine - cache| 1.4e-4 on costa_rica).
  The load_region that ran is preserved as bytecode: python's own cache of defo_train.py,
  __pycache__/defo_train.cpython-39.pyc, whose header records the source it was compiled from
  (mtime 2026-09-07 12:22:30, 22,398 bytes: before the caches). A copy is kept beside this file
  (defo_train_cachetime.cpython-39.pyc, sha256 pinned below), because any later import of
  defo_train under python 3.9 would recompile the original. The harness takes load_region's code
  object from that copy and checks, before use: the header's source time precedes every cache; the
  other three defo_train functions are bytecode-identical to today's text; and today's load_region
  differs from it only by the two sentinel names (panel_sentinel, mask). add_linkcorr.py was also
  edited after the caches (2026-09-14, its report section); its cache-time bytecode (the copy
  add_linkcorr_cachetime.cpython-39.pyc, compiled from the source of 2026-09-13 22:19:00, the run's
  own start) is checked instead: stack, form, LINK_G and LINK_I are bytecode-identical, and so are
  the instructions of every source line of the donor block and the row block of main().
  Only the ridge is replaced: the shipped
      wb = S.ridge(q, LINK_G(y), ti, LAM);  link_corrector = clip(LINK_I(S.apply(q, wb)), 0, 1)[te]
  becomes, with lam = region_lambda(region_centre()) (== LAM, asserted),
      gram = region_gram(q[ti]); fit = region_ridge(gram, LINK_G(y)[ti], lam); p = region_predict(fit, q)
  (and the same on i_fit for inner_link_corrector). q is formed exactly as add_linkcorr.py formed it
  (eta = 1.0, the ungated corrector), and predictions are made on ALL rows of q, as the shipped apply
  did, before the test / inner rows are taken.
  INFORMATION (not the gate):
    --info-threads=N (default 16, this machine's unpinned OpenBLAS thread count, the state the shipped run
        was launched in): the same engine solve at N BLAS threads, compared with the cache. MEASURED
        2026-09-29 (D:/treeroute/region_build/two_regions_1): at 16 threads the engine reproduces the cache
        BYTE FOR BYTE on costa_rica (no cap; 10,172 + 7,629 rows) and greece_mainland (the shipped linspace
        cap, 60,000 fit rows; 16,000 + 8,000 rows); at 4 threads (the ruled mode) max |engine - cache| is
        8.4e-9 and 4.4e-8, above the ruled 1e-9. The gap is the float32 Gram: OpenBLAS splits its
        accumulation by thread count (on costa_rica, Gram at 16 and apply at 1 thread: 8.7e-10). So the
        ruled check fails by rounding the solver does not cause; the owner rules the tolerance or the gate's
        thread count (the report carries both numbers).
    --shipped-too: the shipped defo_softgate.ridge / apply on the same q at the gate's threads, compared
        with the engine byte for byte, and with the cache. MEASURED 2026-09-29 on costa_rica (the skeptic's
        re-run): at 4 threads the shipped code gives the engine's w and predictions byte for byte, and is
        itself 8.43e-9 from its own cache; so the 4-thread gap is the thread count the cache was written at
        (16, unpinned), not the engine. The owner chooses the golden (see the task report): the shipped code
        at 4 threads (passes at 0), the cache at 16 threads (byte-exact), or the cache at 4 threads with a
        measured tolerance.

FENCES
  - Read-only on every store: D:/defo_matrix, D:/defo_corrector/banks, D:/adaptation/defo, D:/run89full.
    The protected roots (D:/treeroute/registry/protected_roots.txt) and D:/defo_matrix are snapshotted
    (size and mtime of every file) before and after; any change fails the run (exit 5).
  - Nothing is written except <out-dir>/report.json, <out-dir>/console.txt and the row-level arrays
    <out-dir>/predictions/<region>.npz (per key link_corrector / inner_link_corrector: __cell_id, __year,
    __y, __cache, __engine_4threads, and __engine_<N>threads / __shipped_4threads when run; the report
    records each file's sha256); <out-dir> is a NEW folder strictly under D:/treeroute/region_build/.
    No temp file: everything else stays in RAM.
  - Threads: BLAS 4 (the engine's region 4-thread mode, owner ruling C) and OpenMP 4, set before numpy
    loads; the engine solve runs inside threadpoolctl's BLAS limit at BLAS_THREADS, checked on entering
    and leaving. Tree prediction uses no BLAS.
  - Refuses to start (exit 2) beside another heavy python job, below MIN_AVAIL_GB of available RAM, if
    add_linkcorr.py, a cache file or a pair bank differs from the golden registry (every pair bank by its
    sha256, about 0.8 GB read; --size-only-banks checks sizes only, for a smoke, and the report says so;
    --deep-banks, the old opt-in, is accepted and is the default), or if <out-dir> exists.
    The cache-time load_region must equal today's with its two sentinel lines removed, instruction for
    instruction (check_load_region_is_cache_time_plus_mask), not only by the names it uses.
    Before each region a RAM guard estimates that region's peak and refuses (exit 2, report kept) if it
    does not fit.

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine\\legacy_harness"
    py -3.9 -u region_replay.py --out-dir=D:/treeroute/region_build/run1                 # all 17 regions (~1.5 h)
    py -3.9 -u region_replay.py --out-dir=D:/treeroute/region_build/run2 --shipped-too   # + the shipped code
    py -3.9 -u region_replay.py --out-dir=D:/treeroute/region_build/smoke1 --only=costa_rica --shipped-too
    py -3.9 -u region_replay.py --out-dir=D:/treeroute/region_build/x --check-only       # pre-flight only

Exit codes: 0 every replayed region passes; 1 a gate failed; 2 refused; 5 a protected file changed.
"""
import ast
import gc
import glob
import hashlib
import json
import os
import re
import sys
import textwrap
import time
import traceback
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
PROJECT = os.path.dirname(ENGINE)
BUILD_ROOT = "D:/treeroute/region_build"
PROTECTED_LIST = "D:/treeroute/registry/protected_roots.txt"
WATCH_EXTRA = ("D:/defo_matrix",)
GOLDEN_ID = "defo_link_corrector"
CACHE_GLOB = "D:/adaptation/defo/*_c4000.npz"
GATE_TOLERANCE = 1e-9                     # owner ruling C: 1e-9 against its golden (y units)
MIN_AVAIL_GB = 3.0
GB = float(1 << 30)

ENV_PINS = {"OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4", "BLIS_NUM_THREADS": "4",
            "VECLIB_MAXIMUM_THREADS": "4", "OMP_NUM_THREADS": "4", "NUMEXPR_NUM_THREADS": "4"}
NUMERIC_MODULES = ("numpy", "scipy", "sklearn", "sklearnex", "daal4py", "onedal", "pandas")
HEAVY_MARKERS = ("pm25_adaptation", "adaptation.py", "adaptation_rooted", "launch_pinned",
                 "run_shipped_blas1", "bank_replay", "router_replay", "layer_replay", "region_replay",
                 "pm25_forecast", "pm25_rivals", "fire_architecture", "fire_evt_arch", "coral_architecture",
                 "add_linkcorr", "defo_", "build_store", "treeroute smoke", "-m treeroute")

# the cache-time bytecode copies (see the module docstring) and their pinned sha256
TRAIN_PYC = os.path.join(HERE, "defo_train_cachetime.cpython-39.pyc")
TRAIN_PYC_SHA256 = "4dbcb8b21f7dbe1979784f44a2c35b197d57703fbe597c2330d10b55d3daa6db"
TRAIN_PYC_SOURCE = ("2026-09-07 12:22:30", 22398)
ADD_PYC = os.path.join(HERE, "add_linkcorr_cachetime.cpython-39.pyc")
ADD_PYC_SHA256 = "c041a879eb70b1b13d245abc8a8ebde69b574d9c6e69f7588d2c67af0e2ef528"
ADD_PYC_SOURCE = ("2026-09-13 22:19:00", 12113)

TRAIN = os.path.join(PROJECT, "defo_train.py")
CORR = os.path.join(PROJECT, "defo_corrector.py")
ADD = os.path.join(PROJECT, "add_linkcorr.py")
SOFT = os.path.join(PROJECT, "defo_softgate.py")

# add_linkcorr.py's main(): the donor block and the row block, cut out by exact first and last line
BLOCK_DONORS = ('    donors, tests = T.load_split()',
                '    pair = [C.bpath("pair", d) for d in donors]')
BLOCK_ROWS = ('        meta, X = T.load_region(reg, cols, cap=CELLS)',
              '        assert len(z["inner_y"]) == len(i_sc), "cached inner rows differ for %s" % reg')
CONSTANTS_LINE = "CELLS, REGROWS, LAM, INNER, BLK = "


class Refused(Exception):
    pass


# ---------------------------------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(p):
    return os.path.normcase(os.path.abspath(p)).replace("\\", "/").rstrip("/")


def is_under(path, root):
    p, r = norm(path), norm(root)
    return p == r or p.startswith(r + "/")


def newest_registry():
    best, best_v = os.path.join(HERE, "goldens.json"), 1
    for path in glob.glob(os.path.join(HERE, "goldens_v*.json")):
        m = re.match(r"goldens_v(\d+)\.json$", os.path.basename(path))
        if m and int(m.group(1)) > best_v:
            best, best_v = path, int(m.group(1))
    with open(best, encoding="utf-8") as f:
        return best, json.load(f)


def protected_roots():
    with open(PROTECTED_LIST, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]


def snapshot(roots):
    snap = {}
    for root in roots:
        if not os.path.isdir(root):
            snap[norm(root)] = "absent"
            continue
        for dirpath, _dirs, files in os.walk(root):
            try:
                snap["dir:" + norm(dirpath)] = os.stat(dirpath).st_mtime_ns
            except OSError:
                pass
            for fn in files:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                    snap[norm(p)] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    snap[norm(p)] = "unreadable"
    return snap


def heavy_jobs():
    import psutil
    me = os.getpid()
    out = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
        try:
            if proc.info["pid"] == me or "python" not in (proc.info["name"] or "").lower():
                continue
            cmd = " ".join(proc.info["cmdline"] or [])
            rss = proc.info["memory_info"].rss / GB if proc.info["memory_info"] else 0.0
            if any(mark in cmd for mark in HEAVY_MARKERS) or rss > 1.0:
                out.append("%d (%.1f GB): %s" % (proc.info["pid"], rss, cmd[:160]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def avail_gb():
    import psutil
    return psutil.virtual_memory().available / GB


def cut_block(text, first, last):
    lines = text.split("\n")
    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\r") == first]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r") == last]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise Refused("block %r..%r not found exactly once (%d / %d hits)"
                      % (first.strip(), last.strip(), len(starts), len(ends)))
    block = "\n".join(ln.rstrip("\r") for ln in lines[starts[0]:ends[0] + 1]) + "\n"
    return textwrap.dedent(block), starts[0] + 1, ends[0] + 1


def function_source(text, name):
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(hits) != 1:
        raise Refused("function %s not found exactly once" % name)
    lines = text.split("\n")
    node = hits[0]
    return "\n".join(ln.rstrip("\r") for ln in lines[node.lineno - 1:node.end_lineno]) + "\n", node.lineno


def assignment_source(text, name):
    """The source of the top-level assignment to ``name`` (a lambda or a constant)."""
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    if len(hits) != 1:
        raise Refused("assignment %s not found exactly once" % name)
    lines = text.split("\n")
    node = hits[0]
    return "\n".join(ln.rstrip("\r") for ln in lines[node.lineno - 1:node.end_lineno]) + "\n", node.lineno


def pyc_module(path, want_sha, want_source):
    """(module code object, facts) of a python 3.9 bytecode cache file whose sha256 and recorded
    source (mtime, size) are pinned."""
    import marshal
    got = sha256_file(path)
    if got != want_sha:
        raise Refused("%s sha256 %s != pinned %s" % (path, got, want_sha))
    data = open(path, "rb").read()
    if data[:4] != bytes([0x61, 0x0D, 0x0D, 0x0A]):        # python 3.9's magic number
        raise Refused("%s is not a python 3.9 bytecode file" % path)
    flags = int.from_bytes(data[4:8], "little")
    mtime = int.from_bytes(data[8:12], "little")
    size = int.from_bytes(data[12:16], "little")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
    if flags != 0 or (stamp, size) != tuple(want_source):
        raise Refused("%s records the source %s (%d bytes, flags %d), pinned %s"
                      % (path, stamp, size, flags, want_source))
    return marshal.loads(data[16:]), {"file": path, "sha256": got, "source_mtime": stamp,
                                      "source_mtime_epoch": mtime, "source_size": size}


def code_functions(module_code):
    import types
    return {c.co_name: c for c in module_code.co_consts if isinstance(c, types.CodeType)}


def same_code(a, b):
    return (a.co_code == b.co_code and a.co_consts == b.co_consts and a.co_names == b.co_names
            and a.co_varnames == b.co_varnames)


def _normalised(ins):
    """(opname, argrepr) with code-object addresses, file names and lines, and jump targets removed (they
    move with any edit or with the name the source was compiled under); nested code objects are compared
    by instructions_except_lines."""
    arg = re.sub(r"<code object (\S+) at 0x[0-9a-fA-F]+(, file \"[^\"]*\", line \d+)?", r"<code object \1",
                 ins.argrepr)
    return ins.opname, re.sub(r"to \d+", "to ?", arg)


def instructions_in_lines(code, lo, hi):
    """(opname, normalised argrepr) of every instruction on source lines lo..hi of ``code``."""
    import dis
    out, line = [], None
    for ins in dis.get_instructions(code):
        if ins.starts_line is not None:
            line = ins.starts_line
        if line is not None and lo <= line <= hi:
            out.append(_normalised(ins))
    return out


def instructions_except_lines(code, skip=()):
    """(opname, normalised argrepr) of every instruction of ``code`` NOT on the source lines ``skip``,
    followed by the same list for every nested code object (comprehensions), in order."""
    import dis
    import types
    out, line = [], None
    for ins in dis.get_instructions(code):
        if ins.starts_line is not None:
            line = ins.starts_line
        if line not in skip:
            out.append(_normalised(ins))
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            out.append(("<nested>", c.co_name))
            out.extend(instructions_except_lines(c, skip))
    return out


# today's load_region masks the panel's NoData sentinels with exactly these two lines (defo_train.py, 2026-09-22)
SENTINEL_LINES = ("    import panel_sentinel as _ps", "    _ps.mask(d)")


def check_load_region_is_cache_time_plus_mask(old_code, new_code, text):
    """Today's load_region (``new_code``, compiled from ``text``) must be the cache-time one
    (``old_code``) plus the two SENTINEL_LINES and nothing else: the names they add are exactly
    panel_sentinel and mask, and with the instructions of those two source lines removed, today's
    instruction stream (nested comprehensions included) is the cache-time one. Returns the two line
    numbers; refuses otherwise."""
    added = sorted(set(new_code.co_names) - set(old_code.co_names))
    removed = sorted(set(old_code.co_names) - set(new_code.co_names))
    if added != ["mask", "panel_sentinel"] or removed:
        raise Refused("today's load_region differs from the cache-time one by more than the sentinel mask: "
                      "names added %s, removed %s" % (added, removed))
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "load_region")
    lines = text.split("\n")
    skip = []
    for want in SENTINEL_LINES:
        hits = [i + 1 for i in range(node.lineno - 1, node.end_lineno) if lines[i].rstrip("\r") == want]
        if len(hits) != 1:
            raise Refused("load_region holds the sentinel line %r %d times, not once" % (want.strip(), len(hits)))
        skip += hits
    if instructions_except_lines(old_code) != instructions_except_lines(new_code, set(skip)):
        raise Refused("today's load_region without its sentinel lines %s is not the cache-time bytecode" % skip)
    return skip


class Tee(object):
    def __init__(self, stream, fh):
        self.stream, self.fh = stream, fh

    def write(self, data):
        self.stream.write(data)
        self.fh.write(data)
        return len(data)

    def flush(self):
        self.stream.flush()
        self.fh.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


# ---------------------------------------------------------------------------------------------------
def preflight(out_dir, deep_banks):
    early = [m for m in NUMERIC_MODULES if m in sys.modules]
    if early:
        raise Refused("numeric modules loaded before the pins: %s" % early)
    if not is_under(out_dir, BUILD_ROOT) or norm(out_dir) == norm(BUILD_ROOT):
        raise Refused("--out-dir must be a sub-folder of %s" % BUILD_ROOT)
    if os.path.exists(out_dir):
        raise Refused("%s already exists; every run uses a new folder" % out_dir)
    roots = protected_roots()
    for root in roots:
        if is_under(out_dir, root):
            raise Refused("%s lies under the protected root %s" % (out_dir, root))
    reg_path, reg = newest_registry()
    golden = reg["goldens"][GOLDEN_ID]
    want_add = None
    for line in golden["produced_by"]:
        m = re.search(r"add_linkcorr\.py .*its sha256 now is ([0-9a-f]{64})", line)
        if m:
            want_add = m.group(1)
    if want_add is None:
        raise Refused("the registry records no add_linkcorr.py sha256")
    got_add = sha256_file(ADD)
    if got_add != want_add:
        raise Refused("add_linkcorr.py sha256 %s != registry %s" % (got_add, want_add))
    bad = []
    caches = {}
    for f in golden["files"]:
        if f.get("role") != "link_corrector cache":
            continue
        if not os.path.exists(f["path"]) or sha256_file(f["path"]) != f["sha256"]:
            bad.append(f["path"])
        caches[os.path.basename(f["path"])[:-len("_c4000.npz")]] = f
    if bad:
        raise Refused("cache files missing or changed: %s" % bad)
    on_disk = sorted(os.path.basename(p)[:-len("_c4000.npz")] for p in glob.glob(CACHE_GLOB)
                     if not os.path.basename(p).startswith("_"))
    if sorted(caches) != on_disk:
        raise Refused("registry caches %s != on disk %s" % (sorted(caches), on_disk))
    pairs = [b for b in golden["banks"]["files"] if b.get("role", "").startswith("pair bank")]
    if len(pairs) != 25:
        raise Refused("the registry lists %d pair banks, 25 expected" % len(pairs))
    bad = [b["path"] for b in pairs if not os.path.exists(b["path"]) or os.path.getsize(b["path"]) != b["size"]]
    if deep_banks:
        bad += [b["path"] for b in pairs if os.path.exists(b["path"]) and sha256_file(b["path"]) != b["sha256"]]
    if bad:
        raise Refused("pair banks missing or changed: %s" % bad)
    heavy = heavy_jobs()
    if heavy:
        raise Refused("another heavy python job is running: %s" % heavy)
    avail = avail_gb()
    if avail < MIN_AVAIL_GB:
        raise Refused("%.2f GB of RAM available, need %.1f" % (avail, MIN_AVAIL_GB))
    return {"registry": reg_path, "add_linkcorr_sha256": got_add, "caches_verified": len(caches),
            "pair_banks_checked": len(pairs), "pair_banks_sha256_checked": bool(deep_banks),
            "defo_train_sha256": sha256_file(TRAIN), "defo_corrector_sha256": sha256_file(CORR),
            "defo_softgate_sha256": sha256_file(SOFT), "ram_available_gb": round(avail, 2),
            "protected_roots": roots, "rows_per_region": golden["rows_per_region"],
            "pair_banks": {b["path"]: b["sha256"] for b in pairs}}


def pin_threads():
    for k, v in ENV_PINS.items():
        os.environ[k] = v
    import numpy  # noqa: F401  (after the pins, on purpose)
    import scipy.linalg  # noqa: F401  (loads scipy's own BLAS under the same pin)
    import threadpoolctl
    return [{k: d.get(k) for k in ("user_api", "internal_api", "num_threads")}
            for d in threadpoolctl.threadpool_info()]


def shipped_namespace(report):
    """The shipped functions and blocks, executed from their source text in one namespace."""
    import numpy as np
    import pandas as pd
    import pickle

    for path, want in ((TRAIN_PYC, TRAIN_PYC_SHA256), (ADD_PYC, ADD_PYC_SHA256)):
        if not os.path.isfile(path):
            raise Refused("the cache-time bytecode copy %s is missing" % path)
    if PROJECT not in sys.path:
        sys.path.insert(0, PROJECT)            # load_region imports panel_sentinel from the project root
    t_train = open(TRAIN, encoding="utf-8").read()
    t_corr = open(CORR, encoding="utf-8").read()
    t_add = open(ADD, encoding="utf-8").read()
    t_soft = open(SOFT, encoding="utf-8").read()
    src = {}
    T = {"np": np, "pd": pd, "os": os, "glob": glob, "gc": gc, "sys": sys,
         "MAT": "D:/defo_matrix", "SPLIT": "D:/run89full/ndvi_split.txt",
         "MASK": {"cell_id", "year", "y", "forest2000_px", "land_px", "is_train"}, "EXTRA": ""}
    import types
    cache_mtime = min(os.path.getmtime(p) for p in glob.glob(CACHE_GLOB))
    old_train, train_info = pyc_module(TRAIN_PYC, TRAIN_PYC_SHA256, TRAIN_PYC_SOURCE)
    if train_info["source_mtime_epoch"] >= cache_mtime:
        raise Refused("the cache-time defo_train bytecode was compiled from a source newer than the caches")
    old_fn = code_functions(old_train)
    new_fn = code_functions(compile(t_train, "defo_train.py", "exec"))
    for name in ("load_split", "feature_cols", "extra_cols"):
        if not same_code(old_fn[name], new_fn[name]):
            raise Refused("defo_train.%s differs from its cache-time bytecode" % name)
        code, line = function_source(t_train, name)
        src["defo_train.%s" % name] = line
        exec(compile(code, "defo_train.py:%s" % name, "exec"), T)
    a, b = old_fn["load_region"], new_fn["load_region"]
    train_info["todays_sentinel_lines_removed"] = check_load_region_is_cache_time_plus_mask(a, b, t_train)
    sig =next(n for n in ast.parse(t_train).body if isinstance(n, ast.FunctionDef) and n.name == "load_region")
    if [ast.literal_eval(d) for d in sig.args.defaults] != [None, False] or \
            [x.arg for x in sig.args.args] != list(a.co_varnames[:a.co_argcount]):
        raise Refused("load_region's signature is not (reg, cols, cap=None, train_only=False)")
    T["load_region"] = types.FunctionType(a, T, "load_region", (None, False))
    src["defo_train.load_region"] = "cache-time bytecode %s (source %s, %d bytes)" % (
        os.path.basename(TRAIN_PYC), train_info["source_mtime"], train_info["source_size"])
    report["cache_time_bytecode"] = {"defo_train": train_info}
    for name in ("MAT", "SPLIT", "MASK"):
        code, line = assignment_source(t_train, name)
        chk = {}
        exec(compile(code, "defo_train.py:%s" % name, "exec"), chk)
        if chk[name] != T[name]:
            raise Refused("defo_train.py %s is %r, the harness assumed %r" % (name, chk[name], T[name]))
    C = {"os": os, "BANK": "D:/defo_corrector/banks", "ARM": "hist", "NT": 250, "MF": 15, "CDEPTH": 12,
         "LEAD": 0, "CRIT": "squared_error", "NDON": 25}
    code, line = function_source(t_corr, "bpath")
    src["defo_corrector.bpath"] = line
    exec(compile(code, "defo_corrector.py:bpath", "exec"), C)
    # the defaults the harness assumed are the shipped file's _a defaults
    defaults = {"NT": ("--ntrees", 250), "MF": ("--maxfeatures", 15), "NDON": ("--donors", 25),
                "ARM": ("--arm", "hist"), "CDEPTH": ("--cdepth", 12), "LEAD": ("--lead", 0),
                "CRIT": ("--criterion", "squared_error")}
    for key, (flag, value) in defaults.items():
        if not re.search(r'^%s\s*=\s*T\._a\("%s", %r' % (key, re.escape(flag), value), t_corr, re.M) \
                and not re.search(r'^%s\s*=\s*T\._a\("%s", "%s"' % (key, re.escape(flag), value), t_corr, re.M):
            raise Refused("defo_corrector.py: %s is not T._a(%r, %r)" % (key, flag, value))
    A = {"np": np, "pd": pd, "pickle": pickle, "gc": gc, "BLK": None}
    for name in ("stack", "form"):
        code, line = function_source(t_add, name)
        src["add_linkcorr.%s" % name] = line
        exec(compile(code, "add_linkcorr.py:%s" % name, "exec"), A)
    for name in ("LINK_G", "LINK_I"):
        code, line = assignment_source(t_add, name)
        src["add_linkcorr.%s" % name] = line
        exec(compile(code, "add_linkcorr.py:%s" % name, "exec"), A)
    const = [ln for ln in t_add.split("\n") if ln.startswith(CONSTANTS_LINE)]
    if len(const) != 1:
        raise Refused("add_linkcorr.py's constants line not found exactly once")
    exec(compile(const[0].rstrip("\r") + "\n", "add_linkcorr.py:constants", "exec"), A)
    donors_code, d0, d1 = cut_block(t_add, *BLOCK_DONORS)
    rows_code, r0, r1 = cut_block(t_add, *BLOCK_ROWS)
    old_add, add_info = pyc_module(ADD_PYC, ADD_PYC_SHA256, ADD_PYC_SOURCE)
    if add_info["source_mtime_epoch"] >= cache_mtime:
        raise Refused("the cache-time add_linkcorr bytecode was compiled from a source newer than the caches")
    old_a = code_functions(old_add)
    new_mod = compile(t_add, "add_linkcorr.py", "exec")
    new_a = code_functions(new_mod)
    for name in ("stack", "form"):
        if not same_code(old_a[name], new_a[name]):
            raise Refused("add_linkcorr.%s differs from its cache-time bytecode" % name)
    lam_old = [c for c in old_add.co_consts if getattr(c, "co_name", "") == "<lambda>"]
    lam_new = [c for c in new_mod.co_consts if getattr(c, "co_name", "") == "<lambda>"]
    if len(lam_old) != 2 or len(lam_new) != 2 or not all(same_code(x, y) for x, y in zip(lam_old, lam_new)):
        raise Refused("add_linkcorr's LINK_G / LINK_I differ from their cache-time bytecode")
    if [c for c in old_add.co_consts if isinstance(c, tuple) and 4000 in c] != [(4000, 60000, 100.0, 2016, 20000)]:
        raise Refused("add_linkcorr's cache-time constants are not (4000, 60000, 100.0, 2016, 20000)")
    for lo, hi, what in ((d0, d1, "donor block"), (r0, r1, "row block")):
        got_old = instructions_in_lines(old_a["main"], lo, hi)
        if not got_old or got_old != instructions_in_lines(new_a["main"], lo, hi):
            raise Refused("add_linkcorr main()'s %s (lines %d-%d) differs from its cache-time bytecode"
                          % (what, lo, hi))
    report["cache_time_bytecode"]["add_linkcorr"] = add_info
    src["add_linkcorr.main donor block"] = [d0, d1]
    src["add_linkcorr.main row block"] = [r0, r1]
    S = {"np": np, "gc": gc}
    for name in ("ridge", "apply"):
        code, line = function_source(t_soft, name)
        src["defo_softgate.%s" % name] = line
        exec(compile(code, "defo_softgate.py:%s" % name, "exec"), S)
    report["shipped_source_lines"] = src
    report["shipped_constants"] = {k: A[k] for k in ("CELLS", "REGROWS", "LAM", "INNER", "BLK")}
    ns = SimpleNamespace(T=SimpleNamespace(**{k: T[k] for k in ("load_split", "feature_cols", "load_region")}),
                         C=SimpleNamespace(NDON=C["NDON"], ARM=C["ARM"], bpath=C["bpath"]),
                         A=A, S=S, donors_code=donors_code, rows_code=rows_code)
    return ns


def donor_block(ns):
    import numpy as np
    import pandas as pd
    env = {"T": ns.T, "C": ns.C, "pd": pd, "np": np}
    exec(compile(ns.donors_code, "add_linkcorr.py:main donors", "exec"), env)
    return env["donors"], env["cols"], env["pair"]


def row_block(ns, reg, cols, z):
    import numpy as np
    env = {"T": ns.T, "np": np, "reg": reg, "cols": cols, "z": z}
    for k in ("CELLS", "REGROWS", "INNER"):
        env[k] = ns.A[k]
    exec(compile(ns.rows_code, "add_linkcorr.py:main rows", "exec"), env)
    return env


def compare(engine, cache):
    import numpy as np
    e = np.asarray(engine, dtype=np.float64)
    c = np.asarray(cache, dtype=np.float64)
    if e.shape != c.shape:
        return {"rows_engine": int(e.size), "rows_cache": int(c.size), "rows_match": False, "pass": False}
    d = np.abs(e - c)
    return {"rows_engine": int(e.size), "rows_cache": int(c.size), "rows_match": True,
            "max_abs_diff": float(d.max()) if d.size else 0.0,
            "n_bytes_equal": int(np.count_nonzero(e.view(np.uint64) == c.view(np.uint64))),
            "pass": bool(d.size == 0 or float(d.max()) <= GATE_TOLERANCE)}


def replay_region(ns, reg, cols, pair, shipped_too, log, info_threads=None, out_dir=None):
    """One region's gate; with out_dir, its row-level arrays go to <out_dir>/predictions/<reg>.npz."""
    import numpy as np
    from threadpoolctl import threadpool_info, threadpool_limits

    from treeroute import engine_constants as K
    from treeroute.route import region as RG

    path = "D:/adaptation/defo/%s_c4000.npz" % reg
    with np.load(path, allow_pickle=False) as f:
        z = {k: f[k] for k in ("y", "inner_y", "link_corrector", "inner_link_corrector")}
    t0 = time.time()
    env = row_block(ns, reg, cols, z)             # load_region + the row sets + the shipped asserts
    meta, X, y, n = env["meta"], env["X"], env["y"], env["n"]
    ti, te, i_fit, i_sc = env["ti"], env["te"], env["i_fit"], env["i_sc"]
    out = {"rows": int(n), "fit_rows": int(len(ti)), "test_rows": int(len(te)), "inner_fit_rows": int(len(i_fit)),
           "inner_score_rows": int(len(i_sc)),
           "linspace_cap_applied": bool(int(((meta.is_train.to_numpy() == 1) & np.isfinite(y)).sum())
                                        > ns.A["REGROWS"]),
           "y_test_equals_cache": bool(np.array_equal(np.asarray(y[te], dtype=np.float64),
                                                      np.asarray(z["y"], dtype=np.float64))),
           "y_inner_equals_cache": bool(np.array_equal(np.asarray(y[i_sc], dtype=np.float64),
                                                       np.asarray(z["inner_y"], dtype=np.float64)))}
    c = len(pair) * 250                           # columns of q: one per (base, corrector) pair
    peak = max(2 * n * c * 2 + n * c * 4,         # Pm and Cm (float16) while q (float32) is formed
               n * c * 4 + len(ti) * c * 4 + 3 * c * c * 8)      # q, the fit rows, the Gram copies
    if shipped_too:                               # the shipped ridge holds two copies of the fit rows
        peak = max(peak, n * c * 4 + 2 * len(ti) * c * 4 + 2 * c * c * 8)
    need = (peak + 2 * X.nbytes) / GB + 0.3
    have = avail_gb()
    out["ram_needed_gb"], out["ram_available_gb"] = round(need, 2), round(have, 2)
    if have < need:
        raise Refused("%s needs about %.1f GB of RAM, %.1f GB available" % (reg, need, have))
    Pm = ns.A["stack"](pair, X, n, "base")
    Cm = ns.A["stack"](pair, X, n, "corr")
    q = ns.A["form"](Pm, Cm, 1.0, n)
    del Pm, Cm, X
    gc.collect()
    out["columns"] = int(q.shape[1])
    out["stack_minutes"] = round((time.time() - t0) / 60, 2)
    gy = ns.A["LINK_G"](y)
    lam = RG.region_lambda(RG.region_centre())
    if lam != ns.A["LAM"]:
        raise Refused("the engine's region centre lambda %r is not the shipped LAM %r" % (lam, ns.A["LAM"]))
    limit = int(K.BLAS_THREADS)
    preds = {}
    rows_saved = {}                               # row-level arrays (the save-predictions rule)
    cell_ids = meta.cell_id.astype(str).to_numpy()
    years = meta.year.to_numpy().astype(np.int64)
    with threadpool_limits(limits=limit, user_api="blas"):
        seen = sorted({d["num_threads"] for d in threadpool_info() if d.get("user_api") == "blas"})
        if seen != [limit]:
            raise Refused("BLAS runs at %s threads, not the engine's %d" % (seen, limit))
        for key, rows, take in (("link_corrector", ti, te), ("inner_link_corrector", i_fit, i_sc)):
            t1 = time.time()
            gram = RG.region_gram(q[rows], consume=True)
            fit = RG.region_ridge(gram, gy[rows], lam)
            del gram
            gc.collect()
            p = RG.region_predict(fit, q)
            preds[key] = np.clip(ns.A["LINK_I"](p), 0.0, 1.0)[take]
            out[key] = compare(preds[key], z[key])
            rows_saved.update({key + "__cell_id": cell_ids[take].astype("U"), key + "__year": years[take],
                               key + "__y": np.asarray(y[take], dtype=np.float64),
                               key + "__cache": np.asarray(z[key], dtype=np.float64),
                               key + "__engine_%dthreads" % limit: np.asarray(preds[key], dtype=np.float64)})
            out[key]["solve_seconds"] = round(time.time() - t1, 1)
            if info_threads:
                with threadpool_limits(limits=int(info_threads), user_api="blas"):
                    got = sorted({d["num_threads"] for d in threadpool_info() if d.get("user_api") == "blas"})
                    g2 = RG.region_gram(q[rows], consume=True)
                    f2 = RG.region_ridge(g2, gy[rows], lam)
                    del g2
                    gc.collect()
                    p2 = np.clip(ns.A["LINK_I"](RG.region_predict(f2, q)), 0.0, 1.0)[take]
                out[key]["info_threads"] = {"threads": got, "vs_cache": compare(p2, z[key]),
                                            "vs_gate_threads": compare(p2, preds[key])}
                name = key + "__engine_%sthreads" % "_".join(str(t) for t in got)
                rows_saved[name] = np.asarray(p2, dtype=np.float64)
                del f2, p2
                gc.collect()
            if shipped_too:
                wb = ns.S["ridge"](q, gy, rows, ns.A["LAM"])
                ps = ns.S["apply"](q, wb)
                sp = np.clip(ns.A["LINK_I"](ps), 0.0, 1.0)[take]
                out[key]["shipped_code_w_bytes_equal_engine"] = bool(wb[0].tobytes() == fit.w.tobytes())
                out[key]["shipped_code_bytes_equal_engine"] = bool(sp.tobytes() == preds[key].tobytes())
                out[key]["shipped_code_vs_cache"] = compare(sp, z[key])
                rows_saved[key + "__shipped_%dthreads" % limit] = np.asarray(sp, dtype=np.float64)
                del wb, ps, sp
                gc.collect()
            log("    %-22s rows %d = cache %d | %d threads: max |engine - cache| %.3g, bytes equal %d / %d | %s"
                % (key, out[key]["rows_engine"], out[key]["rows_cache"], limit,
                   out[key].get("max_abs_diff", float("nan")), out[key].get("n_bytes_equal", -1),
                   out[key]["rows_engine"], "PASS" if out[key]["pass"] else "FAIL"))
            if info_threads:
                it = out[key]["info_threads"]
                log("    %-22s (information) %s threads: max |engine - cache| %.3g, bytes equal %d / %d"
                    % ("", it["threads"], it["vs_cache"].get("max_abs_diff", float("nan")),
                       it["vs_cache"].get("n_bytes_equal", -1), it["vs_cache"]["rows_engine"]))
        seen = sorted({d["num_threads"] for d in threadpool_info() if d.get("user_api") == "blas"})
        if seen != [limit]:
            raise Refused("BLAS left the limit: %s" % seen)
    del q, meta
    gc.collect()
    if out_dir is not None:
        pdir = os.path.join(out_dir, "predictions")
        os.makedirs(pdir, exist_ok=True)
        ppath = os.path.join(pdir, "%s.npz" % reg)
        np.savez_compressed(ppath, **rows_saved)
        out["predictions_file"] = {"path": ppath, "sha256": sha256_file(ppath), "arrays": sorted(rows_saved)}
    out["minutes"] = round((time.time() - t0) / 60, 2)
    out["pass"] = bool(out["link_corrector"]["pass"] and out["inner_link_corrector"]["pass"])
    return out


def run(out_dir, only, shipped_too, report, log, info_threads=16):
    ns = shipped_namespace(report)
    donors, cols, pair = donor_block(ns)
    reg_pairs = sorted(norm(p) for p in report["preflight"]["pair_banks"])
    if sorted(norm(p) for p in pair) != reg_pairs:
        raise Refused("add_linkcorr's donor block names pair banks %s, the registry %s" % (pair, reg_pairs))
    report["donors_in_column_order"] = donors
    report["feature_columns"] = len(cols)
    regions = sorted(report["preflight"]["rows_per_region"])
    if only:
        unknown = sorted(set(only) - set(regions))
        if unknown:
            raise Refused("--only names regions without a cache: %s" % unknown)
        regions = [r for r in regions if r in only]
    report["regions"] = {}
    for i, reg in enumerate(regions, 1):
        log("[%s] %d/%d %s" % (time.strftime("%H:%M:%S"), i, len(regions), reg))
        report["regions"][reg] = replay_region(ns, reg, cols, pair, shipped_too, log, info_threads, out_dir)
        want = report["preflight"]["rows_per_region"][reg]
        got = report["regions"][reg]
        got["registry_rows_match"] = bool(got["test_rows"] == want["test_rows"]
                                          and got["inner_score_rows"] == want["inner_rows"])
        got["pass"] = bool(got["pass"] and got["registry_rows_match"])
    return all(r["pass"] for r in report["regions"].values())


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1") for a in argv if a.startswith("--"))
    unknown = sorted(set(opts) - {"out-dir", "only", "shipped-too", "check-only", "deep-banks", "size-only-banks",
                                  "info-threads"})
    if unknown or "out-dir" not in opts or ("deep-banks" in opts and "size-only-banks" in opts):
        print("usage: py -3.9 -u region_replay.py --out-dir=D:/treeroute/region_build/<new> [--only=a,b] "
              "[--shipped-too] [--info-threads=N|0] [--size-only-banks] [--check-only]")
        return 2
    out_dir = opts["out-dir"]
    only = [r for r in opts.get("only", "").split(",") if r]
    try:
        pre = preflight(out_dir, "size-only-banks" not in opts)
    except Refused as exc:
        print("REFUSED: %s" % exc)
        return 2
    if "check-only" in opts:
        print("pre-flight passed (nothing run, nothing written): %s"
              % json.dumps({k: v for k, v in pre.items() if k not in ("rows_per_region", "pair_banks")}))
        return 0
    watched = protected_roots() + list(WATCH_EXTRA)
    before = snapshot(watched)
    os.makedirs(out_dir)
    report = {"gate": "region replay (plan 4.4, M3; owner ruling C: 4 threads, 1e-9)", "tolerance": GATE_TOLERANCE,
              "started": time.strftime("%Y-%m-%d %H:%M:%S"), "argv": argv, "preflight": pre}
    console = open(os.path.join(out_dir, "console.txt"), "w", encoding="utf-8")
    old_out = sys.stdout
    sys.stdout = Tee(old_out, console)
    code = 1
    try:
        report["threads_after_pin"] = pin_threads()
        if ENGINE not in sys.path:
            sys.path.insert(0, ENGINE)
        import treeroute.route.region as RG
        report["engine_region_sha256"] = sha256_file(RG.__file__)
        info = int(opts.get("info-threads", "16"))
        ok = run(out_dir, only, "shipped-too" in opts, report, lambda m: print(m, flush=True), info or None)
        code = 0 if ok else 1
        print("GATE %s" % ("PASS" if ok else "FAIL"))
    except Refused as exc:
        print("REFUSED: %s" % exc)
        report["refused"] = str(exc)
        code = 2
    except Exception:
        report["error"] = traceback.format_exc()
        print(report["error"])
        code = 1
    finally:
        after = snapshot(watched)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        report["protected_changed"] = changed[:50]
        if changed:
            print("PROTECTED FILES CHANGED: %s" % changed[:10])
            code = 5
        report["exit_code"] = code
        report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1, default=str)
        sys.stdout = old_out
        console.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
