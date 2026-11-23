"""Router replay gate (plan 4.4, 4.5 speedup 3; APP_PLAN.md 8.0, Fri 2 Oct): the engine's per-unit
router, fed the shipped WIDE smoke in LEGACY mode, reproduces the shipped router run at BLAS 1 bit for
bit, and gives the same bytes at 1 and 8 router workers.

Outside the product: the engine never imports this file (G-IMPORT). It may name problems, years and
drives; the engine may not.

WHAT IT DOES
  1. Rebuilds the shipped wide smoke (8 donors, 3 test regions, 40 cells, 400 trees per donor, links
     identity/log/logc) with the SHIPPED CODE ITSELF: the frames, normals, bank, inner-window and
     link blocks of pm25_adaptation.py's _run() and adaptation.py's fit_correctors are cut out of
     the files as text (sha256 checked against the golden registry) and executed verbatim. The
     scoring function (score, _demean) comes from the same file.
  2. Refits the bank with the ENGINE primitives and the legacy seed values (bank_replay's approach:
     draw_bag(n, 7000 + e*17 + j), fit_one_tree(..., 700 + j), fit_corrector / fit_placebo_corrector
     with j over the global tree list) and checks every tree, corrector and placebo corrector
     against the shipped bank node for node.
  3. Builds the tree answers with the ENGINE store (treeroute.fit.tables.TreeAnswerStore: row-keyed,
     scan once per block, 8 tree workers) from the engine bank: one table per test region and kind
     (plain, corrector, placebo_corrector) over its history + test rows.
  4. Routes every test cell with the ENGINE per-unit router kernels (treeroute.route.kinds.
     _route_per_unit_grid / _route_per_unit_at, private until the owner approves public entry
     points) in LEGACY mode:
       - no own-block drop: each test region owns no tree, so its routers see all 3,200 columns
         (RouterTreeColumns built here with every group alone in its block and router groups = the
         region itself; the engine checks the mask against the store's own trees on every call and
         asserts no own-group column on every fit);
       - the shipped context columns (month, lat), standardised by the engine's
         router_standardisation over the pass's fit rows, and the shipped normals (add_clim, run
         here from the shipped text) as the normal column;
       - the shipped penalties: the engine grid (C12 centres, 7 x 5) IS the shipped grid, checked
         against the golden's grid array; the test pass runs at the golden's adopted tree penalty,
         which this script also re-derives from its own inner candidates;
       - the shipped trees-off definition (intercept + normal + context at the centre penalties),
         which differs from the engine's R16 (context dropped): rebuilt here from the engine's own
         design builder and solve_local, exactly as the source forms it (the inner pass slices the
         full design, the test pass builds a 4-column design);
       - fallback: the engine never fills a short-history unit; the golden has none (checked).
  5. GATES (all bit for bit, both sides at BLAS 1):
       G1 bank: every engine tree / corrector / placebo equals the shipped one (node arrays).
       G2 frames: the test frame's keys, y and normals equal predictions.parquet; the inner frame's
          equal inner_preds.npz; the engine grid equals the golden grid; c equals.
       G3 inner surfaces: every arm's 35-point surface and every trees-off surface, as float32,
          equal inner_preds.npz; every one of the 213 candidate scores (n, mae, r2, pat, hit, hit0,
          mae0, a_tree, a_ctx) equals inner_candidates.csv; the re-derived adoption equals verdict.json.
       G4 test pass: all 13 arms' float64 predictions equal predictions.parquet.
       G5 workers: every engine output (predictions and trees-off, every call) is the same bytes at 1
          and at 8 router workers.
       G6 trees-off identity (R16 under R36): the engine's trees-off is within k x s of the normal on
          every call, with s = the donor-row sd of link(y) and k = the U-4 stand-in (identity gate
          1e-6 on the identity link), because the C9 constant k is not set yet. The engine asserts it
          per unit; the maxima are reported. R36's check that the tolerance is at least 10x the
          measured arithmetic error is applied PER LINK in link units (against the largest trees-off
          gap of that link on this run), and on the identity link also against the C9 figure 9e-8.
     INFORMATION: the contract point (1.0, 0.5) solved alone reproduces the grid's MAE (< 1e-9);
     timings of the bank, the store and the router at 8 and 1 workers.

FENCES
  - Temp files: the pool goes to <out-dir>/pool_<pid>.f32 (the shipped module's POOL is redirected
    before the build; nothing is written to D:/pm25) and the store's tables to <out-dir>/tmp/ as
    engine temp memmaps. This script deletes both (references dropped, gc, loud delete that raises),
    also on a crash, and removes the emptied tmp folder.
  - <out-dir> is a NEW folder strictly under D:/treeroute/route_build/; it keeps report.json and
    console.txt. Nothing is written anywhere else.
  - The protected roots (D:/treeroute/registry/protected_roots.txt) and D:/pm25 are snapshotted
    before and after; any change fails the run (exit 5).
  - Threads: BLAS 1, OpenMP 4, set before numpy loads (as launch_pinned.py and bank_replay.py).
  - Refuses to start (exit 2) beside another heavy python job, below 3 GB of available RAM, if a
    shipped file's or a golden file's sha256 differs from the registry.

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine\\legacy_harness"
    py -3.9 -u router_replay.py                    # the wide smoke gate (about 10-15 minutes)
    py -3.9 -u router_replay.py --check-only       # pre-flight only; writes nothing

Exit codes: 0 all gates pass; 1 a gate failed; 2 refused before starting; 5 a protected file changed.
"""
import ast
import gc
import glob
import hashlib
import json
import os
import sys
import time
import traceback
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
PROJECT = os.path.dirname(ENGINE)
sys.path.insert(0, HERE)
import bank_replay as BR  # noqa: E402  (stdlib-only at import; its helpers are reused, not changed)

