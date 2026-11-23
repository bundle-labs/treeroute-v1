"""Legacy-harness launcher: run a SHIPPED script (or its rooted copy) with every thread pool pinned.

Plan 4.4 (legacy harness, outside the product) and the Day-1 correction box: goldens are captured
under pinned threads, and the pins must be set BEFORE numpy loads. This generalises
engine/speedproof/run_shipped_blas1.py, which captured the PM2.5 golden wide_golden_blas1 the same way.

WHAT IT DOES, IN ORDER
  1. Pre-flight, before anything numeric is imported. Refuses (exit 2, nothing written) when:
     numpy or another numeric module is already loaded; --out-dir or --scratch is not a sub-folder of
     D:/treeroute/golden/ or already holds files; a path lies under a protected root
     (D:/treeroute/registry/protected_roots.txt); the script arguments contain --force; a variable
     the numeric libraries read is set in the shell (other than the pins below); an --env name is a
     thread variable; an --env value that is a path does not lie inside --out-dir (so a retry with a
     new --out-dir can never write into an earlier run's folder); a --watch folder overlaps
     --out-dir or --scratch; a file already sits at a --redirect-prefix location; another heavy
     python job is running (m0_input_hashes.py, a smoke, a shipped script, another launcher); with
     --copy-of, the script is not the rooted copy that rooted_copy.py checks (same line count, and
     the ONE changed line is exactly rooted_copy.OLD -> rooted_copy.NEW); and, checked last, less
     than --min-avail-gb of RAM is available. --check-only stops here: it prints the pre-flight
     result and exits 0 without running or writing anything.
  2. Pins the environment BEFORE numpy loads (constants below, not flags):
         OPENBLAS / MKL / BLIS / VECLIB = 1 thread     (every BLAS library at 1 thread)
         OMP / NUMEXPR               = 4 threads      (the shipped cap_threads(4), coral_safe.py:29-34;
                                                       plan C14's forest threads)
     then imports numpy and scipy.linalg, so BOTH OpenBLAS copies load at 1 thread, and applies
     threadpoolctl limits (BLAS = 1) for the whole process. sklearn is NOT imported early: the shipped
     code imports it itself after its own cap_threads(4), exactly as when it is launched normally.
     NOTE (owner question, plan A8/C14): A8 puts only router units at BLAS 1 and "any BLAS outside
     router units" at 4. This launcher holds BLAS 1 for the WHOLE process (the harness task's
     wording). That is the A8 pin for fire's per-cell router units, but not literally A8 for a
     region solve (defo), which A8 runs at BLAS 4.
  3. Optionally redirects scratch files by NAME ONLY (--redirect-prefix P, repeatable): any path that
     starts with P goes to <scratch>/<rest of the path after P's folder>. Hooked calls: the `open`
     that numpy's memmap module uses (a name shadowed in that one module, so np.memmap stays numpy's
     own class), os.remove / os.unlink, and glob.glob. The bytes written and read are unchanged.
     Every redirect is printed and recorded. Paths not matching a prefix are never touched.
  4. Runs the script as __main__ with runpy (argv = the arguments after `--`, unchanged). stdout and
     stderr are also copied to <out-dir>/console.txt.
  5. Afterwards records, in <out-dir>/launcher.json (never overwritten): the script's sha256 before
     and after, the --copy-of check (source sha256, the changed line, the diff), the thread pools at
     three points (as loaded under the env pins, after threadpoolctl, at the end), versions, the
     environment the script left behind, every redirect, scratch leftovers, the other python
     processes seen at start, the three leak diffs and the size + sha256 of every file under
     <out-dir>.
     Leak diffs (each compares a before/after snapshot by size and mtime, not by content):
       - protected roots: every file;
       - redirect sources: only files whose NAMES start with a --redirect-prefix;
       - --watch folders (repeatable): every file AND every folder's mtime, so a file created and
         deleted during the run still shows as a changed folder.
     A write anywhere else on D: (outside the protected roots and the watched folders, and not
     prefix-named) is neither redirected nor detected.
     Exit codes: the script's own code; 3 = INVALID (a BLAS pool not at 1 thread, or an OpenMP pool
     not at 4, at the end); 4 = the script file (or its --copy-of source) changed during the run;
     5 = a leak diff is not empty.

    cd "C:\\Users\\moh the ghost\\Desktop\\data set for reserch paper\\engine\\legacy_harness"
    py -3.9 -u launch_pinned.py --script adaptation_rooted.py --copy-of ../../adaptation.py ^
        --out-dir D:/treeroute/golden/fire_smoke --env ADAPTATION_OUT_ROOT=D:/treeroute/golden/fire_smoke ^
        --redirect-prefix D:/fire/pool_features_ --redirect-prefix D:/fire/lead1_pool_ ^
        --redirect-prefix D:/fire/A_ --watch D:/fire --watch D:/joblib_tmp ^
        --min-avail-gb 8.5 -- --problem=fire --calib=strict --smoke=1
    (add --check-only before the `--` to run the pre-flight alone; 8.5 GB is a caution choice, see
    README.md "RAM threshold")

Outside the product: the engine never imports this module (G-IMPORT). Importing it does nothing;
every action happens inside main().
"""
import glob
import hashlib
import json
import os
import platform
import re
import runpy
import sys
import time
import traceback

