"""Layer replay gate (plan 4.4; APP_PLAN.md 8.0, Sat 3 Oct): the engine's Type-2 layer, fed the shipped
WIDE smoke in LEGACY mode, re-derives the shipped inner candidate table (213 rows) and its adoption
exactly, bit for bit.

Outside the product: the engine never imports this file (G-IMPORT). It may name problems, years and
drives; the engine may not.

LEGACY MODE = the shipped settings: no GLS weights, no own-block drop (the 3 test regions own no tree,
so every router sees all 3,200 columns), one bank (the shipped bank at the train end serves the inner
decision; not the L6 inner-cut refit), the shipped link set identity / log / logc, the shipped normals
and the shipped trees-off definition (intercept + normal + context at the centre penalties), and no
legal clip (the shipped run clipped nothing, so the harness passes an unbounded legal range: the
engine clip is then the identity; the same decision with the target's own range [0, inf) is reported
beside as information). The shipped 'log' link is log1p / expm1, which R22 does not have: the harness
builds it itself (plan 4.4: legacy variants live in the harness) and enters it into the engine
decision under a harness link key (LegacyLink.LOG1P), through the engine's only door for such a key:
a DECLARED layer.arms.LegacyCandidates list (the shipped candidate order, NORMAL_OF's per-link plain
then corrector, and the reason), which decide() checks and writes into the locked adoption.json.
identity and logc go through the ENGINE link transforms, checked bit-equal to the shipped lambdas.
The legacy declaration also lets the decision surface's vault (the test regions' rows) differ from the
guard context's vault (the donor rows): the shipped frames kept them apart.

WHAT IT DOES
  1. Rebuilds the wide smoke's frames, normals, links and inner window with the SHIPPED CODE ITSELF
     (the blocks of pm25_adaptation.py's _run(), sha256 checked, executed verbatim; router_replay.py's
     block boundaries), and the donor matrix lines (Vd, yd).
  2. Refits the bank with the ENGINE primitives and the legacy seed values (trees and correctors; the
     placebo never enters the decision surface), builds the ENGINE tree-answer store over the test
     regions' history rows, and routes the inner window with the ENGINE per-unit router kernels
     (router_replay.py's legacy inputs).
  3. Builds the ENGINE label vault over the test regions' rows and the donor rows, and ENGINE
     FitContexts over the donor rows (lead 0 FIT and GUARD):
       - the decision surface is issued by the vault (LabelView.decision_surface) at the train end, on
         the inner score rows: its labels must equal the shipped inner y;
       - c = layer.links.c_for_cut(FitContext(lead 0, FIT).donor_rows('c')) must equal the shipped
         C_LOG, and the vault's plan-time donor view (with the R18 lists) must give the same row-key
         hash and derive's R23;
  4. Runs the ENGINE layer: layer.decide.decide(surface, arms, the engine grid, legal range, the GUARD
     context, legacy=the declared list) -> G-FITCUT on the surface, the candidate check, the clip,
     R26's penalty search, the N2 guard, R27's MAE adoption and the decline rule.
  5. Locks the adoption with the ENGINE vault (lock_adoption: the document decide() registered, with
     every candidate and the decision section) in a temp run folder, proves that the test labels do not
     open before the lock, opens them against the hash and checks them against the golden's test y;
     plants a test row (the vault refuses to issue it), a hand-built surface, a TestLabels object and
     surface rows before the inner guard's cut (all refused).

GATES (all exact, bit for bit, BLAS 1):
  GL1 surfaces   every engine inner surface (6 arms x 35 points, and the 3 legacy trees-off) as float32
                 equals inner_preds.npz (the chain the layer reads).
  GL2 inputs     the vault's as-of labels of the surface rows equal the shipped inner y; the engine link
                 transforms equal the shipped identity / logc lambdas; c from FitContext's DonorRows
                 equals the shipped C_LOG; the vault's donor view has the DonorRows' row-key hash and
                 derive's R23 value.
  GL3 candidates every one of the 213 candidate rows of inner_candidates.csv: arm, level, ratio, n and
                 MAE from the engine layer, a_tree and a_ctx from the engine grid; the report columns
                 (r2, pat, hit, hit0, mae0) come from the shipped score() fed the engine layer's clipped
                 predictions (the shipped report's own formulas; the engine's report/metrics.py is a
                 separate module with its own gate). No row missing, none extra. The adoption's
                 surface_mae holds all 213 candidates with the golden MAEs, and the record's candidate
                 table hash is the recomputed one; the record's rows are keyed by the surface's units and
                 steps.
  GL4 adoption   the engine adoption equals verdict.json: adopted arm and penalty, tree pick and its
                 penalty, the eligible list in order, the edge flags, every arm's best MAE and penalty,
                 its own normal, beats_own_normal and saved_vs_own_normal, the candidate count.
  GL5 lock       test labels refused before the lock; lock_adoption hashes adoption.json, which carries
                 all 213 candidates and the decision section (surface hash, candidate-table hash, the
                 legacy declaration); the test labels open only against that hash and equal the golden's
                 test y; planted faults refused: the vault will not issue a surface holding a test-window
                 row, a hand-built surface, a TestLabels object on the surface, surface rows before the
                 inner guard's cut (G-FITCUT).
  INFORMATION: the same decision under the target's legal range [0, inf) (pre-clip counts per arm, the
  adoption, how many candidate MAEs move); timings.

FENCES
  - <out-dir> is a NEW folder strictly under D:/treeroute/layer_build/; it keeps report.json and
    console.txt. The pool (<out-dir>/pool_<pid>.f32), the store's temp tables (<out-dir>/tmp/) and the
    temp run folder (<out-dir>/run/) are deleted by this script (references dropped, gc, loud delete),
    also on a crash.
  - The protected roots (D:/treeroute/registry/protected_roots.txt) and D:/pm25 are snapshotted before
    and after; any change fails the run (exit 5).
  - Threads: BLAS 1, OpenMP 4, set before numpy loads (as router_replay.py).
  - Refuses to start (exit 2) beside another heavy python job, below 3 GB of available RAM, or if a
    shipped or golden file's sha256 differs from the registry.

    cd "C:\\Users\\<user>\\Desktop\\data set for reserch paper\\engine\\legacy_harness"
    py -3.9 -u layer_replay.py                    # the layer gate (about 10 minutes)
    py -3.9 -u layer_replay.py --check-only       # pre-flight only; writes nothing

Exit codes: 0 all gates pass; 1 a gate failed; 2 refused before starting; 5 a protected file changed.
"""
import enum
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
import bank_replay as BR  # noqa: E402  (stdlib-only at import)
import router_replay as RRP  # noqa: E402  (stdlib-only at import; its helpers are reused, not changed)