BUILD_ROOT = "D:/treeroute/route_build"
REGISTRY_DIR = "D:/treeroute/registry"
SHIPPED_TEMP = "D:/pm25"
GOLDEN_ID = "pm25_wide_smoke_blas1"
PM25_SCRIPT = BR.PM25_SCRIPT
ADAPT_SCRIPT = BR.ADAPT_SCRIPT
MIN_AVAIL_GB = 3.0

# The golden's argv: --smoke --npd 400 --links identity,log,logc (pm25_adaptation.py:118-140 with
# --smoke; MF default 0.1). Checked against the golden's own log lines below.
LEGACY_PRESET = {"SMOKE": True, "CELLS": 40, "DCELLS": 40, "NPD": 400, "MF": 0.1,
                 "LINK_SET": ["identity", "log", "logc"]}

# Shipped code blocks, by exact first and last line (pm25_adaptation.py).
BLOCK_FRAMES = BR.BLOCK_FRAMES
BLOCK_BANK = BR.BLOCK_BANK
BLOCK_NORMALS = ('    gmean = float(don.y.mean())',
                 '    yh = hist.y.values.astype(np.float64)')
BLOCK_LINKS = ('    LINKS = {"identity": (lambda v: v, lambda v: v),',
               '           "logc": ("logc", "logc_corrector", "logc_placebo", "logc_treesoff")}')
BLOCK_INNER = ('    ih = hist[hist.year <= INNER].reset_index(drop=True)',
               '    ihy, ity = ih.y.values.astype(np.float64), it.y.values.astype(np.float64)')

HEAVY_MARKERS = BR.HEAVY_MARKERS + ("router_replay",)
TABLE_KIND = {"none": "plain", "corr": "corrector", "plac": "placebo_corrector"}


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


def module_constant(text, name):
    """A top-level NAME = <literal> of a shipped file."""
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise BR.Refused("constant %s not found" % name)


def same_float(a, b):
    """Bit-level float equality, NaN equal to NaN (CSV round trip is exact: repr out, round_trip in)."""
    import math
    a, b = float(a), float(b)
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return a == b


def max_abs(a, b):
    import numpy as np
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if a.shape != b.shape:
        return float("inf")
    d = np.abs(a - b)
    both_nan = np.isnan(a) & np.isnan(b)
    d[both_nan] = 0.0
    return float(np.nanmax(d)) if d.size else 0.0


# ---------------------------------------------------------------------------------------------------
def preflight(out_dir):
    early = [m for m in BR.NUMERIC_MODULES if m in sys.modules]
    if early:
        raise BR.Refused("numeric modules loaded before the pins: %s" % early)
    if not BR.is_under(out_dir, BUILD_ROOT) or BR.norm(out_dir) == BR.norm(BUILD_ROOT):
        raise BR.Refused("--out-dir must be a sub-folder of %s" % BUILD_ROOT)
    if os.path.exists(out_dir):
        raise BR.Refused("%s already exists; every run uses a new folder" % out_dir)
    roots = BR.protected_roots()
    for root in roots:
        if BR.is_under(out_dir, root):
            raise BR.Refused("%s lies under the protected root %s" % (out_dir, root))
    reg_path, reg = BR.newest_registry()
    golden = reg["goldens"][GOLDEN_ID]
    want_pm25 = golden["script_sha256_now"]
    want_adapt = reg["goldens"]["fire_smoke"]["source_sha256"]
    got_pm25, got_adapt = BR.sha256_file(PM25_SCRIPT), BR.sha256_file(ADAPT_SCRIPT)
    if got_pm25 != want_pm25:
        raise BR.Refused("pm25_adaptation.py sha256 %s != registry %s" % (got_pm25, want_pm25))
    if got_adapt != want_adapt:
        raise BR.Refused("adaptation.py sha256 %s != registry %s" % (got_adapt, want_adapt))
    bad = [f["path"] for f in golden["files"]
           if not os.path.exists(f["path"]) or BR.sha256_file(f["path"]) != f["sha256"]]
    if bad:
        raise BR.Refused("golden files missing or changed: %s" % bad)
    heavy = heavy_jobs()
    if heavy:
        raise BR.Refused("another heavy python job is running: %s" % heavy)
    import psutil
    avail = psutil.virtual_memory().available / float(1 << 30)
    if avail < MIN_AVAIL_GB:
        raise BR.Refused("%.2f GB of RAM available, need %.1f" % (avail, MIN_AVAIL_GB))
    return {"registry": reg_path, "pm25_adaptation_sha256": got_pm25, "adaptation_sha256": got_adapt,
            "golden": GOLDEN_ID, "golden_files_verified": len(golden["files"]),
            "golden_dir": os.path.dirname(golden["files"][0]["path"]),
            "ram_available_gb": round(avail, 2), "protected_roots": roots}