import rooted_copy          # harness module, pure (no numeric imports): the exact rooted-copy check

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))          # the folder that holds the shipped scripts
SCOPE = "D:/treeroute/golden"                              # every harness output lives under here
DEFAULT_SCRATCH = SCOPE + "/_scratch"
PROTECTED_LIST = "D:/treeroute/registry/protected_roots.txt"

BLAS_THREADS = 1
OMP_THREADS = 4
ENV_PINS = {
    "OPENBLAS_NUM_THREADS": str(BLAS_THREADS),
    "MKL_NUM_THREADS": str(BLAS_THREADS),
    "BLIS_NUM_THREADS": str(BLAS_THREADS),
    "VECLIB_MAXIMUM_THREADS": str(BLAS_THREADS),
    "OMP_NUM_THREADS": str(OMP_THREADS),
    "NUMEXPR_NUM_THREADS": str(OMP_THREADS),
}
EXPECTED_THREADS = {"blas": BLAS_THREADS, "openmp": OMP_THREADS}

NUMERIC_MODULES = ("numpy", "scipy", "sklearn", "sklearnex", "daal4py", "onedal", "pandas", "numexpr")
# variables the numeric runtimes read; any set in the shell (other than ENV_PINS) is refused
FOREIGN_ENV_PREFIXES = ("OPENBLAS_", "GOTO", "OMP_", "KMP_", "MKL_", "BLIS_", "NUMEXPR_", "VECLIB_",
                        "SKLEARN", "SCIPY_", "NPY_", "DAAL", "ONEDAL", "TBB_")
FOREIGN_ENV_NAMES = ("PYTHONHASHSEED",)
# command-line fragments of the heavy jobs this machine runs one at a time
HEAVY_MARKERS = ("m0_input_hashes", "adaptation", "launch_pinned", "run_shipped_blas1", "smoke",
                 "pm25_forecast", "pm25_rivals", "pm25_architecture", "fire_architecture",
                 "fire_evt_arch", "coral_architecture", "cross_region", "defo_", "treeroute")
DRIVE_PATH = re.compile(r"^[A-Za-z]:[/\\]")

_LIMITER = []           # the threadpool_limits object, kept alive for the process lifetime


class LaunchRefused(Exception):
    """A pre-flight refusal: printed, exit code 2, nothing written."""

    def __init__(self, msg):
        super().__init__("launch_pinned: REFUSED: " + msg)


# ---------------------------------------------------------------------------- small pure helpers

def norm(p):
    """Absolute, forward slashes, no trailing slash (a drive root keeps its slash)."""
    s = os.path.abspath(os.fspath(p)).replace("\\", "/")
    return s if re.fullmatch(r"[A-Za-z]:/", s) else s.rstrip("/")


