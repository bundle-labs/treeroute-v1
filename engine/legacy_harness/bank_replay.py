"""Bank replay gate (plan 4.4, R19): the engine's fit-one-tree primitive, fed the LEGACY seed values,
reproduces the shipped PM2.5 smoke bank bit for bit.

Outside the product: the engine never imports this file (G-IMPORT). It may name problems, years and
drives; the engine may not.

WHAT IT PROVES
  The shipped smoke bank is built by the SHIPPED CODE ITSELF: the pool-and-frames block and the bank
  block of pm25_adaptation.py's _run() are cut out of the file as text (both files' sha256 must equal
  the golden registry) and executed verbatim, and the correctors come from adaptation.py's own
  fit_correctors, also executed from its source text. Nothing is re-typed. Then the engine's
  primitives are fed the legacy seed values on the same donor rows:
      bag      treeroute.fit.bank.draw_bag(n, 7000 + e*17 + j)       (pm25_adaptation.py:642)
      tree     treeroute.fit.bank.fit_one_tree(Vd, yd, gi[bag], 700 + j)     (:646)
      oob      treeroute.fit.bank.oob_rows(gi, gi[bag])
      corr     treeroute.fit.correctors.fit_corrector(tree, Vd, yd, oob, j_global)   (adaptation.py:470)
      placebo  treeroute.fit.correctors.fit_placebo_corrector(..., j_global)
  GATE: for every tree, corrector and placebo corrector, the engine's predictions on every smoke row
  (donor, history and test rows: the rows the shipped run asks the trees about) equal the shipped
  bank's BIT FOR BIT, in float64 and in the float32 table columns (tree, and tree + corrector as
  the shipped writer forms them); and the node arrays of every pair are identical.
  TIE TO THE GOLDEN: the shipped blocks' own log lines (region, feature and tree counts, corrector
  counts and held-out shares), the feature list and the row counts must equal the registered golden
  smoke D:/treeroute/speedproof/golden_smoke (run.log, _adaptation.log, verdict.json), whose files
  are re-hashed against the registry first. So the bank rebuilt here is the golden run's bank.
  INFORMATION (not the replay gate): the engine's own NAME-SEED recipe (fit_donor_bank at the smoke
  tree count) on the same donor rows: the D51 held-out share check per group, a second fit for byte
  determinism, and a fit without the first group to show the other groups' trees do not move. Also
  the fail-closed refusals on these real rows: the router column mask refuses a misspelled group,
  another letter case and a unit id; the bank refuses one group's rows handed over out of grid
  order (R19), a missing feature value (R30) and fold donor rows (no fold bank under leave one
  group out). These count toward the exit code.

FENCES
  - Temp files: the pool goes to <out-dir>/pool_<pid>.f32 (the shipped module's POOL is redirected
    before the build; nothing is written to D:/pm25). It is deleted by this script (references
    dropped, gc, then a LOUD delete that raises on failure), also on a crash.
  - <out-dir> is a NEW folder strictly under D:/treeroute/fit_build/; it keeps report.json and
    console.txt. Nothing is written anywhere else.
  - The protected roots (D:/treeroute/registry/protected_roots.txt) and D:/pm25 are snapshotted
    (size and mtime of every file) before and after; any change fails the run (exit 5).
  - Threads: BLAS 1, OpenMP 4, set before numpy loads (as launch_pinned.py). Tree fits use neither.
  - Refuses to start (exit 2) beside another heavy python job, below 2.5 GB of available RAM, or if a
    shipped file's sha256 differs from the registry.

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine\\legacy_harness"
    py -3.9 -u bank_replay.py                      # smoke: 8 donors, 40 cells, 12 trees per donor
    py -3.9 -u bank_replay.py --check-only         # pre-flight only; writes nothing

Exit codes: 0 all gates pass; 1 a gate failed; 2 refused before starting; 5 a protected file changed.
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
BUILD_ROOT = "D:/treeroute/fit_build"
PROTECTED_LIST = "D:/treeroute/registry/protected_roots.txt"
SHIPPED_TEMP = "D:/pm25"                       # where the shipped script writes its pool; watched
GOLDEN_ID = "pm25_u2_smoke"
PM25_SCRIPT = os.path.join(PROJECT, "pm25_adaptation.py")
ADAPT_SCRIPT = os.path.join(PROJECT, "adaptation.py")
MIN_AVAIL_GB = 2.5

# The shipped smoke preset (pm25_adaptation.py:118-140 with --smoke). Checked against the golden's
# own "PM2.5 | 8 donors | 3 test | 40 test cells/reg | 12 trees/donor" line.
LEGACY_PRESET = {"SMOKE": True, "CELLS": 40, "DCELLS": 40, "NPD": 12, "MF": 0.1, "TRAIN_END": 2019}
ETA = 1.0                                      # pm25_adaptation.py:202 (corrector blend weight)

ENV_PINS = {"OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "BLIS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1", "OMP_NUM_THREADS": "4", "NUMEXPR_NUM_THREADS": "4"}
NUMERIC_MODULES = ("numpy", "scipy", "sklearn", "sklearnex", "daal4py", "onedal", "pandas")
HEAVY_MARKERS = ("pm25_adaptation", "adaptation.py", "adaptation_rooted", "launch_pinned",
                 "run_shipped_blas1", "bank_replay", "pm25_forecast", "pm25_rivals",
                 "fire_architecture", "fire_evt_arch", "coral_architecture", "m0_input_hashes")

# The shipped code blocks, cut out of pm25_adaptation.py by exact first and last line.
BLOCK_FRAMES = ('    donors = list(SPLIT.DONORS)',
                '    test = test.sort_values(["cell", "t"]).reset_index(drop=True)')
BLOCK_BANK = ('    # ---------------------------------------------------------------- bank',
              '    plac = AD.fit_correctors(trees, inbag, home, Vd, yd, MF, placebo=True)')


# ---------------------------------------------------------------------------------------------------
# The legacy seed formulas (plan 4.4: they live in the harness only, passed to the engine as values)
def legacy_bag_seed(e, j):
    """pm25_adaptation.py:642: RandomState(7 * 1000 + int(e) * 17 + j)."""
    return 7 * 1000 + int(e) * 17 + int(j)


def legacy_tree_seed(j):
    """pm25_adaptation.py:646: DecisionTreeRegressor(..., random_state=700 + j)."""
    return 700 + int(j)


def legacy_corrector_seed(j_global):
    """adaptation.py:470: random_state=j, j over the GLOBAL tree list."""
    return int(j_global)


def reversed_inside(member):
    """A row order that reverses the rows where ``member`` is true and keeps every other row in
    place: the same rows and values, one group handed over out of grid order."""
    import numpy as np
    member = np.asarray(member, dtype=bool)
    order = np.arange(member.size)
    idx = np.flatnonzero(member)
    order[idx] = idx[::-1]
    return order


def refusal_rule(fn, *args):
    """Call fn(*args) and return the rule of the treeroute refusal it raises, or None when it does not
    refuse. Any other exception propagates."""
    from treeroute.errors import RefusedError
    try:
        fn(*args)
    except RefusedError as exc:
        return exc.rule
    return None


# ---------------------------------------------------------------------------------------------------
class Refused(Exception):
    pass


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
    """The highest goldens_vN.json in the harness folder (goldens.json is version 1)."""
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
        for dirpath, dirnames, filenames in os.walk(root):
            try:
                st = os.stat(dirpath)
                snap["dir:" + norm(dirpath)] = st.st_mtime_ns
            except OSError:
                pass
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                    snap[norm(p)] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    snap[norm(p)] = "unreadable"
    return snap


def diff(before, after):
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k) != after.get(k))


def heavy_jobs():
    import psutil
    me = os.getpid()
    out = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] == me or "python" not in (proc.info["name"] or "").lower():
                continue
            cmd = " ".join(proc.info["cmdline"] or [])
            if any(mark in cmd for mark in HEAVY_MARKERS):
                out.append("%d: %s" % (proc.info["pid"], cmd[:200]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def cut_block(text, first, last):
    """The lines from the unique line ``first`` to the unique line ``last`` (inclusive), dedented,
    with their 1-based line numbers."""
    lines = text.split("\n")
    starts = [i for i, ln in enumerate(lines) if ln.rstrip("\r") == first]
    ends = [i for i, ln in enumerate(lines) if ln.rstrip("\r") == last]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise Refused("block %r..%r not found exactly once (%d / %d hits)"
                      % (first.strip(), last.strip(), len(starts), len(ends)))
    block = "\n".join(ln.rstrip("\r") for ln in lines[starts[0]:ends[0] + 1]) + "\n"
    return textwrap.dedent(block), starts[0] + 1, ends[0] + 1


def function_source(text, name):
    """The source of the top-level function ``name`` (exact lines), with its line span."""
    tree = ast.parse(text)
    hits = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(hits) != 1:
        raise Refused("function %s not found exactly once" % name)
    lines = text.split("\n")
    node = hits[0]
    src = "\n".join(ln.rstrip("\r") for ln in lines[node.lineno - 1:node.end_lineno]) + "\n"
    return src, node.lineno, node.end_lineno


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


def loud_delete(path):
    """Drop references (the caller already did), collect, then delete; any failure raises."""
    gc.collect()
    if os.path.exists(path):
        os.remove(path)
    if os.path.exists(path):
        raise RuntimeError("temp file %s still exists after the delete" % path)


# ---------------------------------------------------------------------------------------------------
def preflight(out_dir):
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
    _, reg = newest_registry()
    golden = reg["goldens"][GOLDEN_ID]
    want_pm25 = golden["script_sha256_now"]
    want_adapt = reg["goldens"]["fire_smoke"]["source_sha256"]
    got_pm25, got_adapt = sha256_file(PM25_SCRIPT), sha256_file(ADAPT_SCRIPT)
    if got_pm25 != want_pm25:
        raise Refused("pm25_adaptation.py sha256 %s != registry %s" % (got_pm25, want_pm25))
    if got_adapt != want_adapt:
        raise Refused("adaptation.py sha256 %s != registry %s" % (got_adapt, want_adapt))
    bad_golden = []
    for f in golden["files"]:
        if not os.path.exists(f["path"]) or sha256_file(f["path"]) != f["sha256"]:
            bad_golden.append(f["path"])
    if bad_golden:
        raise Refused("golden files missing or changed: %s" % bad_golden)
    heavy = heavy_jobs()
    if heavy:
        raise Refused("another heavy python job is running: %s" % heavy)
    import psutil
    avail = psutil.virtual_memory().available / float(1 << 30)
    if avail < MIN_AVAIL_GB:
        raise Refused("%.2f GB of RAM available, need %.1f" % (avail, MIN_AVAIL_GB))
    return {"pm25_adaptation_sha256": got_pm25, "adaptation_sha256": got_adapt,
            "golden_files_verified": len(golden["files"]), "ram_available_gb": round(avail, 2),
            "protected_roots": roots}


def pin_threads():
    for k, v in ENV_PINS.items():
        os.environ[k] = v
    import numpy  # noqa: F401  (after the pins, on purpose)
    import scipy.linalg  # noqa: F401  (loads scipy's own BLAS at 1 thread too)
    import threadpoolctl
    limiter = threadpoolctl.threadpool_limits(limits={"blas": 1})
    return limiter, [{k: d.get(k) for k in ("user_api", "internal_api", "num_threads")}
                     for d in threadpoolctl.threadpool_info()]


# ---------------------------------------------------------------------------------------------------
def run(out_dir, report):
    import numpy as np
    import pandas as pd

    # ---- the shipped modules, imported with a benign argv (as pm25_adaptation.py:183 does)
    sys.path.insert(0, PROJECT)
    saved_argv = sys.argv
    sys.argv = ["pm25_adaptation.py", "--problem", "fire"]
    try:
        import pm25_architecture as PA
        import pm25_ban as BAN
        import pm25_split as SPLIT
        from sklearn.tree import DecisionTreeRegressor
    finally:
        sys.argv = saved_argv
    import sklearnex
    report["sklearn_patched"] = bool(sklearnex.sklearn_is_patched())
    pool_path = norm(os.path.join(out_dir, "pool_%d.f32" % os.getpid()))
    PA.POOL = pool_path
    report["pool_path"] = pool_path

    def harness_cleanup():
        loud_delete(pool_path)
        report["pool_deleted_by_harness"] = True
    PA.cleanup = harness_cleanup

    # ---- loggers: same line format as the shipped log() functions, lines captured for the golden
    pm_lines, ad_lines = [], []

    def log_pm(m):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)
        pm_lines.append(m)

    def log_ad(m):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)
        ad_lines.append(m)

    phases = {}
    t_phase = [time.time()]

    def phase_done(name):
        phases[name] = round(time.time() - t_phase[0], 1)
        t_phase[0] = time.time()

    # ---- the shipped code, cut out of the shipped files
    with open(PM25_SCRIPT, encoding="utf-8") as f:
        pm_text = f.read()
    with open(ADAPT_SCRIPT, encoding="utf-8") as f:
        ad_text = f.read()
    frames_src, fa, fb = cut_block(pm_text, *BLOCK_FRAMES)
    bank_src, ba, bb = cut_block(pm_text, *BLOCK_BANK)
    corr_src, ca, cb = function_source(ad_text, "fit_correctors")
    report["shipped_blocks"] = {
        "frames": {"file": "pm25_adaptation.py", "lines": [fa, fb],
                   "sha256": hashlib.sha256(frames_src.encode("utf-8")).hexdigest()},
        "bank": {"file": "pm25_adaptation.py", "lines": [ba, bb],
                 "sha256": hashlib.sha256(bank_src.encode("utf-8")).hexdigest()},
        "fit_correctors": {"file": "adaptation.py", "lines": [ca, cb],
                           "sha256": hashlib.sha256(corr_src.encode("utf-8")).hexdigest()}}
    ad_ns = {"np": np, "log": log_ad}
    exec(compile(corr_src, "adaptation.py:fit_correctors", "exec"), ad_ns)
    AD = SimpleNamespace(fit_correctors=ad_ns["fit_correctors"])

    ns = dict(LEGACY_PRESET)
    ns.update({"np": np, "pd": pd, "SPLIT": SPLIT, "PA": PA, "BAN": BAN, "log": log_pm,
               "phase_done": phase_done, "DecisionTreeRegressor": DecisionTreeRegressor, "AD": AD})
    try:
        print("== shipped frames block (pm25_adaptation.py:%d-%d) ==" % (fa, fb), flush=True)
        exec(compile(frames_src, "pm25_adaptation.py:frames", "exec"), ns)
    finally:
        ns.pop("mm", None)
        gc.collect()
        if os.path.exists(pool_path):          # a crash before the shipped PA.cleanup() line
            loud_delete(pool_path)
            report["pool_deleted_by_harness"] = True
    if os.path.exists(pool_path):
        raise RuntimeError("pool file survived: %s" % pool_path)
    print("== shipped bank block (pm25_adaptation.py:%d-%d) ==" % (ba, bb), flush=True)
    t0 = time.time()
    exec(compile(bank_src, "pm25_adaptation.py:bank", "exec"), ns)
    report["seconds_shipped_bank"] = round(time.time() - t0, 1)

    don, hist, test, feat = ns["don"], ns["hist"], ns["test"], ns["feat"]
    Vd, yd = ns["Vd"], ns["yd"]
    trees, inbag, home, corr, plac = ns["trees"], ns["inbag"], ns["home"], ns["corr"], ns["plac"]
    report["rows"] = {"donor": len(don), "history": len(hist), "test": len(test)}
    report["n_features"] = len(feat)
    report["n_shipped_trees"] = len(trees)

    # ---- the engine primitives, fed the legacy seed values
    sys.path.insert(0, ENGINE)
    from treeroute.fit import bank as EB
    from treeroute.fit import correctors as EC

    print("== engine primitives with the legacy seed values ==", flush=True)
    t0 = time.time()
    base_rows = np.arange(len(don))
    e_trees, e_corr, e_plac, bag_ok, inbag_ok, home_ok = [], [], [], 0, 0, 0
    jg = 0
    for e, _g in don.groupby("ecoid"):
        gi = base_rows[don.ecoid.values == e]
        n = len(gi)
        take = max(30, int(0.5 * n))
        for j in range(ns["NPD"]):
            bag = EB.draw_bag(n, legacy_bag_seed(e, j))
            legacy_idx = np.random.RandomState(legacy_bag_seed(e, j)).choice(n, size=take,
                                                                              replace=True)
            bag_ok += int(np.array_equal(bag, legacy_idx))
            rows = gi[bag]
            inbag_ok += int(np.array_equal(np.unique(rows), inbag[jg]))
            home_ok += int(np.array_equal(gi, home[jg]))
            tree = EB.fit_one_tree(Vd, yd, rows, legacy_tree_seed(j))
            ob = EB.oob_rows(gi, rows)
            e_trees.append(tree)
            e_corr.append(EC.fit_corrector(tree, Vd, yd, ob, legacy_corrector_seed(jg)))
            e_plac.append(EC.fit_placebo_corrector(tree, Vd, yd, ob, legacy_corrector_seed(jg)))
            jg += 1
    report["seconds_engine_replay"] = round(time.time() - t0, 1)

    # ---- compare on every smoke row
    V_all = np.vstack([f[feat].fillna(0).values.astype(np.float32) for f in (don, hist, test)])
    report["compared_rows"] = int(V_all.shape[0])
    report["donor_matrix_identical"] = bool(np.array_equal(
        np.ascontiguousarray(V_all[:len(don)]).view(np.uint32),
        np.ascontiguousarray(Vd).view(np.uint32)))
    report["donor_matrix_order"] = "C" if Vd.flags["C_CONTIGUOUS"] else (
        "F" if Vd.flags["F_CONTIGUOUS"] else "strided")
    h_ship, h_eng = hashlib.sha256(), hashlib.sha256()
    counts = {"trees": 0, "tree_nodes": 0, "tree_f64": 0, "tree_f32": 0, "corr_present_match": 0,
              "corr_f64": 0, "corr_col_f32": 0, "plac_f64": 0, "plac_col_f32": 0}
    max_abs = 0.0
    for i in range(len(trees)):
        ts, te = trees[i], e_trees[i]
        counts["trees"] += 1
        counts["tree_nodes"] += int(EB.tree_fingerprint(ts) == EB.tree_fingerprint(te))
        ps, pe = ts.predict(V_all), te.predict(V_all)
        h_ship.update(ps.tobytes())
        h_eng.update(pe.tobytes())
        counts["tree_f64"] += int(ps.tobytes() == pe.tobytes())
        max_abs = max(max_abs, float(np.max(np.abs(ps - pe))))
        ps32, pe32 = ps.astype(np.float32), pe.astype(np.float32)
        counts["tree_f32"] += int(ps32.tobytes() == pe32.tobytes())
        pair_ok = (corr[i] is None) == (e_corr[i] is None) and (plac[i] is None) == (e_plac[i] is None)
        counts["corr_present_match"] += int(pair_ok)
        if corr[i] is not None and e_corr[i] is not None:
            cs, ce = corr[i].predict(V_all), e_corr[i].predict(V_all)
            h_ship.update(cs.tobytes())
            h_eng.update(ce.tobytes())
            counts["corr_f64"] += int(cs.tobytes() == ce.tobytes())
            col_s = ps32 + ETA * cs.astype(np.float32)
            col_e = pe32 + ETA * ce.astype(np.float32)
            counts["corr_col_f32"] += int(col_s.tobytes() == col_e.tobytes())
        elif corr[i] is None and e_corr[i] is None:
            counts["corr_f64"] += 1
            counts["corr_col_f32"] += 1
        if plac[i] is not None and e_plac[i] is not None:
            qs, qe = plac[i].predict(V_all), e_plac[i].predict(V_all)
            h_ship.update(qs.tobytes())
            h_eng.update(qe.tobytes())
            counts["plac_f64"] += int(qs.tobytes() == qe.tobytes())
            col_s = ps32 + ETA * qs.astype(np.float32)
            col_e = pe32 + ETA * qe.astype(np.float32)
            counts["plac_col_f32"] += int(col_s.tobytes() == col_e.tobytes())
        elif plac[i] is None and e_plac[i] is None:
            counts["plac_f64"] += 1
            counts["plac_col_f32"] += 1
    n = len(trees)
    report["replay"] = {
        "counts_identical_of": n, "counts": counts, "bags_identical": bag_ok,
        "inbag_identical": inbag_ok, "home_identical": home_ok,
        "max_abs_tree_prediction_difference": max_abs,
        "sha256_shipped_predictions": h_ship.hexdigest(),
        "sha256_engine_predictions": h_eng.hexdigest(),
        "n_shipped_correctors": sum(c is not None for c in corr),
        "n_shipped_placebos": sum(c is not None for c in plac)}
    replay_pass = (len(e_trees) == n and all(v == n for v in counts.values())
                   and bag_ok == n and inbag_ok == n and home_ok == n and max_abs == 0.0
                   and h_ship.hexdigest() == h_eng.hexdigest())
    report["gate_replay_bit_identical"] = bool(replay_pass)

    # ---- tie to the registered golden smoke
    _, reg = newest_registry()
    gdir = os.path.dirname(reg["goldens"][GOLDEN_ID]["files"][0]["path"])

    def strip_stamp(path):
        with open(path, encoding="utf-8") as f:
            return [re.sub(r"^\[\d\d:\d\d:\d\d\] ", "", ln.rstrip("\n")) for ln in f]

    g_run, g_ad = strip_stamp(os.path.join(gdir, "run.log")), strip_stamp(os.path.join(gdir,
                                                                                   "_adaptation.log"))
    with open(os.path.join(gdir, "verdict.json"), encoding="utf-8") as f:
        g_verdict = json.load(f)
    missing_pm = [m for m in pm_lines if m not in g_run]
    missing_ad = [m for m in ad_lines if m not in g_ad]
    rows_ok = (g_verdict["rows"]["donor"] == len(don) and g_verdict["rows"]["history"] == len(hist)
               and g_verdict["rows"]["scored"] == len(test))
    feats_ok = list(g_verdict["features"]) == list(feat)
    report["golden_tie"] = {"golden": gdir, "shipped_log_lines": pm_lines, "corrector_log_lines": ad_lines,
                            "log_lines_not_in_golden": missing_pm + missing_ad,
                            "rows_equal_verdict": rows_ok, "features_equal_verdict": feats_ok}
    report["gate_golden_tie"] = bool(not missing_pm and not missing_ad and rows_ok and feats_ok
                                     and len(pm_lines) >= 4 and len(ad_lines) == 2)

    # ---- information: the engine's own name-seed recipe on the same donor rows
    print("== engine name-seed recipe (fit_donor_bank, smoke tree count) ==", flush=True)
    from treeroute import engine_constants as K

    def donor_rows(drop=()):
        # grid_rows here are the rows' positions in the shipped donor frame (ascending), standing in
        # for dense-grid positions: the bank needs them ascending and uses nothing else from them.
        keep = ~don.reg.isin(list(drop)).values
        d = don[keep]
        keys = (d.cell_id.astype(str) + "|" + d.t.astype(str)).tolist()
        return SimpleNamespace(
            groups=tuple(sorted(set(d.reg.tolist()))), cut=2019 * 12 + 12, cut_kind="fit", lead=0,
            fold=None, unit_ids=d.cell_id.values, times=d.t.values.astype(np.int64),
            group_of_row=d.reg.values, grid_rows=np.flatnonzero(keep), y=yd[keep],
            X=np.ascontiguousarray(Vd[keep]),
            row_key_hash=hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest())

    def reordered(rows, order):
        return SimpleNamespace(**dict(vars(rows), unit_ids=rows.unit_ids[order],
                                      times=rows.times[order], group_of_row=rows.group_of_row[order],
                                      grid_rows=rows.grid_rows[order], y=rows.y[order],
                                      X=np.ascontiguousarray(rows.X[order])))

    info = {}
    try:
        t0 = time.time()
        b1 = EB.fit_donor_bank(donor_rows(), K.SMOKE_TREES_PER_DONOR)
        info["seconds_fit"] = round(time.time() - t0, 1)
        b2 = EB.fit_donor_bank(donor_rows(), K.SMOKE_TREES_PER_DONOR)
        first = b1.manifest.groups[0]
        b3 = EB.fit_donor_bank(donor_rows(drop=(first,)), K.SMOKE_TREES_PER_DONOR)
        n_by = don.reg.value_counts().to_dict()
        shares = {}
        for g in b1.manifest.groups:
            nn = int(n_by[g])
            p = EB.expected_oob_share(nn, EB.bag_size(nn))
            shares[g] = {"rows": nn, "observed": round(b1.oob_share[g], 6), "expected": round(p, 6),
                         "tolerance": round(EB.oob_share_tolerance(p, nn), 6)}
        fp1 = {(g, j): EB.tree_fingerprint(t) for g, j, t in zip(b1.tree_group, b1.tree_number,
                                                                b1.trees)}
        fp3 = {(g, j): EB.tree_fingerprint(t) for g, j, t in zip(b3.tree_group, b3.tree_number,
                                                                b3.trees)}
        legacy_fps = {EB.tree_fingerprint(t) for t in trees}
        n_b1 = len(b1.trees)
        own_ok = all(
            all(b1.tree_group[c] != g for c in EB.columns_without_own_group(b1, g))
            and len(EB.columns_without_own_group(b1, g)) == n_b1 - K.SMOKE_TREES_PER_DONOR
            and len(EB.group_tree_columns(b1.tree_group, g)) == K.SMOKE_TREES_PER_DONOR
            for g in b1.manifest.groups)
        # the fail-closed refusals, on the real smoke rows (each refuses before any tree is fitted)
        base = donor_rows()
        first_mask = base.group_of_row == first
        nan_X = base.X.copy()
        nan_X[0, 0] = np.nan
        probes = {
            "mask_misspelled_group": refusal_rule(EB.columns_without_own_group, b1, first + "x"),
            "mask_other_case_group": refusal_rule(EB.columns_without_own_group, b1, first.swapcase()),
            "mask_unit_id_as_group": refusal_rule(EB.columns_without_own_group, b1,
                                                  str(base.unit_ids[0])),
            "rows_out_of_grid_order": refusal_rule(EB.fit_donor_bank,
                                                   reordered(base, reversed_inside(first_mask)),
                                                   K.SMOKE_TREES_PER_DONOR),
            "missing_feature": refusal_rule(EB.fit_donor_bank,
                                            SimpleNamespace(**dict(vars(base), X=nan_X)),
                                            K.SMOKE_TREES_PER_DONOR),
            "fold_rows": refusal_rule(EB.fit_donor_bank, SimpleNamespace(**dict(vars(base), fold=0)),
                                      K.SMOKE_TREES_PER_DONOR)}
        want = {"mask_misspelled_group": "G-DISJOINT", "mask_other_case_group": "G-DISJOINT",
                "mask_unit_id_as_group": "G-DISJOINT", "rows_out_of_grid_order": "R19",
                "missing_feature": "R30", "fold_rows": "G-DISJOINT"}
        del nan_X, base
        info["refusal_probes"] = probes
        info["refusal_probes_ok"] = probes == want
        info.update({
            "n_trees": len(b1.trees), "groups": list(b1.manifest.groups),
            "bank_fingerprint": b1.manifest.bank_fingerprint,
            "oob_shares": shares, "d51_check": "passed (fit_donor_bank would have refused)",
            "second_fit_same_fingerprint": b1.manifest.bank_fingerprint == b2.manifest.bank_fingerprint,
            "dropped_group": first,
            "other_groups_trees_unchanged": all(fp3[k] == fp1[k] for k in fp3),
            "n_trees_compared_after_drop": len(fp3),
            "name_seed_trees_equal_to_a_legacy_tree": sum(fp in legacy_fps for fp in fp1.values()),
            "ownership_columns_ok": own_ok,
            "n_correctors": sum(c is not None for c in b1.correctors)})
        info["ok"] = bool(info["second_fit_same_fingerprint"] and info["other_groups_trees_unchanged"]
                          and own_ok and info["refusal_probes_ok"])
    except Exception as exc:                       # reported, and it fails the run below
        info["ok"] = False
        info["error"] = "%s: %s" % (type(exc).__name__, exc)
        info["traceback"] = traceback.format_exc()
    report["engine_name_seed_recipe"] = info
    report["phases_seconds"] = phases


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check_only = "--check-only" in argv
    out_dir = None
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    if out_dir is None:
        out_dir = BUILD_ROOT + "/bank_replay_" + time.strftime("%Y%m%d_%H%M%S")
    out_dir = norm(out_dir)
    try:
        pre = preflight(out_dir)
    except Refused as exc:
        print("bank_replay: REFUSED: %s" % exc, flush=True)
        return 2
    print("bank_replay: pre-flight passed: %s" % json.dumps(pre), flush=True)
    if check_only:
        return 0

    roots = pre["protected_roots"] + [SHIPPED_TEMP]
    before = snapshot(roots)
    os.makedirs(out_dir)
    console = open(os.path.join(out_dir, "console.txt"), "x", encoding="utf-8")
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(real_out, console), Tee(real_err, console)
    report = {"script": os.path.abspath(__file__), "script_sha256": sha256_file(__file__),
              "started": time.strftime("%Y-%m-%d %H:%M:%S"), "out_dir": out_dir,
              "preflight": pre, "legacy_preset": LEGACY_PRESET,
              "legacy_seeds": {"bag": "7000 + e*17 + j", "tree": "700 + j",
                               "corrector": "j over the global tree list"}}
    code = 1
    try:
        _limiter, pools = pin_threads()
        report["threadpools"] = pools
        run(out_dir, report)
        ok = (report.get("gate_replay_bit_identical") and report.get("gate_golden_tie")
              and report.get("engine_name_seed_recipe", {}).get("ok"))
        code = 0 if ok else 1
    except Exception:
        report["crash"] = traceback.format_exc()
        print(report["crash"], flush=True)
        code = 1
    finally:
        pool = report.get("pool_path")
        if pool and os.path.exists(pool):
            gc.collect()
            try:
                loud_delete(pool)
                report["pool_deleted_by_harness"] = True
            except Exception as exc:
                report["pool_delete_error"] = str(exc)
                print("!! could not delete the pool %s: %s" % (pool, exc), flush=True)
                code = 1
        after = snapshot(roots)
        changed = diff(before, after)
        report["protected_or_watched_changes"] = changed
        if changed:
            print("!! protected/watched files changed: %s" % changed[:20], flush=True)
            code = 5
        leftovers = [p for p in glob.glob(os.path.join(out_dir, "*")) if p.endswith(".f32")]
        report["temp_leftovers"] = leftovers
        if leftovers:
            code = 1 if code == 0 else code
        report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report["exit_code"] = code
        with open(os.path.join(out_dir, "report.json"), "x", encoding="utf-8") as f:
            json.dump(report, f, indent=1, default=str)
        summary = {"gate_replay_bit_identical": report.get("gate_replay_bit_identical"),
                   "gate_golden_tie": report.get("gate_golden_tie"),
                   "engine_name_seed_recipe_ok": report.get("engine_name_seed_recipe", {}).get("ok"),
                   "exit_code": code, "report": os.path.join(out_dir, "report.json")}
        print("bank_replay: %s" % json.dumps(summary), flush=True)
        sys.stdout, sys.stderr = real_out, real_err
        console.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