# ---------------------------------------------------------------------------------------------------
def run(out_dir, report, cleanup):
    import numpy as np
    import pandas as pd

    t_all = time.time()
    # ---- the shipped modules, imported with a benign argv (as pm25_adaptation.py:183 does)
    sys.path.insert(0, PROJECT)
    saved_argv = sys.argv
    sys.argv = ["pm25_adaptation.py", "--problem", "fire"]
    try:
        import pm25_architecture as PA
        import pm25_ban as BAN
        import pm25_split as SPLIT
        import fire_architecture as FA
        from sklearn.tree import DecisionTreeRegressor
    finally:
        sys.argv = saved_argv
    import sklearnex
    report["sklearn_patched_by_shipped_import"] = bool(sklearnex.sklearn_is_patched())
    if not sklearnex.sklearn_is_patched():        # the engine launcher's ruling C patch
        sklearnex.patch_sklearn(verbose=False)
    report["sklearn_patched"] = bool(sklearnex.sklearn_is_patched())
    pool_path = BR.norm(os.path.join(out_dir, "pool_%d.f32" % os.getpid()))
    PA.POOL = pool_path
    cleanup["pool"] = pool_path

    def harness_cleanup():
        BR.loud_delete(pool_path)
        report["pool_deleted_by_harness"] = True
    PA.cleanup = harness_cleanup

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
    blocks = {}
    srcs = {}
    for key, (first, last) in (("frames", BLOCK_FRAMES), ("normals", BLOCK_NORMALS),
                               ("bank", BLOCK_BANK), ("links", BLOCK_LINKS), ("inner", BLOCK_INNER)):
        src, a, b = BR.cut_block(pm_text, first, last)
        srcs[key] = src
        blocks[key] = {"file": "pm25_adaptation.py", "lines": [a, b],
                       "sha256": hashlib.sha256(src.encode("utf-8")).hexdigest()}
    fn_src = {}
    for name in ("_demean", "score"):
        src, a, b = BR.function_source(pm_text, name)
        fn_src[name] = src
        blocks[name] = {"file": "pm25_adaptation.py", "lines": [a, b],
                        "sha256": hashlib.sha256(src.encode("utf-8")).hexdigest()}
    corr_src, ca, cb = BR.function_source(ad_text, "fit_correctors")
    blocks["fit_correctors"] = {"file": "adaptation.py", "lines": [ca, cb],
                                "sha256": hashlib.sha256(corr_src.encode("utf-8")).hexdigest()}
    report["shipped_blocks"] = blocks
    consts = {k: module_constant(pm_text, k) for k in ("TRAIN_END", "INNER", "MIN_HIST", "HIT_TOL",
                                                       "CTX", "NVERIFY")}
    report["shipped_constants"] = consts
    ad_ns = {"np": np, "log": log_ad}
    exec(compile(corr_src, "adaptation.py:fit_correctors", "exec"), ad_ns)
    AD = SimpleNamespace(fit_correctors=ad_ns["fit_correctors"])
    sc_ns = {"np": np, "pd": pd, "HIT_TOL": consts["HIT_TOL"]}
    for name in ("_demean", "score"):
        exec(compile(fn_src[name], "pm25_adaptation.py:" + name, "exec"), sc_ns)
    score = sc_ns["score"]

    ns = dict(LEGACY_PRESET)
    ns.update({"np": np, "pd": pd, "SPLIT": SPLIT, "PA": PA, "BAN": BAN, "log": log_pm,
               "phase_done": phase_done, "DecisionTreeRegressor": DecisionTreeRegressor, "AD": AD,
               "TRAIN_END": consts["TRAIN_END"], "INNER": consts["INNER"]})
    try:
        print("== shipped frames block ==", flush=True)
        exec(compile(srcs["frames"], "pm25_adaptation.py:frames", "exec"), ns)
    finally:
        ns.pop("mm", None)
        gc.collect()
        if os.path.exists(pool_path):
            BR.loud_delete(pool_path)
            report["pool_deleted_by_harness"] = True
    if os.path.exists(pool_path):
        raise RuntimeError("pool file survived: %s" % pool_path)
    print("== shipped normals block ==", flush=True)
    exec(compile(srcs["normals"], "pm25_adaptation.py:normals", "exec"), ns)
    print("== shipped bank block ==", flush=True)
    t0 = time.time()
    exec(compile(srcs["bank"], "pm25_adaptation.py:bank", "exec"), ns)
    report["seconds_shipped_bank"] = round(time.time() - t0, 1)
    exec(compile(srcs["links"], "pm25_adaptation.py:links", "exec"), ns)
    exec(compile(srcs["inner"], "pm25_adaptation.py:inner", "exec"), ns)

    don, hist, test, feat = ns["don"], ns["hist"], ns["test"], ns["feat"]
    ih, it, ihy, ity, yh, y = ns["ih"], ns["it"], ns["ihy"], ns["ity"], ns["yh"], ns["y"]
    Vd, yd = ns["Vd"], ns["yd"]
    trees, corr, plac = ns["trees"], ns["corr"], ns["plac"]
    LINKS, CCOL, ARM = ns["LINKS"], ns["CCOL"], ns["ARM"]
    LINK_SET = ns["LINK_SET"]
    report["rows"] = {"donor": len(don), "history": len(hist), "test": len(test),
                      "inner_fit": len(ih), "inner_score": len(it)}
    report["c_log"] = ns["C_LOG"]
    alpha, a_ctx0 = FA.ALPHA, FA.A_CTX

    # ---- G1: the engine bank with the legacy seed values
    sys.path.insert(0, ENGINE)
    from treeroute import engine_constants as K
    from treeroute.fit import bank as EB
    from treeroute.fit import correctors as EC
    print("== engine primitives with the legacy seed values ==", flush=True)
    t0 = time.time()
    base_rows = np.arange(len(don))
    e_trees, e_corr, e_plac, tree_group = [], [], [], []
    jg = 0
    for e, g in don.groupby("ecoid"):
        gi = base_rows[don.ecoid.values == e]
        n = len(gi)
        region = str(g.reg.iloc[0])
        for j in range(ns["NPD"]):
            bag = EB.draw_bag(n, BR.legacy_bag_seed(e, j))
            rows_ = gi[bag]
            tree = EB.fit_one_tree(Vd, yd, rows_, BR.legacy_tree_seed(j))
            ob = EB.oob_rows(gi, rows_)
            e_trees.append(tree)
            e_corr.append(EC.fit_corrector(tree, Vd, yd, ob, BR.legacy_corrector_seed(jg)))
            e_plac.append(EC.fit_placebo_corrector(tree, Vd, yd, ob, BR.legacy_corrector_seed(jg)))
            tree_group.append(region)
            jg += 1
    report["seconds_engine_bank"] = round(time.time() - t0, 1)
    fp = EB.tree_fingerprint
    same = {"trees": 0, "correctors": 0, "placebos": 0}
    for i in range(len(trees)):
        same["trees"] += int(fp(trees[i]) == fp(e_trees[i]))
        for key, a, b in (("correctors", corr[i], e_corr[i]), ("placebos", plac[i], e_plac[i])):
            same[key] += int((a is None and b is None)
                             or (a is not None and b is not None and fp(a) == fp(b)))
    n_trees = len(trees)
    report["G1_bank"] = {"trees": n_trees, "identical": same,
                         "n_correctors": sum(c is not None for c in e_corr),
                         "n_placebos": sum(c is not None for c in e_plac)}
    g1 = len(e_trees) == n_trees and all(v == n_trees for v in same.values())
    report["G1_bank"]["pass"] = bool(g1)

    # ---- tie to the golden's own log lines and verdict
    gdir = report["preflight"]["golden_dir"]

    def strip_stamp(path):
        import re
        with open(path, encoding="utf-8") as fh:
            return [re.sub(r"^\[\d\d:\d\d:\d\d\] ", "", ln.rstrip("\n")) for ln in fh]

    g_run, g_ad = strip_stamp(os.path.join(gdir, "run.log")), strip_stamp(os.path.join(gdir,
                                                                                   "_adaptation.log"))
    with open(os.path.join(gdir, "verdict.json"), encoding="utf-8") as fh:
        g_verdict = json.load(fh)
    report["golden_log_tie"] = {
        "shipped_log_lines": pm_lines, "corrector_log_lines": ad_lines,
        "not_in_golden": [m for m in pm_lines if m not in g_run] + [m for m in ad_lines if m not in g_ad],
        "rows_equal_verdict": (g_verdict["rows"]["donor"] == len(don)
                               and g_verdict["rows"]["history"] == len(hist)
                               and g_verdict["rows"]["scored"] == len(test)),
        "features_equal_verdict": list(g_verdict["features"]) == list(feat)}
    tie_ok = (not report["golden_log_tie"]["not_in_golden"] and len(pm_lines) >= 5
              and report["golden_log_tie"]["rows_equal_verdict"]
              and report["golden_log_tie"]["features_equal_verdict"])

    # ---- G2: frames and grid against the golden files
    from treeroute.route import kinds as R
    gp = pd.read_parquet(os.path.join(gdir, "predictions.parquet"))
    gz = np.load(os.path.join(gdir, "inner_preds.npz"))
    frame_checks = {}
    for col in ("reg", "cell_id"):
        frame_checks["test_" + col] = bool(np.array_equal(gp[col].values.astype(str),
                                                          test[col].values.astype(str)))
    for col in ("cell", "year", "month"):
        frame_checks["test_" + col] = bool(np.array_equal(gp[col].values, test[col].values))
    for col in ("y", "clim", "lclim", "lcclim"):
        frame_checks["test_" + col] = gp[col].values.astype(np.float64).tobytes() == \
            test[col].values.astype(np.float64).tobytes()
    frame_checks["inner_y"] = gz["y"].tobytes() == ity.tobytes()
    for col in ("clim", "lclim", "lcclim"):
        frame_checks["inner_" + col] = gz[col].tobytes() == it[col].values.astype(np.float64).tobytes()
    for col in ("reg", "cell_id"):
        frame_checks["inner_" + col] = bool(np.array_equal(gz[col], it[col].values.astype(str)))
    for col in ("year", "month"):
        frame_checks["inner_" + col] = bool(np.array_equal(gz[col], it[col].values))
    frame_checks["c_log"] = float(gz["c_log"][0]) == float(ns["C_LOG"])
    grid = R.per_unit_grid(True)
    frame_checks["engine_grid_is_golden_grid"] = bool(np.array_equal(
        np.array([[p.level, p.ratio] for p in grid]), gz["grid"]))
    frame_checks["centres_are_shipped_alpha"] = (alpha == K.PER_UNIT_TREES_CENTRE
                                                 and a_ctx0 == K.PER_UNIT_CONTEXT_CENTRE)
    frame_checks["ctx_is_month_lat"] = list(consts["CTX"]) == ["month", "lat"]
    report["G2_frames"] = frame_checks
    g2 = all(frame_checks.values()) and tie_ok
    report["G2_frames_pass"] = bool(g2)

    # ---- the engine tree-answer store (the engine bank), one table per test region and kind
    from treeroute.fit.tables import TreeAnswerStore
    from treeroute.runs.registry import Registry
    tmp = os.path.join(out_dir, "tmp")
    os.makedirs(tmp)
    cleanup["tmp"] = tmp
    nh, nt = len(hist), len(test)
    row_group = np.concatenate([hist.reg.values.astype(str), test.reg.values.astype(str)]).astype(object)
    V_all = np.ascontiguousarray(np.vstack([hist[feat].fillna(0).values.astype(np.float32),
                                            test[feat].fillna(0).values.astype(np.float32)]))
    bank_fp = hashlib.sha256("|".join(fp(t) for t in e_trees).encode("utf-8")).hexdigest()
    store = TreeAnswerStore(e_trees, tree_group, e_corr, e_plac, bank_fp,
                            lambda ids: row_group[np.asarray(ids)], tmp, Registry(REGISTRY_DIR))
    cleanup["store"] = store
    tests_sorted = sorted(set(test.reg.values.astype(str).tolist()))
    t0 = time.time()
    for g in tests_sorted:
        ids = np.flatnonzero(row_group == g).astype(np.int64)
        for kind in ("plain", "corrector", "placebo_corrector"):
            store.build(g, kind, ids, lambda b: V_all[b])
    report["seconds_store_build"] = round(time.time() - t0, 1)
    report["store"] = {k: v for k, v in store.record().items() if k in ("trees", "features", "writer",
                                                                         "tables")}

    # ---- the engine router's legacy inputs
    # legacy mode: no overlap blocks (every group alone in its block); the test regions own no tree
    legacy_blocks = tuple((g,) for g in sorted(set(tree_group) | set(tests_sorted)))
    cols = R.RouterTreeColumns(tree_group=tuple(tree_group), blocks=legacy_blocks,
                               columns_by_group={g: np.arange(n_trees, dtype=np.int64)
                                                 for g in tests_sorted},
                               router_groups={g: (g,) for g in tests_sorted})
    report["legacy_mask"] = {"blocks": len(legacy_blocks), "test_groups": tests_sorted,
                             "columns_per_test_group": n_trees,
                             "store_n_trees": int(store.n_trees)}
    unit_group = dict(zip(hist.cell_id.values.astype(str).tolist(), hist.reg.values.astype(str).tolist()))
    unit_group.update(zip(test.cell_id.values.astype(str).tolist(), test.reg.values.astype(str).tolist()))
    CTX = list(consts["CTX"])

    def pass_rows(fit, score_f, fit_keys, score_keys, cut, link, yfit):
        Ch = np.column_stack([fit[c].values for c in CTX]).astype(np.float64)
        Ct = np.column_stack([score_f[c].values for c in CTX]).astype(np.float64)
        mu, sd = R.router_standardisation(SimpleNamespace(cut=cut, times=fit.year.values), Ch)
        f = LINKS[link][0]
        return R.PerUnitRows(
            cut=cut, fit_unit=fit.cell_id.values.astype(str), fit_time=fit.year.values,
            fit_y=f(yfit), fit_normal=fit[CCOL[link]].values.astype(np.float64),
            fit_context=R.standardise_context(Ch, mu, sd), fit_keys=fit_keys,
            score_unit=score_f.cell_id.values.astype(str), score_time=score_f.year.values,
            score_normal=score_f[CCOL[link]].values.astype(np.float64),
            score_context=R.standardise_context(Ct, mu, sd), score_keys=score_keys,
            score_rows=np.arange(len(score_f)), unit_group=unit_group)

    inner_fit_keys = np.flatnonzero(hist.year.values <= consts["INNER"]).astype(np.int64)
    inner_score_keys = np.flatnonzero(hist.year.values > consts["INNER"]).astype(np.int64)
    rows_in = {L: pass_rows(ih, it, inner_fit_keys, inner_score_keys, consts["INNER"], L, ihy)
               for L in LINK_SET}
    rows_te = {L: pass_rows(hist, test, np.arange(nh, dtype=np.int64),
                            nh + np.arange(nt, dtype=np.int64), consts["TRAIN_END"], L, yh)
               for L in LINK_SET}
    # R36 stand-in: s per link = donor-row sd of link(y); k chosen so the identity link's tolerance is
    # the U-4 identity gate (C9 k is not set yet)
    s_link = {L: float(np.std(LINKS[L][0](don.y.values.astype(np.float64)))) for L in LINK_SET}
    k_standin = K.IDENTITY_GATE / s_link["identity"]
    tol = {L: k_standin * s_link[L] for L in LINK_SET}
    report["r36_standin"] = {
        "k": k_standin, "s": s_link, "tolerance": tol,
        "identity_tolerance_minus_identity_gate": tol["identity"] - K.IDENTITY_GATE,
        # R36: the tolerance is at least 10x the measured arithmetic error. The C9 figure (9e-8) is
        # in y units, so it is compared with the IDENTITY link only; every link is ALSO checked in
        # its own link units against the arithmetic error measured here (G6 below)
        "identity_tolerance_at_least_10x_c9_measured_arith_error":
            tol["identity"] >= K.K_MIN_MULTIPLE_OF_ARITH_ERROR * K.MEASURED_ARITH_ERROR}

    inner_arms = ([(ARM[L][0], L, "none") for L in LINK_SET] + [(ARM[L][1], L, "corr") for L in LINK_SET])

    def engine_inner(workers):
        R._TEST_ONLY_ROUTER_WORKERS = workers
        out, secs = {}, {}
        for name, link, kk in inner_arms:
            t = time.time()
            out[name] = R._route_per_unit_grid(rows_in[link], store, TABLE_KIND[kk], cols, tol[link])
            secs[name] = round(time.time() - t, 2)
        t = time.time()
        out["_contract"] = R._route_per_unit_at(rows_in["identity"], store, "plain", cols,
                                               R.per_unit_centre(True), tol["identity"])
        secs["_contract"] = round(time.time() - t, 2)
        return out, secs

    def engine_test(workers, test_arms):
        R._TEST_ONLY_ROUTER_WORKERS = workers
        out, secs = {}, {}
        for name, link, kk, pen, off in test_arms:
            if off:
                continue
            t = time.time()
            out[name] = R._route_per_unit_at(rows_te[link], store, TABLE_KIND[kk], cols,
                                            R.GridPoint(*pen), tol[link])
            secs[name] = round(time.time() - t, 2)
        return out, secs

    # ---- the engine router, 8 workers (the engine constant)
    print("== engine per-unit router, inner surface, %d workers ==" % K.ROUTER_WORKERS, flush=True)
    t0 = time.time()
    in8, in8_secs = engine_inner(K.ROUTER_WORKERS)
    report["seconds_engine_inner_w8"] = round(time.time() - t0, 1)

    # ---- the shipped trees-off definition, from the engine's builder and solver (legacy only)
    from treeroute.route import solve as S
    a_c = R.point_penalties(R.per_unit_centre(True), True)      # (ALPHA, A_CTX) = (0.5, 0.25)
    report["legacy_trees_off_penalties"] = list(a_c)
    design_full = R.per_unit_router_design(True)
    design_off = R.RouterDesign(kind=R.RouterKind.PER_UNIT, columns=(R.INTERCEPT, R.NORMAL, R.CONTEXT),
                                unpenalised=(R.INTERCEPT, R.NORMAL), centre=(), grid=(),
                                fit_row_cap=None)
    o = 2 + len(CTX)

    def legacy_off_inner(rows):
        plan, short = R.per_unit_plan(rows)
        out0 = np.full(len(rows.score_unit), np.nan)
        for unit, group, hidx, tsel in plan:
            view = store.unit_view(np.concatenate([rows.fit_keys[hidx], rows.score_keys[tsel]]), "plain")
            nf = hidx.size
            M = rows.fit_normal[hidx]
            c = M.mean()
            Xc = R.build_column_block(design_full, M, rows.fit_context[hidx], view.values[:nf], c).X
            Xt = R.build_column_block(design_full, rows.score_normal[tsel], rows.score_context[tsel],
                                      view.values[nf:], c).X
            b0 = S.solve_local(Xc[:, :o], rows.fit_y[hidx], np.ones(nf), 0, len(CTX), a_c[0], a_c[1])
            out0[tsel] = Xt[:, :o] @ b0
        return out0, short

    def legacy_off_test(rows):
        plan, short = R.per_unit_plan(rows)
        out0 = np.full(len(rows.score_unit), np.nan)
        for unit, group, hidx, tsel in plan:
            M = rows.fit_normal[hidx]
            c = M.mean()
            Xc = R.build_column_block(design_off, M, rows.fit_context[hidx], None, c).X
            Xt = R.build_column_block(design_off, rows.score_normal[tsel], rows.score_context[tsel],
                                      None, c).X
            out0[tsel] = S.solve_point(Xc, rows.fit_y[hidx], Xt, 0, len(CTX), a_c[0], a_c[1])
        return out0, short

    t0 = time.time()
    off_in = {L: legacy_off_inner(rows_in[L]) for L in LINK_SET}
    report["seconds_legacy_trees_off_inner"] = round(time.time() - t0, 1)

    # ---- G3: inner surfaces and candidates
    gc_csv = pd.read_csv(os.path.join(gdir, "inner_candidates.csv"), float_precision="round_trip")
    surf, cand, inner = {}, {}, {}
    for name, link, kk in inner_arms:
        finv = LINKS[link][1]
        P = finv(in8[name].predictions)
        surf[name] = P.astype(np.float32)
        best_k, best_s = None, None
        for k, p in enumerate(grid):
            s = score(ity, P[:, k], it.clim.values, groups=it.reg.values)
            cand[(name, p.level, p.ratio)] = s
            if best_s is None or s["mae"] < best_s["mae"]:
                best_k, best_s = k, s
        inner[name] = dict(best_s, pen=(grid[best_k].level, grid[best_k].ratio))
        if kk == "none":
            off = ARM[link][3]
            p0 = finv(off_in[link][0])
            surf[off] = p0.astype(np.float32)
            s = score(ity, p0, it.clim.values, groups=it.reg.values)
            cand[(off, None, None)] = s
            inner[off] = dict(s, pen=None)
    surface_eq = {k: surf[k].tobytes() == gz["P_" + k].tobytes() for k in surf}
    surface_gap = {k: max_abs(surf[k], gz["P_" + k]) for k in surf}
    cand_rows, cand_bad = 0, []
    fields = ("n", "mae", "r2", "pat", "hit", "hit0", "mae0")
    for _, row in gc_csv.iterrows():
        m = None if pd.isna(row.mlt) else float(row.mlt)
        r = None if pd.isna(row.rho) else float(row.rho)
        mine = cand.get((row.arm, m, r))
        if mine is None:
            cand_bad.append((row.arm, m, r, "missing"))
            continue
        cand_rows += 1
        for fld in fields:
            if not same_float(mine.get(fld, float("nan")), row[fld]):
                cand_bad.append((row.arm, m, r, fld, repr(mine.get(fld)), repr(row[fld])))
        if m is not None:
            a_t, a_x = R.point_penalties(R.GridPoint(m, r), True)
            if not (same_float(a_t, row.a_tree) and same_float(a_x, row.a_ctx)):
                cand_bad.append((row.arm, m, r, "penalty", a_t, a_x, row.a_tree, row.a_ctx))
    extra = sorted(set(cand) - set((a, None if pd.isna(mm) else float(mm), None if pd.isna(rr) else float(rr))
                                   for a, mm, rr in zip(gc_csv.arm, gc_csv.mlt, gc_csv.rho)), key=str)
    # contract point (information, as the source checks it): (1.0, 0.5) alone == the grid's MAE
    chk = score(ity, in8["_contract"].predictions[:, 0], it.clim.values)["mae"]
    ref = cand[("base", 1.0, 0.5)]["mae"]
    # the N2 guard and MAE adoption, re-derived as the source does (pm25_adaptation.py:853-873)
    normal_of = {}
    for L in LINK_SET:
        normal_of[ARM[L][0]] = ARM[L][3]
        normal_of[ARM[L][1]] = ARM[L][3]
    eligible = [k for k in normal_of if inner[k]["mae"] < inner[normal_of[k]]["mae"]]
    pick = min(eligible, key=lambda k: inner[k]["mae"]) if eligible else "treesoff"
    tree_pick = pick if pick in normal_of else min(normal_of, key=lambda k: inner[k]["mae"])
    pen_tree = inner[tree_pick]["pen"]
    report["G3_inner"] = {
        "surfaces_identical": surface_eq, "surface_max_abs_gap": surface_gap,
        "candidates_compared": cand_rows, "candidates_in_golden": int(len(gc_csv)),
        "candidates_not_in_golden": [str(x) for x in extra], "candidate_mismatches": cand_bad[:50],
        "contract_point_mae": chk, "grid_point_mae": ref, "contract_gap": abs(chk - ref),
        "adopted": pick, "tree_pick": tree_pick, "penalty_tree_arms": list(pen_tree),
        "golden_adopted": g_verdict.get("adopted"),
        "golden_penalty_tree_arms": g_verdict.get("penalty_tree_arms")}
    g3 = (all(surface_eq.values()) and cand_rows == len(gc_csv) and not cand_bad and not extra
          and pick == g_verdict.get("adopted")
          and list(pen_tree) == list(g_verdict.get("penalty_tree_arms"))
          and abs(chk - ref) < 1e-9)
    report["G3_inner_pass"] = bool(g3)

    # ---- G4: the test pass (13 arms), at the re-derived tree penalty
    test_arms = ([("base_inherited", "identity", "none", (1.0, 0.5), False)]
                 + [(ARM[L][0], L, "none", pen_tree, False) for L in LINK_SET]
                 + [(ARM[L][3], L, "none", (1.0, 0.5), True) for L in LINK_SET]
                 + [(ARM[L][1], L, "corr", pen_tree, False) for L in LINK_SET]
                 + [(ARM[L][2], L, "plac", pen_tree, False) for L in LINK_SET])
    print("== engine per-unit router, test pass, %d workers ==" % K.ROUTER_WORKERS, flush=True)
    t0 = time.time()
    te8, te8_secs = engine_test(K.ROUTER_WORKERS, test_arms)
    report["seconds_engine_test_w8"] = round(time.time() - t0, 1)
    t0 = time.time()
    off_te = {L: legacy_off_test(rows_te[L]) for L in LINK_SET}
    report["seconds_legacy_trees_off_test"] = round(time.time() - t0, 1)
    test_eq, test_gap = {}, {}
    for name, link, kk, pen, off in test_arms:
        finv = LINKS[link][1]
        p = finv(off_te[link][0]) if off else finv(te8[name].predictions[:, 0])
        want = gp["p_" + name].values.astype(np.float64)
        test_eq[name] = p.astype(np.float64).tobytes() == want.tobytes()
        test_gap[name] = max_abs(p, want)
    shorts = {"inner": {L: len(off_in[L][1]) for L in LINK_SET},
              "test": {L: len(off_te[L][1]) for L in LINK_SET},
              "engine_fallback_units": sorted(set(o_.n_units_fallback for o_ in list(in8.values())
                                                  + list(te8.values())))}
    report["G4_test"] = {"arms_identical": test_eq, "max_abs_gap": test_gap,
                         "short_history_units": shorts,
                         "units_fitted": sorted(set(o_.n_units_fitted for o_ in te8.values()))}
    g4 = all(test_eq.values()) and len(test_eq) == 13 and shorts["engine_fallback_units"] == [0]
    report["G4_test_pass"] = bool(g4)

    # ---- G6: the engine's R16 trees-off identity under the R36 stand-in
    ident = {}
    for tag, outs, rows_by in (("inner", in8, rows_in), ("test", te8, rows_te)):
        for name, o_ in outs.items():
            if name.startswith("_"):
                continue
            link = next(L for L in LINK_SET if name in ARM[L] or name == "base_inherited" and L == "identity")
            dev = float(np.nanmax(np.abs(o_.trees_off - rows_by[link].score_normal)))
            ident["%s:%s" % (tag, name)] = {"link": link, "max_abs": dev, "tolerance": tol[link],
                                            "pass": dev <= tol[link]}
    # R36 per link, in link units: the tolerance must be at least 10x the arithmetic error measured
    # on this run (the largest trees-off gap over every call of the link)
    per_link = {}
    for L in LINK_SET:
        measured = max(v["max_abs"] for v in ident.values() if v["link"] == L)
        multiple = (tol[L] / measured) if measured > 0 else float("inf")
        per_link[L] = {"tolerance": tol[L], "measured_arith_error_link_units": measured,
                       "multiple": multiple,
                       "at_least_10x": multiple >= K.K_MIN_MULTIPLE_OF_ARITH_ERROR}
    report["G6_r36_per_link"] = per_link
    report["G6_trees_off_identity"] = ident
    g6 = (all(v["pass"] for v in ident.values())
          and all(v["at_least_10x"] for v in per_link.values())
          and report["r36_standin"]["identity_tolerance_at_least_10x_c9_measured_arith_error"])
    report["G6_pass"] = bool(g6)

    # ---- G5: the same engine calls at 1 worker
    print("== engine per-unit router again, 1 worker ==", flush=True)
    t0 = time.time()
    in1, in1_secs = engine_inner(1)
    report["seconds_engine_inner_w1"] = round(time.time() - t0, 1)
    t0 = time.time()
    te1, te1_secs = engine_test(1, test_arms)
    report["seconds_engine_test_w1"] = round(time.time() - t0, 1)
    R._TEST_ONLY_ROUTER_WORKERS = None
    w_eq = {}
    for tag, a_, b_ in (("inner", in8, in1), ("test", te8, te1)):
        for name in a_:
            w_eq["%s:%s" % (tag, name)] = (a_[name].predictions.tobytes() == b_[name].predictions.tobytes()
                                           and a_[name].trees_off.tobytes() == b_[name].trees_off.tobytes())
    report["G5_workers"] = {"identical_1_vs_8": w_eq, "calls": len(w_eq)}
    g5 = all(w_eq.values()) and len(w_eq) == len(in8) + len(te8)
    report["G5_pass"] = bool(g5)

    report["timings_seconds"] = {
        "shipped_bank_block": report["seconds_shipped_bank"],
        "engine_bank_legacy_seeds": report["seconds_engine_bank"],
        "engine_store_build_3_kinds": report["seconds_store_build"],
        "engine_router_inner_w8": report["seconds_engine_inner_w8"],
        "engine_router_test_w8": report["seconds_engine_test_w8"],
        "engine_router_inner_w1": report["seconds_engine_inner_w1"],
        "engine_router_test_w1": report["seconds_engine_test_w1"],
        "per_call_w8": {"inner": in8_secs, "test": te8_secs},
        "per_call_w1": {"inner": in1_secs, "test": te1_secs},
        "legacy_trees_off_inner": report["seconds_legacy_trees_off_inner"],
        "legacy_trees_off_test": report["seconds_legacy_trees_off_test"],
        "whole_run": round(time.time() - t_all, 1)}
    report["phases_seconds"] = phases
    report["gates"] = {"G1_bank": bool(g1), "G2_frames": bool(g2), "G3_inner": bool(g3),
                       "G4_test": bool(g4), "G5_workers": bool(g5), "G6_trees_off_identity": bool(g6)}
    return all(report["gates"].values())