def is_under(path, root):
    """True if `path` is `root` itself or lies inside it (case-insensitive, Windows)."""
    p, r = norm(path).lower(), norm(root).lower()
    return p == r or p.startswith(r.rstrip("/") + "/")


def strictly_under(path, root):
    return is_under(path, root) and norm(path).lower() != norm(root).lower()


def overlaps(a, b):
    return is_under(a, b) or is_under(b, a)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_argv(argv):
    """Launcher options before the first `--`, script arguments after it."""
    if "--" not in argv:
        raise LaunchRefused("put the script's own arguments after a `--` separator (use `--` alone "
                            "if the script takes none).")
    i = argv.index("--")
    return argv[:i], argv[i + 1:]


def parse_options(opts):
    """A tiny parser, so no option can be abbreviated or reach the script by accident."""
    out = {"script": None, "out_dir": None, "scratch": DEFAULT_SCRATCH, "redirect": [], "env": [],
           "watch": [], "copy_of": None, "min_avail_gb": 0.0, "check_only": False}
    single = {"--script": "script", "--out-dir": "out_dir", "--scratch": "scratch",
              "--copy-of": "copy_of", "--min-avail-gb": "min_avail_gb"}
    multi = {"--redirect-prefix": "redirect", "--env": "env", "--watch": "watch"}
    flags = {"--check-only": "check_only"}
    i = 0
    while i < len(opts):
        k = opts[i]
        if k in flags:
            out[flags[k]] = True
            i += 1
            continue
        if k not in single and k not in multi:
            raise LaunchRefused("unknown launcher option %r (allowed: %s)"
                                % (k, ", ".join(sorted(list(single) + list(multi) + list(flags)))))
        if i + 1 >= len(opts):
            raise LaunchRefused("option %s needs a value" % k)
        v = opts[i + 1]
        if k in single:
            out[single[k]] = v
        else:
            out[multi[k]].append(v)
        i += 2
    if not out["script"] or not out["out_dir"]:
        raise LaunchRefused("--script and --out-dir are required")
    try:
        out["min_avail_gb"] = float(out["min_avail_gb"])
    except ValueError:
        raise LaunchRefused("--min-avail-gb must be a number, got %r" % out["min_avail_gb"])
    return out


def parse_env(pairs, out_dir):
    """--env NAME=VALUE list -> dict. Thread variables are refused (the launcher pins them). A value
    that is a path must be an absolute drive path INSIDE out_dir (equal is fine): the out-dir must be
    empty, so the script's own outputs then land in a fresh folder, and a retry that changes
    --out-dir cannot keep writing into an earlier attempt's folder."""
    env = {}
    for pair in pairs:
        if "=" not in pair:
            raise LaunchRefused("--env needs NAME=VALUE, got %r" % pair)
        name, value = pair.split("=", 1)
        up = name.upper()
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", up):
            raise LaunchRefused("--env name %r is not a plain variable name" % name)
        if up in ENV_PINS or up in FOREIGN_ENV_NAMES or up.startswith(FOREIGN_ENV_PREFIXES) \
                or up == "JOBLIB_TEMP_FOLDER":
            raise LaunchRefused("--env %s: thread and numeric-runtime variables (and the joblib "
                                "temp folder) are set by the launcher, never by a flag" % name)
        if DRIVE_PATH.match(value):
            if not is_under(value, out_dir):
                raise LaunchRefused("--env %s=%s: a path value must lie inside --out-dir %s (use the "
                                    "same new folder for both, so a retry never writes into an "
                                    "earlier run's folder)" % (name, value, norm(out_dir)))
        elif "/" in value or "\\" in value:
            raise LaunchRefused("--env %s=%s looks like a path but is not an absolute drive path; "
                                "give an absolute path inside --out-dir" % (name, value))
        env[name] = value
    return env