BUILD_ROOT = "D:/treeroute/layer_build"
REGISTRY_DIR = RRP.REGISTRY_DIR
SHIPPED_TEMP = RRP.SHIPPED_TEMP
GOLDEN_ID = RRP.GOLDEN_ID
MIN_AVAIL_GB = 3.0
LEGACY_PRESET = RRP.LEGACY_PRESET
HEAVY_MARKERS = BR.HEAVY_MARKERS + ("router_replay", "layer_replay")
BLOCK_DONOR_MATRIX = ('    Vd = don[feat].fillna(0).values.astype(np.float32)',
                      '    yd = don.y.values.astype(np.float64)')
REPORT_FIELDS = ("r2", "pat", "hit", "hit0", "mae0")


class LegacyLink(enum.Enum):
    """Harness link key for the shipped log1p link (R22 has no such link; plan 4.4)."""
    LOG1P = "log1p"


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


def shipped_name(arm_spec, arm_table, link_of_shipped):
    """The shipped arm name of an engine ArmSpec (base, corrector, treesoff; log...; logc...)."""
    shipped_link = link_of_shipped[arm_spec.link]
    col = {"plain": 0, "corrector": 1, "placebo_corrector": 2, "trees_off": 3}[arm_spec.tool.value]
    return arm_table[shipped_link][col]


def edge_word(axis_value):
    return None if axis_value is None else axis_value.upper()


LEGACY_REASON = ("legacy replay of the shipped wide smoke: its 'log' link is log1p / expm1, which R22 "
                 "does not have; candidate order = the shipped NORMAL_OF (pm25_adaptation.py:900-905)")