def release(cleanup, report):
    """Close the store (loud temp-memmap deletes), delete the pool, remove the emptied tmp folder."""
    errors = []
    store = cleanup.pop("store", None)
    if store is not None:
        try:
            store.close()
        except Exception as exc:
            errors.append("store close: %s" % exc)
        del store
    gc.collect()
    pool = cleanup.get("pool")
    if pool and os.path.exists(pool):
        try:
            BR.loud_delete(pool)
            report["pool_deleted_by_harness"] = True
        except Exception as exc:
            errors.append("pool delete: %s" % exc)
    tmp = cleanup.get("tmp")
    if tmp and os.path.isdir(tmp):
        left = sorted(os.listdir(tmp))
        if left:
            errors.append("temp files left in %s: %s" % (tmp, left[:10]))
        else:
            os.rmdir(tmp)
            report["tmp_removed"] = True
    return errors


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check_only = "--check-only" in argv
    out_dir = None
    if "--out-dir" in argv:
        out_dir = argv[argv.index("--out-dir") + 1]
    if out_dir is None:
        out_dir = BUILD_ROOT + "/router_replay_" + time.strftime("%Y%m%d_%H%M%S")
    out_dir = BR.norm(out_dir)
    try:
        pre = preflight(out_dir)
    except BR.Refused as exc:
        print("router_replay: REFUSED: %s" % exc, flush=True)
        return 2
    print("router_replay: pre-flight passed: %s" % json.dumps(pre), flush=True)
    if check_only:
        return 0

    roots = pre["protected_roots"] + [SHIPPED_TEMP]
    before = BR.snapshot(roots)
    os.makedirs(out_dir)
    console = open(os.path.join(out_dir, "console.txt"), "x", encoding="utf-8")
    real_out, real_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = BR.Tee(real_out, console), BR.Tee(real_err, console)
    report = {"script": os.path.abspath(__file__), "script_sha256": BR.sha256_file(__file__),
              "started": time.strftime("%Y-%m-%d %H:%M:%S"), "out_dir": out_dir, "preflight": pre,
              "legacy_preset": LEGACY_PRESET,
              "legacy_seeds": {"bag": "7000 + e*17 + j", "tree": "700 + j",
                               "corrector": "j over the global tree list"}}
    code = 1
    cleanup = {}
    try:
        _limiter, pools = BR.pin_threads()
        report["threadpools"] = pools
        ok = run(out_dir, report, cleanup)
        code = 0 if ok else 1
    except Exception:
        report["crash"] = traceback.format_exc()
        print(report["crash"], flush=True)
        code = 1
    finally:
        errs = release(cleanup, report)
        if errs:
            report["cleanup_errors"] = errs
            print("!! cleanup: %s" % errs, flush=True)
            code = 1 if code == 0 else code
        after = BR.snapshot(roots)
        changed = BR.diff(before, after)
        report["protected_or_watched_changes"] = changed
        if changed:
            print("!! protected/watched files changed: %s" % changed[:20], flush=True)
            code = 5
        leftovers = [p for p in glob.glob(os.path.join(out_dir, "**", "*"), recursive=True)
                     if os.path.isfile(p) and not p.endswith(("report.json", "console.txt"))]
        report["temp_leftovers"] = leftovers
        if leftovers:
            code = 1 if code == 0 else code
        report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report["exit_code"] = code
        with open(os.path.join(out_dir, "report.json"), "x", encoding="utf-8") as f:
            json.dump(report, f, indent=1, default=str)
        summary = {"gates": report.get("gates"), "timings_seconds": {
            k: v for k, v in (report.get("timings_seconds") or {}).items() if not k.startswith("per_call")},
            "exit_code": code, "report": os.path.join(out_dir, "report.json")}
        print("router_replay: %s" % json.dumps(summary), flush=True)
        sys.stdout, sys.stderr = real_out, real_err
        console.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