def check_prefixes(prefixes, scope=SCOPE):
    """Each redirect prefix must be an absolute path whose last part is a non-empty NAME prefix
    (e.g. D:/fire/A_), never a bare folder: a folder prefix would also redirect reads."""
    out = []
    for p in prefixes:
        if not DRIVE_PATH.match(p):
            raise LaunchRefused("--redirect-prefix %r must be an absolute drive path" % p)
        if p.replace("\\", "/").endswith("/"):
            raise LaunchRefused("--redirect-prefix %r must end in a file-name prefix, not a folder"
                                % p)
        n = norm(p)
        folder, name = n.rsplit("/", 1)
        if not name or not folder or any(ch in n for ch in "*?[]"):
            raise LaunchRefused("--redirect-prefix %r needs a literal file-name prefix" % p)
        if is_under(n, scope):
            raise LaunchRefused("--redirect-prefix %r already lies inside the scope" % p)
        out.append(n)
    return out


def check_watch(dirs, out_dir, scratch):
    """--watch folders: absolute drive folders (a missing one is watched for creation), never a whole
    drive, never overlapping --out-dir or --scratch (the run writes there by design)."""
    out = []
    for d in dirs:
        if not DRIVE_PATH.match(d):
            raise LaunchRefused("--watch %r must be an absolute drive path" % d)
        n = norm(d)
        if re.fullmatch(r"[A-Za-z]:/", n):
            raise LaunchRefused("--watch %s: a whole drive is too wide; name a folder" % n)
        if os.path.exists(n) and not os.path.isdir(n):
            raise LaunchRefused("--watch %s is a file, not a folder" % n)
        for label, o in (("--out-dir", out_dir), ("--scratch", scratch)):
            if overlaps(n, o):
                raise LaunchRefused("--watch %s overlaps %s %s (the run writes there)" % (n, label, o))
        if n.lower() not in [x.lower() for x in out]:
            out.append(n)
    return out


def redirect_target(path, prefixes, scratch):
    """The scratch path for `path` if it starts with one of the prefixes, else None."""
    if not isinstance(path, (str, os.PathLike)):
        return None
    s = os.fspath(path)
    if not isinstance(s, str):
        return None
    n = norm(s)
    for pre in prefixes:
        if n.lower().startswith(pre.lower()):
            folder = pre.rsplit("/", 1)[0] + "/"
            return norm(scratch) + "/" + n[len(folder):]
    return None


def files_under(root):
    """[relative/path] of every FILE under root (empty folders are not files)."""
    out = []
    if not os.path.isdir(root):
        return out
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            out.append(os.path.relpath(os.path.join(dp, f), root).replace("\\", "/"))
    return sorted(out)


def snapshot_tree(roots, with_dirs=False):
    """{path: [size, mtime_ns]} of every file under each root (missing roots are skipped). With
    with_dirs, every folder (the root included) is also recorded as '<path>/': [-1, mtime_ns]; a
    folder's mtime changes when an entry is created, deleted or renamed in it."""
    snap = {}

    def put(p, key):
        try:
            st = os.stat(p)
        except OSError:
            return
        snap[key] = [-1 if key.endswith("/") else st.st_size, st.st_mtime_ns]

    for r in roots:
        if not os.path.isdir(r):
            continue
        if with_dirs:
            put(r, norm(r) + "/")
        for dp, dn, fn in os.walk(r):
            if with_dirs:
                for d in dn:
                    p = os.path.join(dp, d)
                    put(p, p.replace("\\", "/") + "/")
            for f in fn:
                p = os.path.join(dp, f)
                put(p, p.replace("\\", "/"))
    return snap


def diff_snapshots(before, after):
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
    return {"added": added, "removed": removed, "changed": changed}


def copy_check(src, dst):
    """The --copy-of check: rooted_copy.check (same line count, exactly one changed line, and that
    line is exactly rooted_copy.OLD in the source and rooted_copy.NEW in the copy, same line end)."""
    res = rooted_copy.check(norm(src), norm(dst))
    return {"ok": res["ok"], "problems": res["problems"], "checked_by": "rooted_copy.check",
            "source": norm(src), "source_sha256": res["source_sha256"],
            "copy_sha256": res["copy_sha256"], "lines_source": res["lines_source"],
            "lines_copy": res["lines_copy"], "changed_lines": [c["line"] for c in res["changed_lines"]],
            "changed_line_text": res["changed_lines"], "unified_diff": res["unified_diff"]}