def legacy_candidates(LA, link_key, link_set):
    """The declared legacy candidate list: per shipped link (LINK_SET order) plain then corrector
    (NORMAL_OF, the shipped tie order), then each link's trees-off; unweighted, no placebo."""
    arms = [LA.ArmSpec(link_key[L], tool, LA.Weighting.UNWEIGHTED, True)
            for L in link_set for tool in (LA.Tool.PLAIN, LA.Tool.CORRECTOR)]
    arms += [LA.trees_off_of(link_key[L]) for L in link_set]
    return LA.LegacyCandidates(arms=tuple(arms), reason=LEGACY_REASON)


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
    got_pm25, got_adapt = BR.sha256_file(RRP.PM25_SCRIPT), BR.sha256_file(RRP.ADAPT_SCRIPT)
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
    sys.path.insert(0, PROJECT)
    saved_argv = sys.argv
    sys.argv = ["pm25_adaptation.py", "--problem", "fire"]
    try:
        import pm25_architecture as PA
        import pm25_ban as BAN
        import pm25_split as SPLIT
        import fire_architecture as FA  # noqa: F401  (the shipped import set, as router_replay.py)
        from sklearn.tree import DecisionTreeRegressor
    finally:
        sys.argv = saved_argv
    import sklearnex
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

    def log_pm(m):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)

    phases = {}
    t_phase = [time.time()]

    def phase_done(name):
        phases[name] = round(time.time() - t_phase[0], 1)
        t_phase[0] = time.time()

    # ---- the shipped code, cut out of the shipped file
    with open(RRP.PM25_SCRIPT, encoding="utf-8") as f:
        pm_text = f.read()
    srcs, blocks = {}, {}
    for key, (first, last) in (("frames", BR.BLOCK_FRAMES), ("normals", RRP.BLOCK_NORMALS),
                               ("donor_matrix", BLOCK_DONOR_MATRIX), ("links", RRP.BLOCK_LINKS),
                               ("inner", RRP.BLOCK_INNER)):
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
    report["shipped_blocks"] = blocks
    consts = {k: RRP.module_constant(pm_text, k) for k in ("TRAIN_END", "INNER", "MIN_HIST", "HIT_TOL",
                                                           "CTX", "DECLINE_TO", "ADOPT_RANK")}
    report["shipped_constants"] = consts
    sc_ns = {"np": np, "pd": pd, "HIT_TOL": consts["HIT_TOL"]}
    for name in ("_demean", "score"):
        exec(compile(fn_src[name], "pm25_adaptation.py:" + name, "exec"), sc_ns)
    score = sc_ns["score"]

    ns = dict(LEGACY_PRESET)
    ns.update({"np": np, "pd": pd, "SPLIT": SPLIT, "PA": PA, "BAN": BAN, "log": log_pm,
               "phase_done": phase_done, "DecisionTreeRegressor": DecisionTreeRegressor,
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
    print("== shipped normals, donor matrix, links and inner blocks ==", flush=True)
    for key in ("normals", "donor_matrix", "links", "inner"):
        exec(compile(srcs[key], "pm25_adaptation.py:" + key, "exec"), ns)
    don, hist, test, feat = ns["don"], ns["hist"], ns["test"], ns["feat"]
    ih, it, ihy, ity = ns["ih"], ns["it"], ns["ihy"], ns["ity"]
    Vd, yd = ns["Vd"], ns["yd"]
    LINKS, CCOL, ARM, LINK_SET = ns["LINKS"], ns["CCOL"], ns["ARM"], ns["LINK_SET"]
    C_LOG = float(ns["C_LOG"])
    TRAIN_END, INNER = int(consts["TRAIN_END"]), int(consts["INNER"])
    report["rows"] = {"donor": len(don), "history": len(hist), "test": len(test),
                      "inner_fit": len(ih), "inner_score": len(it)}
    report["c_log_shipped"] = C_LOG
    if list(LINK_SET) != ["identity", "log", "logc"]:
        raise RuntimeError("the golden's link set is identity, log, logc; got %s" % LINK_SET)
    phase_done("shipped frames")

    # ---- the engine
    sys.path.insert(0, ENGINE)
    from treeroute import engine_constants as K
    from treeroute.derive import rules as DR
    from treeroute.derive.derived import make_derived
    from treeroute.derive.shapes import CutKind, Link, SeasonKeyKind, SeasonKeySpec
    from treeroute.fit import bank as EB
    from treeroute.fit import context as FC
    from treeroute.fit import correctors as EC
    from treeroute.fit.tables import TreeAnswerStore
    from treeroute.io.steps import build_dense_grid, step_bounds
    from treeroute.labels import vault as V
    from treeroute.layer import arms as LA
    from treeroute.layer import decide as LD
    from treeroute.layer import links as LL
    from treeroute.route import kinds as R
    from treeroute.route import solve as S
    from treeroute.runs.registry import Registry
    from treeroute.split import LoroSplitSets, UnitLists
    from treeroute.timing.shapes import CutPair

    link_key = {"identity": Link.IDENTITY, "log": LegacyLink.LOG1P, "logc": Link.LOG_C}
    link_of_shipped = {v: k for k, v in link_key.items()}

    # ---- engine bank with the legacy seed values (trees and correctors)
    print("== engine bank, legacy seed values ==", flush=True)
    t0 = time.time()
    base_rows = np.arange(len(don))
    e_trees, e_corr, tree_group = [], [], []
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
            tree_group.append(region)
            jg += 1
    report["seconds_engine_bank"] = round(time.time() - t0, 1)
    n_trees = len(e_trees)
    phase_done("engine bank")

    # ---- engine store over the test regions' history rows
    tmp = os.path.join(out_dir, "tmp")
    os.makedirs(tmp)
    cleanup["tmp"] = tmp
    nh = len(hist)
    row_group = hist.reg.values.astype(str).astype(object)
    V_hist = np.ascontiguousarray(hist[feat].fillna(0).values.astype(np.float32))
    fp = EB.tree_fingerprint
    bank_fp = hashlib.sha256("|".join(fp(t) for t in e_trees).encode("utf-8")).hexdigest()
    store = TreeAnswerStore(e_trees, tree_group, e_corr, None, bank_fp,
                            lambda ids: row_group[np.asarray(ids)], tmp, Registry(REGISTRY_DIR))
    cleanup["store"] = store
    tests_sorted = sorted(set(row_group.tolist()))
    t0 = time.time()
    for g in tests_sorted:
        ids = np.flatnonzero(row_group == g).astype(np.int64)
        for kind in ("plain", "corrector"):
            store.build(g, kind, ids, lambda b: V_hist[b])
    report["seconds_store_build"] = round(time.time() - t0, 1)
    phase_done("engine store")

    # ---- the engine router's legacy inputs (router_replay.py's)
    legacy_blocks = tuple((g,) for g in sorted(set(tree_group) | set(tests_sorted)))
    cols = R.RouterTreeColumns(tree_group=tuple(tree_group), blocks=legacy_blocks,
                               columns_by_group={g: np.arange(n_trees, dtype=np.int64) for g in tests_sorted},
                               router_groups={g: (g,) for g in tests_sorted})
    unit_group = dict(zip(hist.cell_id.values.astype(str).tolist(), hist.reg.values.astype(str).tolist()))
    CTX = list(consts["CTX"])

    def engine_forward(link, values):
        """identity and logc through the ENGINE link, log1p through the shipped lambda (legacy)."""
        if link == "log":
            return LINKS[link][0](values)
        return LL.link_forward(values, link_key[link], C_LOG, None)

    def engine_inverse(link, values):
        if link == "log":
            return LINKS[link][1](values)
        return LL.link_inverse(values, link_key[link], C_LOG, None)

    transform_eq = {}
    for L in ("identity", "logc"):
        transform_eq["forward_" + L] = engine_forward(L, ihy).tobytes() == LINKS[L][0](ihy).tobytes()
        probe = np.linspace(-1.0, 6.0, 1001)
        transform_eq["inverse_" + L] = engine_inverse(L, probe).tobytes() == np.asarray(
            LINKS[L][1](probe), dtype=np.float64).tobytes()

    Ch = np.column_stack([ih[c].values for c in CTX]).astype(np.float64)
    Ct = np.column_stack([it[c].values for c in CTX]).astype(np.float64)
    mu, sd = R.router_standardisation(SimpleNamespace(cut=INNER, times=ih.year.values), Ch)
    inner_fit_keys = np.flatnonzero(hist.year.values <= INNER).astype(np.int64)
    inner_score_keys = np.flatnonzero(hist.year.values > INNER).astype(np.int64)

    def rows_for(link):
        return R.PerUnitRows(
            cut=INNER, fit_unit=ih.cell_id.values.astype(str), fit_time=ih.year.values,
            fit_y=engine_forward(link, ihy), fit_normal=ih[CCOL[link]].values.astype(np.float64),
            fit_context=R.standardise_context(Ch, mu, sd), fit_keys=inner_fit_keys,
            score_unit=it.cell_id.values.astype(str), score_time=it.year.values,
            score_normal=it[CCOL[link]].values.astype(np.float64),
            score_context=R.standardise_context(Ct, mu, sd), score_keys=inner_score_keys,
            score_rows=np.arange(len(it)), unit_group=unit_group)

    rows_in = {L: rows_for(L) for L in LINK_SET}
    s_link = {L: float(np.std(LINKS[L][0](don.y.values.astype(np.float64)))) for L in LINK_SET}
    k_standin = K.IDENTITY_GATE / s_link["identity"]
    tol = {L: k_standin * s_link[L] for L in LINK_SET}
    report["r36_standin"] = {"k": k_standin, "s": s_link, "tolerance": tol}

    print("== engine per-unit router, inner surface, %d workers ==" % K.ROUTER_WORKERS, flush=True)
    t0 = time.time()
    routed = {}
    for L in LINK_SET:
        for kind in ("plain", "corrector"):
            routed[(L, kind)] = R._route_per_unit_grid(rows_in[L], store, kind, cols, tol[L])
    report["seconds_engine_router_inner"] = round(time.time() - t0, 1)

    # the shipped trees-off definition (context kept at the centre penalties), router_replay.py's
    a_c = R.point_penalties(R.per_unit_centre(True), True)
    design_full = R.per_unit_router_design(True)
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

    off_link = {L: legacy_off_inner(rows_in[L])[0] for L in LINK_SET}
    phase_done("engine router")

    # ---- y-unit surfaces (pre-clip) and GL1
    gdir = report["preflight"]["golden_dir"]
    gz = np.load(os.path.join(gdir, "inner_preds.npz"))
    grid = R.per_unit_grid(True)
    surfaces, off_y = {}, {}
    surf_eq = {}
    for L in LINK_SET:
        for kind, col in (("plain", 0), ("corrector", 1)):
            P = engine_inverse(L, routed[(L, kind)].predictions)
            surfaces[(L, kind)] = P
            name = ARM[L][col]
            surf_eq[name] = P.astype(np.float32).tobytes() == gz["P_" + name].tobytes()
        p0 = engine_inverse(L, off_link[L])
        off_y[L] = p0
        surf_eq[ARM[L][3]] = p0.astype(np.float32).tobytes() == gz["P_" + ARM[L][3]].tobytes()
    grid_eq = bool(np.array_equal(np.array([[p.level, p.ratio] for p in grid]), gz["grid"]))
    report["GL1_surfaces"] = {"identical": surf_eq, "engine_grid_is_golden_grid": grid_eq,
                              "engine_link_transforms_equal_shipped": transform_eq}
    gl1 = all(surf_eq.values()) and grid_eq and len(surf_eq) == 9

    # ---- GL2: the vault's labels of the decision surface, c from FitContext
    cadence = SimpleNamespace(kind="regular", length=1, unit="month")
    months = int(K.MONTHS_PER_YEAR)

    def steps_of(frame):
        return (frame.year.values.astype(np.int64) * months + frame.month.values.astype(np.int64))

    def month_end(steps):
        return step_bounds(np.asarray(steps, dtype=np.int64), cadence)[1]

    test_first = (TRAIN_END + 1) * months + 1
    train_end_step = TRAIN_END * months + months
    inner_end_step = INNER * months + months
    run_folder = os.path.join(out_dir, "run")
    os.makedirs(run_folder)
    cleanup["run_folder"] = run_folder
    both = pd.concat([hist[["cell_id", "reg", "year", "month", "y"]],
                      test[["cell_id", "reg", "year", "month", "y"]]], ignore_index=True)
    b_units = both.cell_id.values.astype(str).astype(object)
    b_groups = both.reg.values.astype(str).astype(object)
    b_steps = steps_of(both)
    b_grid = build_dense_grid(b_units, b_groups, b_steps, (int(b_steps.min()), int(b_steps.max())))
    b_target = SimpleNamespace(unit_ids=b_units, group_ids=b_groups, time_columns={},
                               y=both.y.values.astype(np.float64))
    labels = V.LabelView(b_grid, b_target, b_steps, test_first, month_end(b_steps), run_folder,
                         cadence=cadence)
    it_units = it.cell_id.values.astype(str).astype(object)
    it_steps = steps_of(it)
    surface = labels.decision_surface(it_units, it_steps, train_end_step)   # the vault fills y (G-LOCK)
    surf_y = np.asarray(surface.y, dtype=np.float64)
    labels_eq = surf_y.tobytes() == ity.tobytes()

    d_units = don.cell_id.values.astype(str).astype(object)
    d_groups = don.reg.values.astype(str).astype(object)
    d_steps = steps_of(don)
    d_grid = build_dense_grid(d_units, d_groups, d_steps, (int(d_steps.min()), int(d_steps.max())))
    d_target = SimpleNamespace(unit_ids=d_units, group_ids=d_groups, time_columns={},
                               y=don.y.values.astype(np.float64))
    d_labels = V.LabelView(d_grid, d_target, d_steps, test_first, month_end(d_steps), None, cadence=cadence)
    d_row = {u: i for i, u in enumerate(d_grid.unit_ids)}
    pos_of_don = np.asarray([d_row[u] for u in d_units.tolist()], dtype=np.int64) * d_grid.n_steps + (
        d_steps - d_grid.first_step)
    don_of_pos = np.full(len(d_grid.unit_ids) * d_grid.n_steps, -1, dtype=np.int64)
    don_of_pos[pos_of_don] = np.arange(len(don))

    class DonorFeatures(object):
        tree_columns = tuple(feat)
        context_columns = tuple(CTX)

        def tree_features(self, grid_rows):
            return Vd[don_of_pos[np.asarray(grid_rows, dtype=np.int64)]]

        def context(self, grid_rows):
            idx = don_of_pos[np.asarray(grid_rows, dtype=np.int64)]
            return don[CTX].values[idx].astype(np.float32)

    bank_units = {}
    for u, g in zip(d_units.tolist(), d_groups.tolist()):
        bank_units.setdefault(g, set()).add(u)
    picks = UnitLists(bank={g: tuple(sorted(v)) for g, v in sorted(bank_units.items())},
                      scored={g: () for g in sorted(bank_units)})
    derived = {"R11": make_derived("R11", {0: CutPair(lead=0, lead_unit="steps", fit_cut=train_end_step,
                                                        guard_cut=inner_end_step)}, {"source": "legacy"}),
               "R2": make_derived("R2", SeasonKeySpec(kind=SeasonKeyKind.MONTH_OF_YEAR, steps_per_year=months),
                                  {"source": "legacy"})}
    split = LoroSplitSets(excluded={}, seen_during_design=(), continuity_groups=())
    ctx = FC.FitContext(derived, split, d_grid, d_labels, DonorFeatures(), picks, 0, CutKind.FIT)
    ctx_guard = ctx.for_lead(0, CutKind.GUARD)
    donor_rows = ctx.donor_rows("c")
    c_engine = LL.c_for_cut(donor_rows)
    view = d_labels.donor_labels(split, train_end_step, CutKind.FIT, 0,
                                 tuple(u for g in sorted(picks.bank) for u in picks.bank[g]), "links",
                                 picks=picks)
    r23 = DR.derive_r23_c_for_cut(view)
    DR.check_r23_matches_run(r23, 0, train_end_step, c_engine, donor_rows.row_key_hash)
    report["GL2_inputs"] = {
        "surface_labels_equal_shipped_inner_y": bool(labels_eq), "surface_rows": int(len(surf_y)),
        "surface_sha256": surface.sha256, "surface_issued_by_the_vault": True,
        "c_engine": c_engine, "c_shipped": C_LOG, "c_equal": c_engine == C_LOG,
        "donor_rows": int(donor_rows.y.size), "donor_row_key_hash": donor_rows.row_key_hash,
        "vault_donor_view_hash_equal": view.row_key_hash == donor_rows.row_key_hash,
        "derive_r23_equal": r23.value == c_engine, "fitctx_log": FC.log_records(ctx.log()),
        "engine_link_transforms_equal_shipped": all(transform_eq.values())}
    gl2 = (labels_eq and c_engine == C_LOG and view.row_key_hash == donor_rows.row_key_hash
           and r23.value == c_engine and all(transform_eq.values()))

    # ---- the engine layer on the decision surface (LEGACY: unbounded range = the shipped no clip)
    legacy = legacy_candidates(LA, link_key, LINK_SET)
    arms = []
    for L in LINK_SET:
        for kind, tool in (("plain", LA.Tool.PLAIN), ("corrector", LA.Tool.CORRECTOR)):
            arms.append(LD.SurfaceArm(LA.ArmSpec(link_key[L], tool, LA.Weighting.UNWEIGHTED, True),
                                      surfaces[(L, kind)]))
    for L in LINK_SET:
        arms.append(LD.SurfaceArm(LA.trees_off_of(link_key[L]), off_y[L]))
    print("== engine layer: decide() in legacy mode (unbounded legal range) ==", flush=True)
    rec = LD.decide(surface, arms, grid, (-float("inf"), float("inf")), ctx_guard, legacy=legacy)
    print("== engine layer: decide() with the target's legal range [0, inf) (information) ==", flush=True)
    rec_clip = LD.decide(surface, arms, grid, (0.0, float("inf")), ctx_guard, legacy=legacy)
    phase_done("engine layer")

    # ---- GL3: the candidate table
    gc_csv = pd.read_csv(os.path.join(gdir, "inner_candidates.csv"), float_precision="round_trip")
    golden_rows = {}
    for _, row in gc_csv.iterrows():
        m = None if pd.isna(row.mlt) else float(row.mlt)
        r = None if pd.isna(row.rho) else float(row.rho)
        golden_rows[(row.arm, m, r)] = row
    clipped_of = dict(rec.predictions)                  # the record's row-level (clipped) predictions
    record_eq = all(clipped_of[LA.arm_name(sa.arm)].tobytes()
                    == LL.clip_with_counts(sa.pre_clip, rec.legal_range, False)[0].tobytes() for sa in arms)
    mine, bad = {}, []
    for c in rec.candidates:
        spec = next(sa.arm for sa in arms if LA.arm_name(sa.arm) == c.arm)
        name = shipped_name(spec, ARM, link_of_shipped)
        key = (name, c.level, c.ratio)
        mine[key] = c
        g = golden_rows.get(key)
        if g is None:
            bad.append((key, "not in golden"))
            continue
        if int(g.n) != c.n:
            bad.append((key, "n", c.n, int(g.n)))
        if not RRP.same_float(c.mae, g.mae):
            bad.append((key, "mae", repr(c.mae), repr(g.mae)))
        if c.level is not None:
            a_t, a_x = R.point_penalties(R.GridPoint(c.level, c.ratio), True)
            if not (RRP.same_float(a_t, g.a_tree) and RRP.same_float(a_x, g.a_ctx)):
                bad.append((key, "penalty", a_t, a_x, g.a_tree, g.a_ctx))
            k = grid.index(R.GridPoint(c.level, c.ratio))
            p = clipped_of[c.arm][:, k]
        else:
            p = clipped_of[c.arm]
        s = score(surf_y, p, it.clim.values, groups=it.reg.values)
        for fld in REPORT_FIELDS:
            if not RRP.same_float(s.get(fld, float("nan")), g[fld]):
                bad.append((key, fld, repr(s.get(fld)), repr(g[fld])))
    absent = sorted((str(k) for k in golden_rows if k not in mine))
    # every candidate in the adoption (the approved shape), keyed, with the golden MAE
    sm = dict(rec.adoption.surface_mae)
    sm_bad = []
    for c in rec.candidates:
        spec = next(sa.arm for sa in arms if LA.arm_name(sa.arm) == c.arm)
        point = None if c.level is None else R.GridPoint(c.level, c.ratio)
        key = LD.candidate_key(spec, point)
        g = golden_rows.get((shipped_name(spec, ARM, link_of_shipped), c.level, c.ratio))
        if key not in sm or g is None or not RRP.same_float(sm[key], g.mae):
            sm_bad.append(key)
    table_sha_eq = rec.candidate_table_sha256 == LD.candidate_table_sha256(rec.candidates)
    keyed = (rec.unit_ids.tolist() == it_units.tolist() and rec.times.tolist() == it_steps.tolist())
    report["GL3_candidates"] = {"engine_rows": len(rec.candidates), "golden_rows": len(golden_rows),
                                "record_predictions_equal_the_clip": bool(record_eq),
                                "missing_in_engine": absent[:20], "mismatches": bad[:50],
                                "adoption_surface_mae_candidates": len(sm),
                                "adoption_surface_mae_mismatches": sm_bad[:20],
                                "candidate_table_sha256": rec.candidate_table_sha256,
                                "candidate_table_sha256_recomputed_equal": bool(table_sha_eq),
                                "record_rows_keyed_by_surface_units_and_steps": bool(keyed),
                                "fields": ["arm", "mlt", "rho", "a_tree", "a_ctx", "n", "mae"] + list(REPORT_FIELDS)}
    gl3 = (not bad and not absent and record_eq and len(rec.candidates) == len(golden_rows) == 213
           and len(sm) == 213 and not sm_bad and table_sha_eq and keyed)

    # ---- GL4: the adoption against verdict.json
    with open(os.path.join(gdir, "verdict.json"), encoding="utf-8") as fh:
        g_verdict = json.load(fh)
    a = rec.adoption
    name_of = lambda spec: shipped_name(spec, ARM, link_of_shipped)          # noqa: E731
    adopted = consts["DECLINE_TO"] if a.declined else name_of(a.adopted)
    penalty = None if a.penalty is None else [a.penalty.level, a.penalty.ratio]
    tree_pick = name_of(a.best_tree_arm)
    pen_tree = [a.best_tree_penalty.level, a.best_tree_penalty.ratio]
    axes = rec.edge_axes[LA.arm_name(a.best_tree_arm)]
    edge = {"level": edge_word(axes["level"]), "ratio": edge_word(axes["ratio"])}
    inner_best, ib_bad = {}, []
    for p in rec.picks:
        name = name_of(p.arm)
        own = ARM[link_of_shipped[p.arm.link]][3]
        own_mae = rec.trees_off_mae[p.arm.link]
        inner_best[name] = {"mae": p.mae, "pen": [p.point.level, p.point.ratio], "own_normal": own,
                            "saved_vs_own_normal": own_mae - p.mae,
                            "beats_own_normal": bool(LD.n2_eligible(p.mae, own_mae))}
    for p in rec.trees_off:
        inner_best[name_of(p.arm)] = {"mae": p.mae, "pen": None, "own_normal": None,
                                      "saved_vs_own_normal": None, "beats_own_normal": None}
    for name, want in g_verdict["inner_best"].items():
        got = inner_best.get(name)
        if got is None:
            ib_bad.append((name, "missing"))
            continue
        for fld in ("mae", "saved_vs_own_normal"):
            if want[fld] is None or got[fld] is None:
                if want[fld] is not got[fld] and not (want[fld] is None and got[fld] is None):
                    ib_bad.append((name, fld, got[fld], want[fld]))
            elif not RRP.same_float(got[fld], want[fld]):
                ib_bad.append((name, fld, repr(got[fld]), repr(want[fld])))
        for fld in ("pen", "own_normal", "beats_own_normal"):
            if got[fld] != want[fld]:
                ib_bad.append((name, fld, got[fld], want[fld]))
    checks = {
        "adopted": (adopted, g_verdict["adopted"]),
        "penalty": (penalty, g_verdict["penalty"]),
        "tree_pick": (tree_pick, g_verdict["tree_pick"]),
        "penalty_tree_arms": (pen_tree, g_verdict["penalty_tree_arms"]),
        "eligible": ([name_of(x) for x in a.eligible], g_verdict["eligible"]),
        "edge": (edge, g_verdict["edge"]),
        "n_candidates": (len(rec.candidates), g_verdict["n_candidates"]),
        "a_tree": (list(R.point_penalties(a.best_tree_penalty, True))[0], g_verdict["a_tree"]),
        "a_ctx": (list(R.point_penalties(a.best_tree_penalty, True))[1], g_verdict["a_ctx"]),
        "decline_to_is_the_identity_trees_off": (ARM["identity"][3], g_verdict["decline_to"]),
        "adopt_rank_is_mae": ("mae", g_verdict["adopt_rank"]),
    }
    report["GL4_adoption"] = {k: {"engine": v[0], "golden": v[1], "equal": v[0] == v[1]}
                              for k, v in checks.items()}
    report["GL4_adoption"]["inner_best_mismatches"] = ib_bad
    report["GL4_adoption"]["engine_edge_pick_flag"] = bool(next(p.edge for p in rec.picks
                                                                if p.arm == a.best_tree_arm))
    gl4 = all(v[0] == v[1] for v in checks.values()) and not ib_bad and len(inner_best) == 9

    # ---- INFORMATION: the target's legal range [0, inf)
    moved = sum(1 for c0, c1 in zip(rec.candidates, rec_clip.candidates) if c0.mae != c1.mae)
    ac = rec_clip.adoption
    report["INFO_clip_on"] = {
        "legal_range": [0.0, "inf"],
        "preclip_counts": {name_of(next(sa.arm for sa in arms if LA.arm_name(sa.arm) == k)):
                           {"below": v.n_below, "above": v.n_above, "values": v.n_finite}
                           for k, v in rec_clip.clip.items()},
        "candidate_maes_moved": moved,
        "adopted": consts["DECLINE_TO"] if ac.declined else name_of(ac.adopted),
        "penalty": None if ac.penalty is None else [ac.penalty.level, ac.penalty.ratio],
        "same_adoption_as_legacy": (ac.adopted == a.adopted and ac.penalty == a.penalty)}

    # ---- GL5: the lock, the test labels, the planted test rows
    lock = {}
    try:
        labels.open_test_labels("0" * 64, 0, alarm_sha256="0" * 64)
        lock["open_before_lock_refused"] = False
    except V.VaultRefusal:
        lock["open_before_lock_refused"] = True
    sha = V.lock_adoption(a, labels, run_folder)
    with open(os.path.join(run_folder, V.ADOPTION_FILE), "rb") as fh:
        adoption_bytes = fh.read()
    lock["adoption_sha256"] = sha
    lock["sha_of_file"] = hashlib.sha256(adoption_bytes).hexdigest() == sha
    doc = json.loads(adoption_bytes.decode("utf-8"))
    lock["adoption_document"] = doc
    decision = doc.get("decision") or {}
    lock["document_holds_every_candidate"] = len(doc.get("surface_mae", {})) == 213
    lock["document_decision_section"] = bool(
        decision.get("surface_sha256") == surface.sha256
        and decision.get("candidate_table_sha256") == rec.candidate_table_sha256
        and decision.get("n_candidates") == 213 and decision.get("missing_arms") == []
        and (decision.get("legacy") or {}).get("reason") == LEGACY_REASON)
    with open(os.path.join(run_folder, V.ADOPTION_FILE + V.LOCK_SUFFIX), encoding="utf-8") as fh:
        lock["lock_record_pre_lock_test_window_reads"] = json.load(fh).get("pre_lock_test_window_reads")
    # owner ruling AE (engine v2): every pass's alarm record is locked before its test labels open; this replay scores
    # no arm on the test rows, so it locks a not-applicable record (the harness never takes the twin)
    from treeroute.layer import alarm as LAL

    alarm_sha = V.lock_alarm(LAL.not_applicable_document(0, V.ADOPTION_FILE, sha, "a legacy harness replay: no arm is "
                                                         "scored on the test rows, so no batch can take the twin"),
                             0, labels, run_folder)
    tl = labels.open_test_labels(sha, 0, alarm_sha256=alarm_sha)
    gp = pd.read_parquet(os.path.join(gdir, "predictions.parquet"))
    g_steps = gp.year.values.astype(np.int64) * months + gp.month.values.astype(np.int64)
    g_key = {(u, int(t)): float(v) for u, t, v in zip(gp.cell_id.values.astype(str).tolist(), g_steps.tolist(),
                                                     gp.y.values.astype(np.float64).tolist())}
    t_pairs = list(zip(tl.unit_ids.tolist(), tl.times.tolist()))
    lock["test_rows"] = len(t_pairs)
    lock["test_rows_equal_golden_rows"] = set((u, int(t)) for u, t in t_pairs) == set(g_key)
    got_y = np.asarray(tl.y, dtype=np.float64)
    want_y = np.asarray([g_key.get((u, int(t)), float("nan")) for u, t in t_pairs])
    lock["test_labels_equal_golden_y"] = got_y.tobytes() == want_y.tobytes()
    legal_off = (-float("inf"), float("inf"))
    try:        # planted: a test-window row on the decision surface (the vault will not issue it)
        labels.decision_surface(np.append(it_units[:-1], it_units[-1]), np.append(it_steps[:-1], test_first),
                                train_end_step)
        lock["test_row_refused"] = False
    except V.VaultRefusal:
        lock["test_row_refused"] = True
    try:        # planted: a hand-built surface carrying the released test labels
        LD.DecisionSurface(unit_ids=tl.unit_ids[:len(it_units)], times=it_steps, y=tl.y[:len(it_units)],
                           label_cut=train_end_step, test_first_time=test_first, sha256=surface.sha256)
        lock["hand_built_surface_refused"] = False
    except LA.LayerRefusal:
        lock["hand_built_surface_refused"] = True
    try:        # planted: a TestLabels object on the decision surface
        LD.decide(surface, arms + [tl], grid, legal_off, ctx_guard, legacy=legacy)
        lock["test_labels_object_refused"] = False
    except LA.LayerRefusal:
        lock["test_labels_object_refused"] = True
    try:        # planted: surface rows before the inner guard's cut (the inner-fit rows; G-FITCUT)
        early = labels.decision_surface(ih.cell_id.values.astype(str).astype(object), steps_of(ih),
                                        train_end_step)
        LD.decide(early, arms, grid, legal_off, ctx_guard, legacy=legacy)
        lock["rows_before_guard_cut_refused"] = False
    except FC.FitContextRefusal:
        lock["rows_before_guard_cut_refused"] = True
    report["GL5_lock"] = lock
    gl5 = (lock["open_before_lock_refused"] and lock["sha_of_file"] and lock["test_rows_equal_golden_rows"]
           and lock["test_labels_equal_golden_y"] and lock["test_row_refused"]
           and lock["hand_built_surface_refused"] and lock["test_labels_object_refused"]
           and lock["rows_before_guard_cut_refused"] and lock["document_holds_every_candidate"]
           and lock["document_decision_section"] and lock["test_rows"] == len(test))
    report["vault_read_log"] = labels.read_log()
    report["vault_test_window_reads"] = labels.test_window_reads()
    phase_done("lock")

    report["timings_seconds"] = dict(phases, whole_run=round(time.time() - t_all, 1))
    report["gates"] = {"GL1_surfaces": bool(gl1), "GL2_inputs": bool(gl2), "GL3_candidates": bool(gl3),
                       "GL4_adoption": bool(gl4), "GL5_lock": bool(gl5)}
    return all(report["gates"].values())


def release(cleanup, report):
    """Close the store (loud temp deletes), delete the pool and the temp run folder's files (written by
    this run only), remove the emptied folders."""
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
    run_folder = cleanup.get("run_folder")
    if run_folder and os.path.isdir(run_folder):
        from_this_run = ("adoption.json", "adoption.json.lock.json", "test_labels_opened_lead_0.json")
        for name in sorted(os.listdir(run_folder)):
            if name in from_this_run:
                try:
                    BR.loud_delete(os.path.join(run_folder, name))
                except Exception as exc:
                    errors.append("run folder delete: %s" % exc)
        left = sorted(os.listdir(run_folder))
        if left:
            errors.append("files left in %s: %s" % (run_folder, left[:10]))
        else:
            os.rmdir(run_folder)
            report["run_folder_removed"] = True
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
        out_dir = BUILD_ROOT + "/layer_replay_" + time.strftime("%Y%m%d_%H%M%S")
    out_dir = BR.norm(out_dir)
    try:
        pre = preflight(out_dir)
    except BR.Refused as exc:
        print("layer_replay: REFUSED: %s" % exc, flush=True)
        return 2
    print("layer_replay: pre-flight passed: %s" % json.dumps(pre), flush=True)
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
              "legacy_mode": {"gls": False, "own_block_drop": False, "banks": "one (train end)",
                              "legal_clip": "none (unbounded range, the shipped setting)",
                              "log_link": "log1p / expm1 built by the harness",
                              "trees_off": "shipped definition (context at the centre penalties)"},
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
        summary = {"gates": report.get("gates"), "timings_seconds": report.get("timings_seconds"),
                   "exit_code": code, "report": os.path.join(out_dir, "report.json")}
        print("layer_replay: %s" % json.dumps(summary, default=str), flush=True)
        sys.stdout, sys.stderr = real_out, real_err
        console.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