def protected_roots(path=PROTECTED_LIST):
    if not os.path.exists(path):
        raise LaunchRefused("%s is missing; the launcher will not run without the protected-root "
                            "list" % path)
    with open(path, encoding="utf-8") as f:
        return [norm(ln.strip()) for ln in f if ln.strip() and not ln.strip().startswith("#")]


def foreign_environment(environ):
    out = {}
    for k, v in environ.items():
        up = k.upper()
        if up in ENV_PINS:
            continue
        if up in FOREIGN_ENV_NAMES or up.startswith(FOREIGN_ENV_PREFIXES):
            out[k] = v
    return dict(sorted(out.items()))


def other_python_processes():
    """[(pid, cmdline)] of python processes other than this one and its ancestors (py.exe spawns
    python.exe, so the parent carries the same command line)."""
    import psutil
    me = psutil.Process()
    skip = {me.pid} | {p.pid for p in me.parents()}
    out = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (p.info["name"] or "").lower()
            if p.info["pid"] in skip or not (name.startswith("python") or name in ("py.exe", "pyw.exe")):
                continue
            out.append((p.info["pid"], " ".join(p.info["cmdline"] or [])))
        except Exception:
            continue
    return out


def heavy_jobs(procs):
    return [(pid, cmd) for pid, cmd in procs if any(m in cmd.lower() for m in HEAVY_MARKERS)]


def available_gb():
    import psutil
    return psutil.virtual_memory().available / 2.0 ** 30


def pool_rows(threadpool_info):
    return [{k: d.get(k) for k in ("user_api", "internal_api", "prefix", "version", "num_threads",
                                   "filepath")} for d in threadpool_info()]


def bad_pools(rows):
    return [r for r in rows if r["user_api"] in EXPECTED_THREADS
            and r["num_threads"] != EXPECTED_THREADS[r["user_api"]]]


class _Tee(object):
    def __init__(self, stream, fh):
        self._s, self._f = stream, fh

    def write(self, data):
        self._s.write(data)
        try:
            self._f.write(data)
        except ValueError:          # the copy was closed; the console still gets everything
            pass
        return len(data)

    def flush(self):
        self._s.flush()
        try:
            self._f.flush()
        except ValueError:
            pass

    def __getattr__(self, name):
        return getattr(self._s, name)


# ---------------------------------------------------------------------------- the launcher

def preflight(o, script_args):
    """Every refusal, cheapest first; the RAM check is LAST, so a RAM refusal means every other
    check passed."""
    early = sorted(m for m in NUMERIC_MODULES if m in sys.modules)
    if early:
        raise LaunchRefused("numeric modules already imported (%s); the pins would come too late"
                            % ", ".join(early))
    script = norm(o["script"])
    if not os.path.isfile(script) or not script.lower().endswith(".py"):
        raise LaunchRefused("--script %s is not a .py file" % script)
    out_dir, scratch = norm(o["out_dir"]), norm(o["scratch"])
    for label, d in (("--out-dir", out_dir), ("--scratch", scratch)):
        if not strictly_under(d, SCOPE):
            raise LaunchRefused("%s must be a sub-folder of %s/, got %s" % (label, SCOPE, d))
        if files_under(d):
            raise LaunchRefused("%s %s already holds files; pick a new folder (nothing is ever "
                                "overwritten)" % (label, d))
    if overlaps(out_dir, scratch):
        raise LaunchRefused("--out-dir and --scratch must be separate folders")
    roots = protected_roots()
    for r in roots:
        for label, d in (("--out-dir", out_dir), ("--scratch", scratch), ("scope", SCOPE)):
            if is_under(d, r):
                raise LaunchRefused("%s %s lies under the protected root %s" % (label, d, r))
    if any(a == "--force" or a.startswith("--force=") for a in script_args):
        raise LaunchRefused("--force is refused (it moves earlier runs aside)")
    foreign = foreign_environment(os.environ)
    if foreign:
        raise LaunchRefused("variables the numeric libraries read are set in this shell: %s. Unset "
                            "them; the launcher sets only its own pins."
                            % ", ".join("%s=%s" % kv for kv in foreign.items()))
    env = parse_env(o["env"], out_dir)
    prefixes = check_prefixes(o["redirect"])
    watch = check_watch(o["watch"], out_dir, scratch)
    present = []
    for pre in prefixes:
        present += glob.glob(glob.escape(pre) + "*")
    if present:
        raise LaunchRefused("files already sit at a redirect-source location (another run, or "
                            "leftovers):\n  " + "\n  ".join(sorted(present)))
    procs = other_python_processes()
    heavy = heavy_jobs(procs)
    if heavy:
        raise LaunchRefused("another heavy python job is running (one heavy job at a time):\n  "
                            + "\n  ".join("pid %d: %s" % hp for hp in heavy))
    copy = None
    if o["copy_of"]:
        copy = copy_check(o["copy_of"], script)
        if not copy["ok"]:
            raise LaunchRefused("--copy-of: %s is not the rooted copy of %s: %s"
                                % (script, copy["source"], "; ".join(copy["problems"])))
    avail = available_gb()
    if o["min_avail_gb"] and avail < o["min_avail_gb"]:
        raise LaunchRefused("%.2f GB of RAM available, --min-avail-gb asks for %.1f (every other "
                            "pre-flight check passed). Close other programs (a browser holds "
                            "several GB) and start again, or choose a lower --min-avail-gb."
                            % (avail, o["min_avail_gb"]))
    return dict(script=script, out_dir=out_dir, scratch=scratch, env=env, prefixes=prefixes,
                watch=watch, roots=roots, procs=procs, avail_gb=avail, copy=copy)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts, script_args = split_argv(argv)
    o = parse_options(opts)
    pf = preflight(o, script_args)                 # raises LaunchRefused (exit 2) before any write

    script, out_dir, scratch = pf["script"], pf["out_dir"], pf["scratch"]
    if o["check_only"]:
        print("[launcher] PREFLIGHT OK (--check-only: nothing run, nothing written)\n"
              "  script   %s (sha256 %s)\n  out-dir  %s\n  scratch  %s\n  env      %s\n"
              "  redirect %s\n  watch    %s\n  RAM      %.2f GB available (--min-avail-gb %.1f)\n"
              "  copy-of  %s"
              % (script, sha256_file(script), out_dir, scratch, pf["env"], pf["prefixes"],
                 pf["watch"], pf["avail_gb"], o["min_avail_gb"],
                 "n/a" if not pf["copy"] else "%s OK, changed line(s) %s"
                 % (pf["copy"]["source"], pf["copy"]["changed_lines"])), flush=True)
        return 0

    sha_before = sha256_file(script)
    rec = dict(launcher=norm(__file__), launcher_sha256=sha256_file(os.path.abspath(__file__)),
               rooted_copy_sha256=sha256_file(os.path.join(HERE, "rooted_copy.py")),
               script=script, script_sha256=sha_before, copy_of=pf["copy"], argv=script_args,
               launcher_argv=opts, cwd=norm(os.getcwd()), started=time.strftime("%Y-%m-%d %H:%M:%S"),
               python=platform.python_version(), platform=platform.platform(),
               min_avail_gb=o["min_avail_gb"], avail_ram_gb_at_start=round(pf["avail_gb"], 2),
               other_python_processes=[{"pid": p, "cmdline": c} for p, c in pf["procs"]],
               env_before_pins={k: os.environ.get(k) for k in ENV_PINS}, env_pins=dict(ENV_PINS),
               env_script=pf["env"], redirect_prefixes=pf["prefixes"], watch=pf["watch"],
               scratch=scratch, protected_roots=pf["roots"])
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(scratch, exist_ok=True)
    joblib_tmp = scratch + "/joblib"
    os.makedirs(joblib_tmp, exist_ok=True)
    console_path = out_dir + "/console.txt"
    console = open(console_path, "x", encoding="utf-8")
    sys_stdout, sys_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = _Tee(sys_stdout, console), _Tee(sys_stderr, console)
    print("[launcher] script %s sha256 %s" % (script, sha_before), flush=True)
    if pf["copy"]:
        print("[launcher] rooted copy of %s (sha256 %s); changed line(s) %s"
              % (pf["copy"]["source"], pf["copy"]["source_sha256"], pf["copy"]["changed_lines"]),
              flush=True)

    print("[launcher] snapshot of the protected roots and watched folders ...", flush=True)
    prot_before = snapshot_tree(pf["roots"])
    watch_before = snapshot_tree(pf["watch"], with_dirs=True)
    src_dirs = sorted({pre.rsplit("/", 1)[0] for pre in pf["prefixes"]})
    src_before = {p: v for p, v in snapshot_tree(src_dirs).items()
                  if any(p.lower().startswith(pre.lower()) for pre in pf["prefixes"])}

    # 1. environment pins BEFORE numpy loads, then load both OpenBLAS copies and pin them with threadpoolctl
    for k, v in ENV_PINS.items():
        os.environ[k] = v
    os.environ["JOBLIB_TEMP_FOLDER"] = joblib_tmp
    for k, v in pf["env"].items():
        os.environ[k] = v
    for p in reversed([os.path.dirname(script), PROJECT]):
        if p not in sys.path:
            sys.path.insert(0, p)
    import numpy as np                      # noqa: F401  (numpy's OpenBLAS loads at the env pin)
    import scipy.linalg                     # noqa: F401  (scipy's own OpenBLAS loads at the env pin)
    from threadpoolctl import threadpool_info, threadpool_limits
    rec["pools_loaded_at_env_pins"] = pool_rows(threadpool_info)
    _LIMITER.append(threadpool_limits(limits=BLAS_THREADS, user_api="blas"))
    rec["pools_after_pin"] = pool_rows(threadpool_info)
    bad = bad_pools(rec["pools_after_pin"])
    if bad or not any(r["user_api"] == "blas" for r in rec["pools_after_pin"]):
        sys.stdout, sys.stderr = sys_stdout, sys_stderr
        console.close()
        raise SystemExit("launch_pinned: BLAS not pinned before the run (script NOT started): %s"
                         % rec["pools_after_pin"])
    print("[launcher] pools after pin: %s" % [(r["prefix"], r["user_api"], r["num_threads"])
                                              for r in rec["pools_after_pin"]], flush=True)

    # 2. scratch-file redirects (file names only)
    redirects = []
    mm_globals = np.memmap.__new__.__globals__
    hooks = {}
    if pf["prefixes"]:
        assert mm_globals["__name__"].endswith("memmap") and "open" not in mm_globals, \
            "numpy's memmap module is not laid out as this launcher expects; stopping"
        import builtins
        _open, _remove, _unlink, _glob = builtins.open, os.remove, os.unlink, glob.glob

        def _r(p):
            new = redirect_target(p, pf["prefixes"], scratch)
            if new is None:
                return p
            if (os.fspath(p), new) not in redirects:
                redirects.append((os.fspath(p), new))
                print("[launcher] redirect %s -> %s" % (os.fspath(p), new), flush=True)
            return new

        mm_globals["open"] = lambda file, *a, **k: _open(_r(file), *a, **k)
        os.remove = lambda path, *a, **k: _remove(_r(path), *a, **k)
        os.unlink = lambda path, *a, **k: _unlink(_r(path), *a, **k)
        glob.glob = lambda pathname, *a, **k: _glob(_r(pathname), *a, **k)
        hooks = dict(remove=_remove, unlink=_unlink, glob=_glob)

    # 3. the script, unchanged, as __main__
    sys.argv = [script] + script_args
    rc = None
    try:
        runpy.run_path(script, run_name="__main__")
        rc = 0
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if not isinstance(e.code, (int, type(None))):
            print(e.code, flush=True)
    except BaseException:
        rc = 1
        traceback.print_exc()
    finally:
        if hooks:
            del mm_globals["open"]
            os.remove, os.unlink, glob.glob = hooks["remove"], hooks["unlink"], hooks["glob"]
        rec["pools_at_end"] = pool_rows(threadpool_info)
        bad_end = bad_pools(rec["pools_at_end"])
        prot_diff = diff_snapshots(prot_before, snapshot_tree(pf["roots"]))
        watch_diff = diff_snapshots(watch_before, snapshot_tree(pf["watch"], with_dirs=True))
        src_after = {p: v for p, v in snapshot_tree(src_dirs).items()
                     if any(p.lower().startswith(pre.lower()) for pre in pf["prefixes"])}
        src_diff = diff_snapshots(src_before, src_after)
        versions = {}
        try:
            from importlib import metadata
            for dist in ("numpy", "scipy", "scikit-learn", "scikit-learn-intelex", "pandas",
                         "threadpoolctl", "psutil"):
                try:
                    versions[dist] = metadata.version(dist)
                except Exception:
                    versions[dist] = None
        except Exception:
            pass
        rec.update(exit_code=rc, finished=time.strftime("%Y-%m-%d %H:%M:%S"),
                   pins_ok_at_end=not bad_end, bad_pools_at_end=bad_end,
                   env_at_end={k: os.environ.get(k) for k in list(ENV_PINS) + ["JOBLIB_TEMP_FOLDER"]
                               + sorted(pf["env"])},
                   sklearn_patched=_sklearn_patched(), versions=versions,
                   redirects=redirects, scratch_left=files_under(scratch),
                   protected_roots_changed=prot_diff, redirect_sources_changed=src_diff,
                   watched_changed=watch_diff, script_sha256_after=sha256_file(script))
        if pf["copy"]:
            rec["copy_of_sha256_after"] = sha256_file(pf["copy"]["source"])
        sys.stdout.flush()
        sys.stdout, sys.stderr = sys_stdout, sys_stderr
        console.close()
        rec["outputs"] = [{"path": out_dir + "/" + rel, "size": os.path.getsize(out_dir + "/" + rel),
                           "sha256": sha256_file(out_dir + "/" + rel)}
                          for rel in files_under(out_dir)]
        out = out_dir + "/launcher.json"
        if os.path.exists(out):                     # never overwrite
            out = out_dir + "/launcher_%s.json" % time.strftime("%Y%m%d_%H%M%S")
        with open(out, "x", encoding="utf-8") as f:
            json.dump(rec, f, indent=1)
        print("[launcher] exit %s | pools at end %s | scratch left %d file(s) | written %s"
              % (rc, [(r["prefix"], r["user_api"], r["num_threads"]) for r in rec["pools_at_end"]],
                 len(rec["scratch_left"]), out), flush=True)
    if any(prot_diff.values()) or any(src_diff.values()) or any(watch_diff.values()):
        print("[launcher] !! LEAK: a protected root, a redirect-source name or a watched folder "
              "changed during the run: protected %s | redirect sources %s | watched %s"
              % (prot_diff, src_diff, watch_diff), flush=True)
        return 5
    if rec["script_sha256_after"] != sha_before or (
            pf["copy"] and rec["copy_of_sha256_after"] != pf["copy"]["source_sha256"]):
        print("[launcher] !! the script (or its source) changed during the run", flush=True)
        return 4
    if bad_end:
        print("[launcher] !! INVALID: a pool is not at its pinned thread count at the end: %s"
              % bad_end, flush=True)
        return 3
    return rc


def _sklearn_patched():
    if "sklearnex" not in sys.modules:
        return None
    try:
        return bool(sys.modules["sklearnex"].sklearn_is_patched())
    except Exception:
        return None


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LaunchRefused as refusal:
        print(str(refusal), file=sys.stderr, flush=True)
        sys.exit(2)
