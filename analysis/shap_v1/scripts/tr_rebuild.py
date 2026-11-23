"""treeroute v1: rebuild the model behind one problem's kept predictions, outside the run folders, and prove it
(PROTOCOL.md section 4.1, v3). One engine process per problem (every tree lead in it), through the engine's own
launcher pins.

  py -3.9 -I -B tr_rebuild.py --problem coral --leads 0 183 [--arcsine-tolerance 0] [--recorded-path-map]
        [--package-dir DIR] [--precheck-only] [--engine-root DIR] [--reference RUN] [--kind headline]
        [--sample-root DIR] [--register FILE] [--machine YAML] [--out-root DIR] [--explain-pinned]

Steps: the engine's own pipeline steps up to the temp folder (machine file inside this analysis folder), with the
input pre-check E3a right after the target listing and BEFORE the target is read (the package fingerprint, the
static and target file lists, the engine constants, groups, context, strata: a moved input stops the run in
minutes, not after the census and derive); the nowcast pool or the lead's pool; the fit-cut bank of that lead (and
the GLS weight model for a weighted arm); the kept arm routed at the adopted penalty for the sampled units only, the
router coefficients captured while the engine's own kernel solves; gates E1-E10 (PROTOCOL.md 4.1). Writes
rebuild/<problem>/lead_<L>/: gates.json, preds_check.parquet, bank.npz (the bank's trees as arrays), routers.npz and
rows.parquet (coefficients, design values and features of every row SHAP reads), DONE.json (with the sample's
SHA-256, the tolerance and the path map used: a resume reuses a finished lead only under the same identity). The
engine keeps its bank checkpoints in this folder's engine_runs (never deleted here), so a re-run after a crash
reloads the fitted groups (verified by their tree fingerprints).

Owner decisions this script implements as switches (PROTOCOL.md 12): D8 --arcsine-tolerance (a TRUE relative bound
on arcsine arms, licensed only by an identity-twin proof); D14 --recorded-path-map (the package moved with the
2026-11-08 reinstall: hash today's package files under the run's recorded engine path, accepted only when every
mapped file's content SHA-256, size and mtime equal the freeze lock's record) or --package-dir (a real copy of the
package at the recorded path, made by the owner).
"""
import argparse
import contextlib
import glob
import os
import sys
import threading
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402  (standard library only: the engine's launcher must pin first)

_TLS = threading.local()
CAPTURE = {"units": {}, "regions": {}, "keep": None, "first_values": None, "kind": None}
PATHMAP = {"on": False, "new": None, "old": None, "mapped": {}}
FREEZE_DIR = "D:/treeroute/registry/freeze"


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--leads", "--lead", type=int, nargs="+", required=True,
                    help="one or more leads, rebuilt in ONE engine process (the census and derive run once)")
    ap.add_argument("--engine-root", default=None, help="default: the run's own engine snapshot (PROTOCOL.md 4.1)")
    ap.add_argument("--reference", default=None, help="default: the headline run folder (read-only)")
    ap.add_argument("--kind", default="headline", choices=("headline", "smoke"))
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--machine", default=os.path.join(C.ROOT, "machine_shap.yaml"))
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--allow-engine-mismatch", action="store_true", help="owner option A only (gates decide)")
    ap.add_argument("--explain-pinned", action="store_true", help="a declined lead: explain the pinned arm (D5)")
    ap.add_argument("--all-units", action="store_true", help="smoke worlds: route every scored unit")
    ap.add_argument("--smoke-arm", default=None, help="smoke worlds only: route and check this saved arm instead of "
                                                      "the kept one (exercises another kernel path)")
    ap.add_argument("--diagnose", action="store_true",
                    help="continue past E5-E7 to learn where a rebuild differs; the result is never SHAP-ready")
    ap.add_argument("--arcsine-tolerance", type=float, default=0.0,
                    help="owner decision D8: the TRUE relative tolerance |rebuilt - saved| <= tol |saved| of E8 on an "
                         "arcsine-link arm (default 0: bit identity), licensed only by the identity-twin proof (E5a "
                         "at this lead, or at lead 0 of the same engine and inputs plus the trees-off twin E5b)")
    ap.add_argument("--recorded-path-map", action="store_true",
                    help="owner decision D14 (b): hash the package's files under the run's recorded engine path")
    ap.add_argument("--package-dir", default=None,
                    help="owner decision D14 (a): the package folder to load (a real copy at the recorded path)")
    ap.add_argument("--precheck-only", action="store_true",
                    help="stop after gate E3a (the inputs before the target is read); writes precheck.json")
    ap.add_argument("--ignore-ram-warning", action="store_true",
                    help="go on although the engine's RAM pre-flight says the run will be refused after the census")
    ap.add_argument("--lead0-dir", default=None,
                    help="where lead 0's finished rebuild lies, when lead 0 is not rebuilt in this process (default: "
                         "rebuild/<problem>/lead_0, or <out-root>/lead_0 with several leads)")
    return ap.parse_args()


# ----------------------------------------------------------------------------------------- coefficient capture
def install_capture(RK, S, RR):
    """Wrap the router's work list and its solves (same arithmetic, line for line) to keep each fit's b."""
    orig_units = RK._solve_units

    def keyed(item):
        return item[0]

    def solve_units(plan, load, solve, workers):
        keep = CAPTURE["keep"]
        todo = [it for it in plan if keep is None or keyed(it) in keep]
        done = {}

        def solve2(loaded):
            item, values = loaded
            _TLS.item = item
            if CAPTURE["first_values"] is None and values is not None and not CAPTURE.get("off"):
                CAPTURE["first_values"] = (item, np.array(values, copy=True))
            try:
                return solve(loaded)
            finally:
                _TLS.item = None
        res = orig_units(todo, load, solve2, workers)
        for it, r in zip(todo, res):
            done[id(it)] = r
        out = []
        for it in plan:
            if id(it) in done:
                out.append(done[id(it)])
            else:                                   # a unit outside the sample: a placeholder, never read
                n = int(np.asarray(it[3]).size) if CAPTURE["kind"] == "per_unit" else 1
                out.append((np.zeros((n, 1)), np.zeros(n)) if CAPTURE["kind"] == "per_unit"
                           else (np.zeros(1), 0.0))
        return out

    def record(Xc, yc, Xt, b, ntree, nctx, n_unp, w):
        item = getattr(_TLS, "item", None)
        if item is None or not ntree or CAPTURE.get("off"):
            return
        CAPTURE["units"][item[0]] = {"item": item, "b": np.array(b, copy=True), "ntree": int(ntree),
                                     "nctx": int(nctx), "n_unp": int(n_unp),
                                     "Xc_lin": np.array(Xc[:, :n_unp + nctx], copy=True),
                                     "Xt_lin": np.array(Xt[:, :n_unp + nctx], copy=True),
                                     "eta_c": Xc @ b, "eta_t": Xt @ b, "weighted": w is not None}

    # The engine's own solve_point / solve_point_weighted run unchanged and their output is returned as is. b is
    # solved again by the same engine's solve_local with the same arguments (deterministic in one process), and
    # X_t b must equal the returned prediction bit for bit, else the row is flagged and the rebuild refuses.
    import inspect
    orig_point = S.solve_point
    orig_pointw = getattr(S, "solve_point_weighted", None)
    has_unp = "n_unpenalised" in inspect.signature(S.solve_local).parameters
    default_unp = getattr(S, "UNPENALISED_COLUMNS", 2)

    def local(Xc, yc, w, ntree, nctx, a_tree, a_ctx, n_unp):
        if has_unp:
            return S.solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx, n_unp)
        return S.solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx)

    def solve_point(Xc, yc, Xt, ntree, nctx, a_tree, a_ctx, *args, **kw):
        P = orig_point(Xc, yc, Xt, ntree, nctx, a_tree, a_ctx, *args, **kw)
        if ntree and getattr(_TLS, "item", None) is not None and not CAPTURE.get("off"):
            n_unp = kw.get("n_unpenalised", args[0] if args else default_unp)
            b = local(Xc, yc, np.ones(len(yc)), ntree, nctx, a_tree, a_ctx, n_unp)
            if not np.array_equal(Xt @ b, P):
                CAPTURE.setdefault("mismatch", []).append(_TLS.item[0])
            record(Xc, yc, Xt, b, ntree, nctx, n_unp, None)
        return P

    def solve_point_weighted(Xc, yc, w, Xt, ntree, nctx, a_tree, a_ctx, *args, **kw):
        P = orig_pointw(Xc, yc, w, Xt, ntree, nctx, a_tree, a_ctx, *args, **kw)
        if ntree and getattr(_TLS, "item", None) is not None and not CAPTURE.get("off"):
            n_unp = kw.get("n_unpenalised", args[0] if args else default_unp)
            ww = S.unit_mean_weights(w, Xc.shape[0]) if hasattr(S, "unit_mean_weights") else np.asarray(w, float)
            b = local(Xc, yc, ww, ntree, nctx, a_tree, a_ctx, n_unp)
            if not np.array_equal(Xt @ b, P):
                CAPTURE.setdefault("mismatch", []).append(_TLS.item[0])
            record(Xc, yc, Xt, b, ntree, nctx, n_unp, w)
        return P

    RK._solve_units = solve_units
    S.solve_point = solve_point
    if orig_pointw is not None:
        S.solve_point_weighted = solve_point_weighted
    if RR is not None and hasattr(RR, "_route") and hasattr(RR, "region_ridge"):
        orig_route, orig_ridge = RR._route, RR.region_ridge

        def route(rows, answers, table_kind, tree_columns, points, identity_tolerance, gram):
            _TLS.region = rows
            try:
                out = orig_route(rows, answers, table_kind, tree_columns, points, identity_tolerance, gram)
            finally:
                _TLS.region = None
            if not CAPTURE.get("off") and rows.group in CAPTURE["regions"]:
                try:                                  # the engine's own answers and recomputation (E9, E10)
                    region_extra(RR, rows, answers, table_kind, tree_columns, out)
                except Exception as exc:              # recorded; the region gates then fail (fail loud)
                    CAPTURE["regions"][rows.group]["extra_error"] = repr(exc)
            return out

        def region_ridge(gram, fit_y, lam, fit_normal=None):
            fit = orig_ridge(gram, fit_y, lam, fit_normal)
            rows = getattr(_TLS, "region", None)
            if rows is not None and not CAPTURE.get("off"):
                CAPTURE["regions"][rows.group] = {"fit": fit, "rows": rows}
            return fit
        RR._route, RR.region_ridge = route, region_ridge


def region_extra(RR, rows, answers, table_kind, tree_columns, out):
    """Inside the region kernel's call: the store's float32 answers of the sampled units' score rows and their own
    rows at or before the cut, and the engine's own region_predict of both with the fit just solved."""
    from treeroute import engine_constants as KK
    chk = RR._check_region_rows(rows, KK.REGION_ROUTER_ROW_BUDGET)
    keep = CAPTURE["keep"]
    rec = CAPTURE["regions"][rows.group]
    fit = rec["fit"]
    su = np.asarray([str(u) for u in np.asarray(rows.score_unit, dtype=object)], dtype=object)
    ms = np.ones(su.size, bool) if keep is None else np.isin(su, np.asarray(sorted(keep), dtype=object))
    fu = np.asarray([str(u) for u in np.asarray(rows.fit_unit, dtype=object)], dtype=object)
    mf = np.ones(fu.size, bool) if keep is None else np.isin(fu, np.asarray(sorted(keep), dtype=object))
    sk, fk = chk["sk"][ms], chk["fk"][mf]
    sT = RR._masked_view(answers, sk, table_kind, tree_columns, rows.group, "score")
    bT = RR._masked_view(answers, fk, table_kind, tree_columns, rows.group, "fit") if fk.size else None
    with RR._blas_limit():
        p_store = RR.region_predict(fit, sT, chk["sn"][ms])
        p_bg = RR.region_predict(fit, bT, chk["fn"][mf]) if fk.size else np.zeros(0)
    rec.update({"score_keys": np.array(sk), "score_T": np.array(sT, dtype=np.float32, copy=True),
                "score_time": np.asarray(rows.score_time)[ms].astype(np.int64),
                "score_normal": np.array(chk["sn"][ms]), "score_rows": np.array(chk["sr"][ms]),
                "score_unit": su[ms], "score_pred_engine": np.array(out.predictions[ms, 0]),
                "p_store": np.array(p_store), "bg_keys": np.array(fk), "bg_unit": fu[mf],
                "bg_time": np.asarray(rows.fit_time)[mf].astype(np.int64),
                "bg_normal": np.array(chk["fn"][mf]),
                "bg_T": None if bT is None else np.array(bT, dtype=np.float32, copy=True),
                "p_bg": np.array(p_bg)})


# ----------------------------------------------------------------------------------------- the recorded path map
def _norm_root(p):
    return str(p).replace("\\", "/").rstrip("/")


def _under_root(p, root):
    a, r = _norm_root(p).lower(), _norm_root(root).lower()
    return a == r or a.startswith(r + "/")


def map_raw(p):
    """Today's engine path p (raw string) as the run recorded it (the recorded engine root + the same tail)."""
    s = str(p)
    if PATHMAP["on"] and _under_root(s, PATHMAP["new"]):
        tail = s[len(_norm_root(PATHMAP["new"])):]
        out = PATHMAP["old_raw"] + tail
        PATHMAP["mapped"][s] = out
        return out
    return s


def install_path_map(RUN, CK, man, log):
    """D14 (b): wrap pipeline.run._file_list_sha and runs.checkpoint.file_stats so that a file under today's engine
    folder is hashed under the run's recorded engine folder (read from manifest.machine.file); size and mtime are
    those of today's file. Accepted only by gate E3m (content SHA-256, size and mtime equal the freeze lock's)."""
    mfile = (man.get("machine") or {}).get("file")
    if not mfile:
        raise SystemExit("REFUSED (D14): the run manifest records no machine file, so no recorded engine path")
    old = os.path.dirname(os.path.dirname(str(mfile)))
    new = C.engine_live_root()
    if os.path.basename(old.replace("\\", "/").rstrip("/")) != "engine" or os.path.basename(_norm_root(new)) != "engine":
        raise SystemExit("REFUSED (D14): the recorded or today's engine folder is not an 'engine' folder")
    PATHMAP.update({"on": True, "new": new, "old_raw": old, "mapped": {}})
    orig_sha = RUN._file_list_sha

    def file_list_sha(paths):
        pairs = sorted((map_raw(str(x)), str(x)) for x in set(str(x) for x in paths))
        items = []
        for mapped, real in pairs:
            st = os.stat(real)
            items.append([mapped.replace("\\", "/"), int(st.st_size), int(st.st_mtime_ns)])
        return RUN._sha_json(items)
    file_list_sha.__wrapped__ = orig_sha
    RUN._file_list_sha = file_list_sha
    if CK is not None and hasattr(CK, "file_stats"):
        def file_stats(paths):
            out = []
            for p in paths:
                st = os.stat(str(p))
                out.append([map_raw(str(p)).replace("\\", "/"), int(st.st_size), int(st.st_mtime_ns)])
            return out
        CK.file_stats = file_stats
    log("D14 (b) recorded path map ON: files under today's engine folder are hashed under the run's recorded engine "
        "folder (%s)" % C.redact(old))


def freeze_store_records():
    """{normalised path: [record, ...]} of every store file listed in the freeze locks (content SHA-256, size,
    mtime in seconds)."""
    import json
    out = {}
    for f in sorted(glob.glob(os.path.join(FREEZE_DIR, "FREEZE_*.lock.json"))):
        with open(f, encoding="utf-8") as fh:
            L = json.load(fh)
        for p, rec in (L.get("store_files") or {}).items():
            if isinstance(rec, dict) and "sha256" in rec:
                out.setdefault(_norm_root(p).lower(), []).append(dict(rec, lock=os.path.basename(f)))
    return out


def gate_path_map(gates, log):
    """E3m: every file the map renamed has today's content SHA-256, size and mtime (seconds) equal to every freeze
    lock record of its recorded path; at least one record per file."""
    recs = freeze_store_records()
    rows = []
    ok = True                                          # nothing mapped (no package file under the engine): nothing to prove
    for real, mapped in sorted(PATHMAP["mapped"].items()):
        st = os.stat(real)
        sha = C.sha256_file(real)
        found = recs.get(_norm_root(mapped).lower(), [])
        good = bool(found) and all(r["sha256"] == sha and int(r["size"]) == int(st.st_size)
                                   and int(r["mtime"]) == int(st.st_mtime_ns // 10 ** 9) for r in found)
        ok = ok and good
        rows.append({"today": real, "recorded": mapped, "sha256": sha, "size": int(st.st_size),
                     "lock_records": len(found), "locks": sorted(set(r["lock"] for r in found)), "equal": good})
    gate(gates, "E3m_recorded_path_map", ok, {"files": rows, "rule": "content SHA-256, size and mtime equal every "
                                                                     "freeze-lock record of the recorded path"}, log)


# ----------------------------------------------------------------------------------------- engine version guards
def code_hash():
    """The hash the run manifest records as engine_code_hash (runs/fingerprint.py engine_code_hash: per-module
    hashes with comments stripped)."""
    from treeroute.runs import fingerprint as F
    fn = getattr(F, "engine_code_hash", None)
    if not callable(fn):
        raise SystemExit("the engine has no engine_code_hash function")
    return fn()


DIAGNOSE = {"on": False, "failed": []}


def gate(gates, name, ok, values, log, stop=True):
    gates[name] = {"pass": bool(ok), "values": values}
    log("gate %s: %s %s" % (name, "PASS" if ok else "FAIL", C.redact(str(values))[:400]))
    if not ok and stop:
        DIAGNOSE["failed"].append(name)
    if stop and not ok and not (DIAGNOSE["on"] and name in ("E5_bank_fingerprint", "E6_c_and_tolerances",
                                                            "E7_gls_weight_model")):
        raise GateFailed(name)


class GateFailed(Exception):
    pass


def out_of(a, L):
    if a.out_root and len(a.leads_all) == 1:
        return C.makedirs(a.out_root)
    if a.out_root:
        return C.makedirs(os.path.join(a.out_root, "lead_%d" % L))
    return C.makedirs(C.rebuild_dir(a.problem, L))


def identity_of(a, eng, sample_sha):
    """What a finished lead's DONE.json must match to be reused on a resume."""
    return {"sample_sha256": sample_sha, "engine_root": C.norm(eng), "path_map": bool(a.recorded_path_map),
            "package_dir": C.norm(a.package_dir) if a.package_dir else None, "smoke_arm": a.smoke_arm,
            "script_sha256": C.sha256_file(os.path.abspath(__file__))}


def reusable(rec, ident, tol):
    """A finished lead is reused only under the same identity, and under the same D8 tolerance unless its E8 was
    bit-identical (a reversal of D8 then redoes it)."""
    for k, v in ident.items():
        if rec.get("identity", {}).get(k) != v:
            return False, "identity field %s differs" % k
    if not rec.get("e8_bit_identical") and float(rec.get("arcsine_tolerance", -1)) != float(tol):
        return False, "E8 relied on the tolerance %s, now %s" % (rec.get("arcsine_tolerance"), tol)
    return True, ""


def main():
    a = parse()
    if a.smoke_arm and a.kind != "smoke":
        raise SystemExit("REFUSED: --smoke-arm is for smoke worlds only")
    if a.recorded_path_map and a.package_dir:
        raise SystemExit("REFUSED: choose one form of D14 (--recorded-path-map or --package-dir)")
    P = C.PROBLEMS[a.problem]
    ref = os.path.abspath(a.reference or P["run"])
    a.leads_all = sorted(set(a.leads))
    log = C.Log("tr_rebuild_%s_leads%s%s" % (a.problem, "_".join(map(str, a.leads_all)),
                                              "_smoke" if a.kind == "smoke" else ""))
    eng = os.path.abspath(a.engine_root or P["engine"])
    sroot = a.sample_root or C.sample_dir(a.problem)
    ident = C.sample_identity(a.problem, sroot, a.register)
    a.ident = identity_of(a, eng, ident["sample_sha256"])
    todo = []
    for L in a.leads_all:
        out = out_of(a, L)
        done = os.path.join(out, "DONE.json")
        if os.path.isfile(done) and not a.precheck_only:  # resume: a finished lead under the same identity is kept
            rec = C.read_json(done)
            files_ok = bool(rec.get("files")) and all(
                os.path.isfile(os.path.join(out, f)) and C.sha256_file(os.path.join(out, f)) == h
                for f, h in rec.get("files", {}).items())
            same, why = reusable(rec, a.ident, a.arcsine_tolerance)
            if files_ok and same:
                log("rebuild %s lead %d: DONE.json found, files and identity match: skipped" % (a.problem, L))
                continue
            log("rebuild %s lead %d: DONE.json not reusable (%s): rebuilding" % (
                a.problem, L, "a file changed" if not files_ok else why))
            os.remove(C.assert_writable(done))
        todo.append(L)
    if not todo:
        return
    a.leads = todo
    a.lead = todo[0]
    sys.path.insert(0, eng)
    from treeroute import launch
    launch_rec = launch.pin_threads()             # the engine's pins: BLAS 4, oneDAL 4, router workers 8 at BLAS 1
    import treeroute
    if not C.norm(treeroute.__file__).startswith(C.norm(eng) + "/"):
        raise SystemExit("REFUSED: treeroute was imported from %s, not %s" % (C.redact(treeroute.__file__), eng))
    global np, pd, pq
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq
    from treeroute.route import kinds as RK
    from treeroute.route import solve as S
    try:
        from treeroute.route import region as RR
    except ImportError:
        RR = None
    install_capture(RK, S, RR)
    gates = {}
    DIAGNOSE["on"] = bool(a.diagnose)
    t_start = time.time()
    man = C.read_json(os.path.join(ref, "manifest.json"))
    if a.recorded_path_map:
        from treeroute.pipeline import run as RUN
        try:
            from treeroute.runs import checkpoint as CK
        except ImportError:
            CK = None
        install_path_map(RUN, CK, man, log)
    try:
        stopped = rebuild(a, P, ref, eng, man, gates, log, launch_rec)
    except GateFailed as exc:                         # a gate before any lead (E1-E3): every lead stops
        for L in a.leads:
            C.write_json(os.path.join(out_of(a, L), "gates.json"), {"gates": gates, "stopped_at": str(exc),
                                                                    "seconds": round(time.time() - t_start, 1)})
        log("STOP S-EXACT at gate %s: no SHAP value for %s leads %s" % (exc, a.problem, a.leads))
        sys.exit(3)
    log("rebuild %s leads %s finished in %.1f s (peak %s GB)%s" % (
        a.problem, a.leads, time.time() - t_start, C.rss_gb(), (" ; STOPPED: %s" % stopped) if stopped else ""))
    if stopped:
        sys.exit(3)


def reset_capture():
    CAPTURE.update({"units": {}, "regions": {}, "keep": None, "first_values": None, "mismatch": [], "off": False})
    CAPTURE.pop("pool", None)


def arm_by_name(LA, Link, name):
    for cand in LA.candidate_arms(tuple(Link)):
        if LA.arm_name(cand) == name:
            return cand
    raise SystemExit("REFUSED: no candidate arm is named %s" % name)


def read_decision(ref, lead, P_mod, log):
    """The run's saved decision at the lead: (arm spec, point, kept_is_tree, record)."""
    from treeroute.layer import arms as LA
    doc = C.read_json(os.path.join(ref, "adoption.json"))
    spec_nowcast = P_mod._arm_doc_spec(doc["adopted"]) if doc.get("adopted") else None
    best = P_mod._arm_doc_spec(doc["best_tree_arm"])
    point = P_mod._point_doc(doc["best_tree_penalty"] if doc["declined"] else doc["penalty"])
    if lead == 0:
        arm = spec_nowcast if not doc["declined"] else best
        kept_tree = not doc["declined"]
        return arm, point, kept_tree, {"declined": bool(doc["declined"]), "arm": LA.arm_name(arm)}
    rec = C.read_json(os.path.join(ref, "ladder", "lead_%d" % lead, "lead.json"))
    arm = best if doc["declined"] else spec_nowcast
    if LA.arm_name(arm) != rec["pinned"]:
        raise SystemExit("REFUSED: the pinned arm %s is not lead.json's %s" % (LA.arm_name(arm), rec["pinned"]))
    point = P_mod._point_doc(rec["penalty"])
    kept_tree = not bool(rec["declined_at_lead"])
    return arm, point, kept_tree, {"declined_at_lead": bool(rec["declined_at_lead"]), "arm": rec["pinned"],
                                   "adopted": rec.get("adopted")}


def precheck(a, P, pipe, man, gates, log):
    """E3a: every run-fingerprint part that needs no read or derive, key by key against the manifest's config, right
    after the target listing (before _read): a moved or changed input stops here in minutes."""
    import json
    from treeroute import engine_constants as K
    from treeroute.pipeline import data as D
    from treeroute.pipeline import run as RUN
    cfg = man["config"]
    mod = sys.modules[type(pipe).__module__]
    fls = getattr(mod, "_file_list_sha", RUN._file_list_sha)
    if a.recorded_path_map and mod is RUN:
        fls = RUN._file_list_sha                      # the mapped one (installed before the pipeline was built)
    comp = {}

    def put(key, fn):
        try:
            comp[key] = C._sanitize(fn())
        except Exception as exc:                      # not computable before the read: E3 checks it after derive
            comp[key] = {"_not_computed": repr(exc)[:200]}
    put("kind", lambda: pipe.kind)
    put("package", lambda: pipe.package.dataset.name)
    put("package_fingerprint", lambda: pipe.package.fingerprint)
    put("groups", lambda: list(pipe.run_groups))
    put("trees_per_group", lambda: pipe.trees_per_group)
    put("engine_constants_sha256", lambda: K.constants_hash())
    put("target_files_sha256", lambda: fls(pipe.data_files))
    put("static_files_sha256", lambda: fls([]) if P["kind"] == "neighbour" else fls(D.static_files(pipe.pkg)))
    put("context_list", lambda: list(pipe.spec.context))
    put("strata", lambda: list(pipe.spec.strata))
    put("draft", lambda: pipe.draft.record())
    differ, checked, skipped = [], [], []
    for k, v in sorted(comp.items()):
        if isinstance(v, dict) and "_not_computed" in v:
            skipped.append(k)
            continue
        if k not in cfg:
            skipped.append(k)
            continue
        checked.append(k)
        if json.dumps(v, sort_keys=True) != json.dumps(C._sanitize(cfg[k]), sort_keys=True):
            differ.append(k)
    tf = list(getattr(pipe.spec, "tree_features", ()) or ())
    if tf:
        checked.append("feature_list (tree-feature prefix)")
        if list(cfg.get("feature_list", []))[:len(tf)] != tf:
            differ.append("feature_list (tree-feature prefix)")
    # the package stores that resolve under the package folder (they move with it); informational
    moved = []
    try:
        for f in (D.static_files(pipe.pkg) if P["kind"] != "neighbour" else []):
            if _under_root(f, os.path.dirname(C.engine_live_root())) or _under_root(f, str(pipe.package.root)):
                moved.append(str(f))
    except Exception:
        pass
    vals = {"checked": checked, "differ": differ, "not_before_read": skipped,
            "static_files_sha256": [str(comp.get("static_files_sha256"))[:16], str(cfg.get("static_files_sha256"))[:16]],
            "target_files_sha256": [str(comp.get("target_files_sha256"))[:16], str(cfg.get("target_files_sha256"))[:16]],
            "package_files_under_the_package_folder": moved, "path_map": bool(a.recorded_path_map),
            "package_dir": a.package_dir}
    if differ and "static_files_sha256" in differ and not a.recorded_path_map and not a.package_dir:
        vals["note"] = ("the static table's path, size or mtime differs from the run's: after the 2026-11-08 "
                        "reinstall the package lives under another folder. Owner decision D14: (a) a real copy of "
                        "the package at the recorded path (--package-dir), or (b) --recorded-path-map")
    gate(gates, "E3a_inputs_before_read", not differ, vals, log)
    if a.recorded_path_map:
        gate_path_map(gates, log)


def rebuild(a, P, ref, eng, man, gates, log, launch_rec):
    import json
    from contextlib import ExitStack
    from treeroute.pipeline import passes as PS
    from treeroute.pipeline import stages as ST
    from treeroute.layer import arms as LA
    from treeroute.derive.shapes import CutKind, Link
    from treeroute.runs.machine import load_machine

    # E1, E2: engine code and libraries
    ch = code_hash()
    gate(gates, "E1_engine_code", ch == man["engine_code_hash"] or a.allow_engine_mismatch,
         {"engine": ch[:16], "manifest": man["engine_code_hash"][:16], "engine_root": eng}, log)
    vers = C.versions()
    want = man.get("versions") or {}
    diff = {k: (v, vers.get(k)) for k, v in want.items() if k in vers and vers.get(k) != v}
    gate(gates, "E2_versions", not diff and vers["python"] == str(man.get("python", vers["python"])).split()[0],
         {"differ": diff, "python": vers["python"]}, log)
    machine = load_machine(a.machine)
    for fld in ("run_root", "temp_dir"):
        C.assert_writable(getattr(machine, fld))
    decisions = {}
    for L in list(a.leads):
        arm, point, kept_tree, drec = read_decision(ref, L, PS, log)
        if a.smoke_arm:
            arm = arm_by_name(LA, Link, a.smoke_arm)
            drec["smoke_arm"] = a.smoke_arm
        log("decision at lead %d (read from the run): %s at level %r ratio %r; kept value is %s"
            % (L, LA.arm_name(arm), point.level, point.ratio, "this arm" if kept_tree else "the decline target"))
        if not kept_tree and not a.explain_pinned:
            C.write_json(os.path.join(out_of(a, L), "NOT_APPLICABLE.json"), {
                "problem": a.problem, "lead": L, "decision": drec,
                "reason": "the lead declined: the kept prediction is a feature-free baseline, so treeroute has no "
                          "feature attribution here (PROTOCOL.md 2, D5)"})
            log("lead %d declined: no treeroute SHAP (D5); NOT_APPLICABLE.json written" % L)
            continue
        decisions[L] = (arm, point)
    if not decisions and not a.precheck_only:
        return []
    sroot = a.sample_root or C.sample_dir(a.problem)
    sfile = os.path.join(sroot, "sample.parquet")
    sample = pq.read_table(sfile).to_pandas()
    pkg = a.package_dir or C.package_dir(a.problem)
    if P["kind"] == "neighbour":
        from treeroute.pipeline.table_run import TablePipeline as PL
        from treeroute.pipeline.table_passes import TableRunState as RS
    else:
        from treeroute.pipeline.run import Pipeline as PL
        RS = PS.RunState
    ram_warn = []

    def echo(m):
        if "will be refused" in str(m):              # the engine's own RAM pre-flight (report only at this point)
            ram_warn.append(str(m))
        log("engine| " + m)
    pipe = PL(pkg, machine.run_root, a.kind, machine=machine, echo=echo)
    t0 = time.time()
    try:
        pipe._lock()
        pipe._load()
        pipe._groups()
        pipe._preflight_target()
        log("engine steps load..preflight in %.1f s" % (time.time() - t0))
        gate(gates, "E0_ram_preflight", not ram_warn or a.ignore_ram_warning,
             {"engine_warning": [w[-260:] for w in ram_warn], "ignored": bool(a.ignore_ram_warning and ram_warn),
              "fix": "close other programs and start again (the engine needs the RAM it names), or "
                     "--ignore-ram-warning"}, log)
        precheck(a, P, pipe, man, gates, log)
        if a.precheck_only:
            for L in a.leads:
                C.write_json(os.path.join(out_of(a, L), "precheck.json"), {"gates": gates, "seconds":
                                                                           round(time.time() - t0, 1)})
            log("precheck only: E3a passed in %.1f s; stopping before the read" % (time.time() - t0))
            return []
        pipe._read()
        pipe._derive()
        if pipe.smoke:
            pipe._smoke_bank_plans(pipe._vault(None))
        pipe._open()
        if getattr(pipe, "per_group", False):
            pipe._release_census()
        pipe._temp()
        log("engine steps load..temp in %.1f s; rebuild run folder %s" % (time.time() - t0, pipe.folder))
        gate(gates, "E3_inputs", pipe.package.fingerprint == man["package_fingerprint"]
             and pipe.derived_sha == man["config"]["derived_sha256"] and pipe.fingerprint == man["fingerprint"],
             {"package": pipe.package.fingerprint[:16], "derived": pipe.derived_sha[:16],
              "fingerprint": pipe.fingerprint[:16], "manifest_fingerprint": man["fingerprint"][:16],
              "config_keys_differing": sorted(k for k in set(pipe.config) | set(man["config"])
                                              if json.dumps(pipe.config.get(k), sort_keys=True, default=str)
                                              != json.dumps(man["config"].get(k), sort_keys=True, default=str))},
             log)
        stopped = []
        common = dict(gates)
        evidence = {}
        with RS(pipe) as state:
            t1 = time.time()
            try:
                state.build_pool(need_inner=False)
            except TypeError:
                state.build_pool()
            log("pool built in %.1f s" % (time.time() - t1))
            for i, L in enumerate(sorted(decisions)):
                a.lead = L
                out = out_of(a, L)
                g = dict(common)
                reset_capture()
                DIAGNOSE["failed"] = []
                t2 = time.time()
                arm, point = decisions[L]
                try:
                    result = route_and_save(a, P, ref, out, man, g, log, pipe, state, arm, point, sample, launch_rec,
                                            ExitStack, PS, ST, LA, CutKind, Link, evidence)
                    C.write_json(os.path.join(out, "gates.json"), {"gates": g, "stopped_at": None, "result": result,
                                                                   "seconds": round(time.time() - t2, 1),
                                                                   "peak_gb": C.rss_gb()})
                    log("lead %d rebuilt in %.1f s (peak %s GB)" % (L, time.time() - t2, C.rss_gb()))
                except GateFailed as exc:
                    C.write_json(os.path.join(out, "gates.json"), {"gates": g, "stopped_at": str(exc),
                                                                   "seconds": round(time.time() - t2, 1)})
                    log("STOP S-EXACT at gate %s: no SHAP value for %s lead %d" % (exc, a.problem, L))
                    stopped.append(L)
                if "E5a_identity_twin" in g:              # the twin proof of this lead (licenses later leads, D8)
                    evidence[L] = {"pass": bool(g["E5a_identity_twin"]["pass"]), "source": "this process"}
                if L == 0 and i + 1 < len(decisions) and hasattr(state, "release_bank"):
                    try:                                 # the nowcast's bank is not read by the leads
                        state.release_bank(PS.BANK_FIT, "shap_v1: the next lead does not read it")
                    except Exception as exc:
                        log("the nowcast bank was not released early (%s); it is released at the end" % exc)
        return stopped
    finally:
        pipe._release()


def _fit_lead0(state, PS, ST, CutKind, Link, need_gls, log):
    """RunState.fit's nowcast lines without the inner bank (and without GLS unless the arm is weighted)."""
    from treeroute.fit.tables import TreeAnswerStore
    from treeroute.layer.links import c_for_cut_against_plan
    p = state.p
    if hasattr(state, "decline_to_donor_median"):           # the table run state's own fit (coral)
        state.fit(need_inner=False)
        return
    state.ctx_guard = state.ctx_fit.for_lead(0, CutKind.GUARD)
    state.donor_fit = state.donor(state.ctx_fit, "bank") if hasattr(state, "donor") else \
        state.ctx_fit.donor_rows("bank")
    if hasattr(state, "fit_bank"):                       # engines with per-group bank checkpoints
        state.bank_fit = state.fit_bank(state.donor_fit, PS.BANK_FIT)
    else:                                                # the PM2.5 engine (6d19c3e2): no bank checkpoints
        from treeroute.fit.bank import fit_donor_bank
        state.bank_fit = fit_donor_bank(state.donor_fit, p.trees_per_group)
    state._check_bank(state.bank_fit, "fit-cut")
    row_group = ST.row_group_of(state.vg)
    stack = state._bank_stack(PS.BANK_FIT) if hasattr(state, "_bank_stack") else state._stack
    try:
        st_obj = TreeAnswerStore.from_bank(state.bank_fit, row_group, p.temp_dir, p.registry, echo=p.log)
    except TypeError:                                    # older signature without echo
        st_obj = TreeAnswerStore.from_bank(state.bank_fit, row_group, p.temp_dir, p.registry)
    state.store_fit = stack.enter_context(st_obj)
    state.masks_fit = ST.block_masks(state.bank_fit.tree_group, p.blocks)
    state.c = c_for_cut_against_plan(state.donor_fit, state.derived) if Link.LOG_C in state.links else None
    state.tol, state.tol_record = ST.guard_tolerances(state.donor_fit, state.links, state.c, state.ub, p.smoke)
    state.donor_mean_fit = ST.donor_link_means(state.donor_fit, state.links, state.c, state.ub)
    state.weights = None
    if need_gls:
        from treeroute.fit.weights import weight_model_for_cut, weight_model_record
        from treeroute.derive.derived import derived_entry
        from treeroute.pipeline import record as REC
        store = state.answers_once(state.store_fit) if hasattr(state, "answers_once") else state.store_fit
        state.weights = weight_model_for_cut(state.ctx_fit, state.ctx_guard, store, state.bank_fit.tree_group,
                                             blocks=p.blocks, matrix_dir=p.temp_dir, echo=state.log)
        REC.write_once_or_same(p.folder / "gls_weight_model.json", derived_entry(weight_model_record(state.weights)))
    state.write_log_part("setup")


def _bank_record_check(gates, log, ref, lead, bank, donor_n, donor_hash, c, tol_record, weights_file):
    import json
    import pyarrow.parquet as pq
    if lead == 0:
        fx = pq.read_table(os.path.join(ref, "fitctx_log.parquet")).to_pandas()
        r = fx[(fx["object_kind"] == "donor_rows") & (fx["purpose"] == "bank")].iloc[0]
        want_n, want_h = int(r["n_rows"]), str(r["row_key_hash"])
        want_fp = C.read_json(os.path.join(ref, "tables.json"))["fit_cut_store"]["bank_fingerprint"]
        dc = C.read_json(os.path.join(ref, "decision_checks.json"))
        want_c, want_tol = dc.get("c"), dc.get("tolerances")
        gls_ref = os.path.join(ref, "gls_weight_model.json")
    else:
        rec = C.read_json(os.path.join(ref, "ladder", "lead_%d" % lead, "lead.json"))
        b = rec["fits"]["bank"]
        want_n, want_h, want_fp = int(b["donor_rows"]), str(b["donor_row_key_hash"]), b["fingerprint"]
        want_c, want_tol = rec["fits"].get("c"), rec["fits"].get("tolerances")
        gls_ref = os.path.join(ref, "ladder", "lead_%d" % lead, "gls_weight_model.json")
    n = int(donor_n)
    gate(gates, "E4_donor_rows", n == want_n and str(donor_hash) == want_h,
         {"rows": [n, want_n], "row_key_hash": [str(donor_hash)[:16], want_h[:16]]}, log)
    fp = bank.manifest.bank_fingerprint
    # informational: the fingerprint hashes every node array of every tree, corrector and placebo. On the coral
    # pilot (2026-11-12) it moved after the OS reinstall while every tree answer stayed bit-identical (E5a, E8 on
    # identity and log_c arms, E10). The cause is NOT established; the answer-level gates decide (PROTOCOL.md 4.1).
    gate(gates, "E5_bank_fingerprint", fp == want_fp, {"rebuilt": fp, "run": want_fp, "trees": len(bank.trees),
                                                       "role": "informational, cause not established (answers "
                                                               "decide: E5a, E8, E10)"},
         log, stop=False)
    same_c = (c is None and want_c is None) or (c is not None and want_c is not None and float(c) == float(want_c))
    gate(gates, "E6_c_and_tolerances", same_c and json.dumps(C._sanitize(tol_record), sort_keys=True)
         == json.dumps(C._sanitize(want_tol), sort_keys=True), {"c": [c, want_c]}, log)
    if weights_file is not None:
        got = C.read_json(weights_file)
        want = C.read_json(gls_ref)
        gate(gates, "E7_gls_weight_model", json.dumps(got, sort_keys=True) == json.dumps(want, sort_keys=True),
             {"rebuilt": weights_file, "run": gls_ref}, log)


def lead0_evidence(a, evidence, gates, log):
    """The lead-0 identity-twin proof that may license D8 at a lead with no saved twin: E5a passed in this process,
    or lead 0's gates.json (a finished, reusable lead-0 rebuild) passed E5a under the same engine code, libraries,
    run fingerprint and identity. Returns (licensed, source)."""
    if evidence.get(0, {}).get("pass"):
        return True, "lead 0 E5a in this process"
    if a.lead0_dir:
        d0 = a.lead0_dir
    elif 0 in a.leads_all:
        d0 = out_of(a, 0)
    else:
        d0 = os.path.join(a.out_root, "lead_0") if a.out_root else C.rebuild_dir(a.problem, 0)
    gf, df = os.path.join(d0, "gates.json"), os.path.join(d0, "DONE.json")
    if not (os.path.isfile(gf) and os.path.isfile(df)):
        return False, "no lead-0 E5a in this process and no finished lead-0 rebuild"
    g0, d0rec = C.read_json(gf), C.read_json(df)
    ok, why = reusable(d0rec, a.ident, a.arcsine_tolerance)
    e5a = (g0.get("gates") or {}).get("E5a_identity_twin", {})
    same = all((g0.get("gates") or {}).get(k, {}).get("values") == gates.get(k, {}).get("values")
               for k in ("E1_engine_code", "E2_versions"))
    fp_same = ((g0.get("gates") or {}).get("E3_inputs", {}).get("values", {}).get("fingerprint")
               == gates.get("E3_inputs", {}).get("values", {}).get("fingerprint"))
    if ok and e5a.get("pass") and same and fp_same:
        return True, "lead 0 gates.json (same engine, libraries, fingerprint and identity)"
    return False, "lead 0 gates.json does not license it (%s)" % (why or "E5a failed or the engine/inputs differ")


def route_and_save(a, P, ref, out, man, gates, log, pipe, state, arm, point, sample, launch_rec, ExitStack, PS, ST,
                   LA, CutKind, Link, evidence):
    from treeroute.layer.links import clip_to_legal
    state.adoption = None
    weighted = arm.weighting is LA.Weighting.GLS
    lead = a.lead
    CAPTURE["kind"] = P["kind"] if P["kind"] != "neighbour" else "neighbour"
    if lead > 0:
        doc = C.read_json(os.path.join(ref, "adoption.json"))
        state.adoption = PS.LD.Adoption(
            adopted=PS._arm_doc_spec(doc.get("adopted")), penalty=PS._point_doc(doc.get("penalty")),
            declined=bool(doc["declined"]), best_tree_arm=PS._arm_doc_spec(doc["best_tree_arm"]),
            best_tree_penalty=PS._point_doc(doc["best_tree_penalty"]),
            eligible=tuple(PS._arm_doc_spec(x) for x in doc.get("eligible", [])),
            surface_mae=dict(doc.get("surface_mae", {})),
            beside={k: (float("nan") if v is None else v) for k, v in doc.get("beside", {}).items()})
        levels0 = dict(C.read_json(os.path.join(ref, "decision_checks.json")).get("fallback_levels") or {})
        state.decided_levels = lambda: levels0
    with ExitStack() as stack:
        t1 = time.time()
        if lead == 0:
            _fit_lead0(state, PS, ST, CutKind, Link, weighted, log)
            bank, store, donor, c, tol, tol_record = (state.bank_fit, state.store_fit, state.donor_fit, state.c,
                                                      state.tol, state.tol_record)
            ctx, pool = state.ctx_fit, state.pool
            masks = getattr(state, "masks_fit", None)
            weights = state.weights if weighted else None
            donor_mean = getattr(state, "donor_mean_fit", None)
            wfile = os.path.join(str(pipe.folder), "gls_weight_model.json") if weighted else None
        else:
            if P["kind"] == "neighbour":
                from treeroute.pipeline.table_ladder import TableLadder
                lad = TableLadder(state)
                o = lad._objects(lead, stack)
                bank, store, donor, c, tol, tol_record = (o["bank"], o["store"], o["donor"], o["c"], o["tol"],
                                                          o["tol_record"])
                ctx, pool, weights, masks, donor_mean = o["ctx_fit"], o["pool"], o["weights"], None, None
            else:
                from treeroute.pipeline.ladder import Ladder
                lad = Ladder(state)
                o = lad._objects(lead, stack)
                bank, store, donor, c, tol, tol_record = (o.bank, o.store, None, o.c, o.tol, o.tol_record)
                ctx, pool, weights, masks, donor_mean = o.ctx_fit, o.pool, o.weights, o.masks, o.donor_mean_fit
                donor = getattr(o, "donor0", None)
            wfile = os.path.join(str(pipe.folder), "ladder", "lead_%d" % lead, "gls_weight_model.json") \
                if weighted else None
        log("bank and fits of lead %d in %.1f s" % (lead, time.time() - t1))
        if donor is not None:
            dn, dh = int(np.asarray(donor.y).size), str(donor.row_key_hash)
        else:                                    # the grid ladder records its donor rows before dropping them
            dn, dh = int(o.record["bank"]["donor_rows"]), str(o.record["bank"]["donor_row_key_hash"])
        _bank_record_check(gates, log, ref, lead, bank, dn, dh, c, tol_record, wfile)
        export_bank(out, bank, LA.table_kind(arm), log)
        # the saved rows of this lead, and the sample's units
        saved = pq.read_table(os.path.join(ref, "test_preds.parquet") if lead == 0 else
                              os.path.join(ref, "ladder", "lead_%d" % lead, "test_preds.parquet")).to_pandas()
        name = LA.arm_name(arm)
        units = sorted(set(sample["unit"].astype(str)))
        if P["kind"] == "neighbour":
            res = route_neighbour(a, state, ctx, store, bank, c, tol, weights, donor, point, arm, saved, sample,
                                  lead, o["lt"] if lead else state.data.leads[0], log)
        else:
            keep = None if a.all_units else set(units)
            if lead == 0:
                levels = dict(C.read_json(os.path.join(ref, "decision_checks.json")).get("fallback_levels") or {})
            else:
                levels = dict((C.read_json(os.path.join(ref, "ladder", "lead_%d" % lead, "lead.json")).get(
                    "fallback_levels") or {}).get("levels") or {})
            res = route_grid(a, P, state, ctx, store, masks, pool, bank, c, tol, donor_mean, weights, point, arm,
                             saved, keep, lead, levels, log, PS, ST, LA, out)
        eta, keys_routed = res["eta"], res["keys"]
        gate(gates, "E9_coefficients_reproduce_the_kernel", not CAPTURE.get("mismatch"),
             {"fits_captured": len(CAPTURE["units"]) or len(CAPTURE["regions"]),
              "fits_whose_X_b_differs_from_the_kernel": len(CAPTURE.get("mismatch", [])),
              "region_proof": res.get("region_proof")}, log)
        chk = saved.merge(keys_routed, on=["unit", "time"], how="inner")
        idx = chk["_pos"].to_numpy(np.int64)

        def compare(eta_, arm_):
            nm = LA.arm_name(arm_)
            pre_ = ST.inverse(eta_, arm_.link, c, state.ub)
            armv_ = clip_to_legal(pre_, state.legal, False)[0]
            sp_ = chk["pre__" + nm].to_numpy(np.float64)
            rp_, ra_ = np.asarray(pre_)[idx], np.asarray(armv_)[idx]
            has_arm = ("arm__" + nm) in chk.columns         # a twin may have only its pre__ column saved
            sa_ = chk["arm__" + nm].to_numpy(np.float64) if has_arm else ra_
            ok_p, rel_p, fail_p, ulp_p = C.relative_check(sp_, rp_, max(a.arcsine_tolerance, 0.0))
            ok_a, rel_a, fail_a, ulp_a = C.relative_check(sa_, ra_, max(a.arcsine_tolerance, 0.0))
            return {"arm": nm, "rows_checked": int(len(chk)), "units": int(chk["unit"].nunique()),
                    "pre_bit_equal": int((sp_ == rp_).sum()), "arm_bit_equal": int((sa_ == ra_).sum()),
                    "same_nan": bool(np.array_equal(np.isnan(sp_), np.isnan(rp_))),
                    "max_abs_pre": float(np.nanmax(np.abs(sp_ - rp_))) if len(chk) else None,
                    "max_rel_pre": rel_p, "max_rel_arm": rel_a, "max_ulps_pre": ulp_p, "max_ulps_arm": ulp_a,
                    "within_relative_tolerance": bool(ok_p and ok_a), "rows_outside_tolerance": fail_p + fail_a,
                    "bit_identical": bool(np.array_equal(sp_, rp_, equal_nan=True)
                                          and np.array_equal(sa_, ra_, equal_nan=True))}, sp_, rp_, sa_, ra_
        e8, sp, rp, sa, ra = compare(eta, arm)
        frame = chk[["unit", "time"]].copy()
        frame["pre_saved"], frame["pre_rebuilt"], frame["arm_saved"], frame["arm_rebuilt"] = sp, rp, sa, ra
        frame["eta"] = np.asarray(eta)[idx]
        C.write_parquet(os.path.join(out, "preds_check.parquet"), frame)

        def route_twin(twin, gname, required):
            CAPTURE["off"] = True
            try:
                rec, *_ = compare(res["other"](twin), twin)
            except Exception as exc:                 # a twin that cannot be routed proves nothing
                rec = {"arm": LA.arm_name(twin), "bit_identical": False, "error": repr(exc)[:300]}
            finally:
                CAPTURE["off"] = False
            gate(gates, gname, rec["bit_identical"], rec, log, stop=required)
            return bool(rec["bit_identical"])
        licence, e5a_ok = None, None
        if arm.link == Link.ARCSINE:
            twin = LA.ArmSpec(Link.IDENTITY, arm.tool, arm.weighting, True)
            if "pre__" + LA.arm_name(twin) in saved.columns:
                e5a_ok = route_twin(twin, "E5a_identity_twin", True)
                licence = "E5a at this lead (the arm's identity-link twin, bit-identical)" if e5a_ok else None
            else:
                gates["E5a_identity_twin"] = {"pass": None, "values": "the run saved no identity twin of %s at lead %d"
                                                                     % (name, lead)}
                off = LA.trees_off_of(Link.IDENTITY)
                e5b_ok = route_twin(off, "E5b_trees_off_twin", False) if "pre__" + LA.arm_name(off) in saved.columns \
                    else False
                lic0, src = lead0_evidence(a, evidence, gates, log)
                licence = ("%s, plus the trees-off twin E5b bit-identical" % src) if (lic0 and e5b_ok) else None
                if licence is None:
                    log("D8 not licensed at lead %d: lead-0 evidence: %s; E5b: %s" % (lead, src, e5b_ok))
        tol = float(a.arcsine_tolerance)
        within = (arm.link == Link.ARCSINE and tol > 0 and licence is not None and e8["same_nan"]
                  and e8["within_relative_tolerance"])
        e8["tolerance_rule"] = ("bit identity" if e8["bit_identical"] or not within else
                                "relative %.0e (|rebuilt - saved| <= %.0e |saved|, exact where saved is 0) on an "
                                "arcsine arm (owner decision D8), licensed by: %s" % (tol, tol, licence))
        e8["d8_licence"] = licence
        gate(gates, "E8_predictions", len(chk) > 0 and (e8["bit_identical"] or within), e8, log)
        res["save"](out, log, gates)
        result = {"arm": name, "point": {"level": point.level, "ratio": point.ratio}, "rows_checked": int(len(chk)),
                  "link": getattr(arm.link, "value", str(arm.link)), "c": c, "ub": state.ub,
                  "legal": list(state.legal), "kind": P["kind"], "table_kind": LA.table_kind(arm),
                  "weighted": weighted, "engine_folder": str(pipe.folder)}
        if DIAGNOSE["failed"]:
            C.write_json(os.path.join(out, "DIAGNOSE_ONLY.json"), {"failed_gates": DIAGNOSE["failed"],
                                                                    "note": "not SHAP-ready (stop rule S-EXACT)"})
            log("diagnose run: gates failed %s; no DONE.json (not SHAP-ready)" % DIAGNOSE["failed"])
            return dict(result, failed_gates=DIAGNOSE["failed"])
        C.write_json(os.path.join(out, "DONE.json"), dict(
            result, identity=a.ident, arcsine_tolerance=tol, e8_bit_identical=bool(e8["bit_identical"]),
            d8_licence=licence, sample_sha256=a.ident["sample_sha256"],
            files={f: C.sha256_file(os.path.join(out, f)) for f in ("bank.npz", "routers.npz", "rows.parquet",
                                                                    "preds_check.parquet")
                   if os.path.isfile(os.path.join(out, f))}))
        return result


def export_bank(out, bank, table_kind, log):
    """The bank's plain trees (and correctors for a corrector arm) as flat arrays, leaf values raw (float64)."""
    t0 = time.time()
    want_corr = table_kind == "corrector"
    arrs = {"left": [], "right": [], "feat": [], "thr": [], "val": []}
    carr = {"left": [], "right": [], "feat": [], "thr": [], "val": []}
    off, coff, has = [0], [0], []
    for t, cr in zip(bank.trees, bank.correctors):
        tr = t.tree_
        for k, v in (("left", tr.children_left), ("right", tr.children_right), ("feat", tr.feature),
                     ("thr", tr.threshold), ("val", tr.value.reshape(tr.node_count, -1)[:, 0])):
            arrs[k].append(np.asarray(v))
        off.append(off[-1] + tr.node_count)
        has.append(cr is not None and want_corr)
        if cr is not None and want_corr:
            ct = cr.tree_
            for k, v in (("left", ct.children_left), ("right", ct.children_right), ("feat", ct.feature),
                         ("thr", ct.threshold), ("val", ct.value.reshape(ct.node_count, -1)[:, 0])):
                carr[k].append(np.asarray(v))
            coff.append(coff[-1] + ct.node_count)
        else:
            coff.append(coff[-1])
    cat = lambda L, dt: np.concatenate(L).astype(dt) if L else np.zeros(0, dt)  # noqa: E731
    C.write_npz(os.path.join(out, "bank.npz"),
                left=cat(arrs["left"], np.int32), right=cat(arrs["right"], np.int32), feat=cat(arrs["feat"], np.int32),
                thr=cat(arrs["thr"], np.float64), val=cat(arrs["val"], np.float64), off=np.asarray(off, np.int64),
                c_left=cat(carr["left"], np.int32), c_right=cat(carr["right"], np.int32),
                c_feat=cat(carr["feat"], np.int32), c_thr=cat(carr["thr"], np.float64),
                c_val=cat(carr["val"], np.float64), c_off=np.asarray(coff, np.int64), has_corr=np.asarray(has, bool),
                tree_group=np.asarray(bank.tree_group, dtype=object).astype(str),
                tree_number=np.asarray(bank.tree_number, np.int64),
                fingerprint=np.asarray(bank.manifest.bank_fingerprint))
    log("bank exported: %d trees, %d correctors (%s), %.1f s" % (len(bank.trees), int(np.sum(has)), table_kind,
                                                               time.time() - t0))


def load_npz(path):
    """Every member of an .npz loaded ONCE (NpzFile re-reads a member on every access)."""
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def bank_tree(Z, k, corr=False):
    import shapv1_treeshap as TS
    p = "c_" if corr else ""
    o = Z[p + "off"]
    s, e = int(o[k]), int(o[k + 1])
    return TS.from_arrays(Z[p + "left"][s:e], Z[p + "right"][s:e], Z[p + "feat"][s:e], Z[p + "thr"][s:e],
                          Z[p + "val"][s:e], leaf_float32=True)


def answers_of(Z, cols, X64, corrector):
    """Our tree answers (float32 arithmetic as the engine's table writer) for rows X64 at bank columns cols."""
    import shapv1_treeshap as TS
    out = np.empty((X64.shape[0], len(cols)), np.float32)
    for j, k in enumerate(cols):
        v = TS.predict(bank_tree(Z, int(k)), X64).astype(np.float32)
        if corrector and bool(Z["has_corr"][int(k)]):
            v = v + TS.predict(bank_tree(Z, int(k), True), X64).astype(np.float32)
        out[:, j] = v
    return out


def route_neighbour(a, state, ctx, store, bank, c, tol, weights, donor, point, arm, saved, sample, lead, lt, log):
    """Coral: every saved test row of the lead through the engine's NeighbourPass (all rows: cheap), coefficients
    of every row captured; the sample's rows and their pools saved for SHAP."""
    from treeroute.pipeline.table_router import NeighbourPass, PassPart
    from treeroute.pipeline import record as REC
    from treeroute.layer import arms as LA
    rows_id = np.asarray(state.data.row_ids, dtype=object).astype(str)
    pos_of = {r: i for i, r in enumerate(rows_id.tolist())}
    t_keys = np.asarray([pos_of[str(u)] for u in saved["unit"].tolist()], np.int64)
    CAPTURE["keep"] = None
    part = PassPart(name="all", score_index=np.arange(t_keys.size, dtype=np.int64), c=c, model=weights,
                    fallback_donor=donor)
    t0 = time.time()
    npass = NeighbourPass(state, getattr(REC, "S1_TEST_PASS", "test pass") if lead == 0 else "lead %d test pass" % lead,
                          ctx, store, bank.tree_group, lead, lt, t_keys, [part], tol)
    routed = npass.route([arm], point)
    name = LA.arm_name(arm)
    eta = np.asarray(routed.predictions[name][:, 0], np.float64)
    log("neighbour pass: %d rows routed in %.1f s; %d row fits captured" % (t_keys.size, time.time() - t0,
                                                                           len(CAPTURE["units"])))
    capt = CAPTURE["units"]
    bad = [i for i in range(t_keys.size) if i not in capt or float(capt[i]["eta_t"][0]) != eta[i]]
    if bad:
        CAPTURE.setdefault("mismatch", []).extend(bad[:50])
        log("%d captured row fits do not give the pass's own predictions (E9 fails)" % len(bad))
    keys = pd.DataFrame({"unit": saved["unit"].astype(str).to_numpy(), "time": saved["time"].to_numpy(np.int64),
                         "_pos": np.arange(t_keys.size)})
    cand_keys = np.asarray(npass.cand_arrays["keys"], np.int64)

    def save(out, log, gates):
        Z = load_npz(os.path.join(out, "bank.npz"))
        feats = ST_zero(ctx)
        si = {u: i for i, u in enumerate(saved["unit"].astype(str).tolist())}
        rows = sample["unit"].astype(str).tolist()
        n_bank = len(bank.trees)
        nl = capt[si[rows[0]]]["nctx"] + capt[si[rows[0]]]["n_unp"]
        B = np.zeros((len(rows), n_bank))
        M = np.zeros((len(rows), n_bank), bool)
        lin = np.zeros((len(rows), nl))
        b_lin = np.zeros((len(rows), nl))
        eta_t = np.zeros(len(rows))
        pool_ids, pool_eta, pool_lin = [], [], []
        for r, u in enumerate(rows):
            rec = capt[si[u]]
            i_, idx, cols, drop, _v = rec["item"]
            B[r, np.asarray(cols)] = rec["b"][nl:]
            M[r, np.asarray(cols)] = True
            b_lin[r] = rec["b"][:nl]
            lin[r] = rec["Xt_lin"][0]
            eta_t[r] = rec["eta_t"][0]
            pool_ids.append(rows_id[cand_keys[np.asarray(idx)]])
            pool_eta.append(rec["eta_c"])
            pool_lin.append(rec["Xc_lin"])
        # features: the explained rows and the union of their pools
        allpool = sorted(set(np.concatenate(pool_ids).tolist()))
        ppos = np.asarray([pos_of[u] for u in allpool], np.int64)
        epos = np.asarray([pos_of[u] for u in rows], np.int64)
        Xe = np.asarray(feats(epos), np.float32)
        Xp = np.asarray(feats(ppos), np.float32)
        pidx = {u: j for j, u in enumerate(allpool)}
        bg = [np.asarray([pidx[u] for u in ids], np.int64) for ids in pool_ids]
        C.write_npz(os.path.join(out, "routers.npz"), b_tree=B, b_mask=M, b_lin=b_lin, lin_e=lin, eta_e=eta_t,
                    x_e=Xe, x_bg=Xp, bg_ptr=np.cumsum([0] + [len(x) for x in bg]).astype(np.int64),
                    bg_idx=np.concatenate(bg), bg_eta=np.concatenate(pool_eta), bg_lin=np.concatenate(pool_lin),
                    bg_ids=np.asarray(allpool, dtype=object).astype(str), rows=np.asarray(rows, dtype=object).astype(str),
                    tree_features=np.asarray(list(ctx.features.tree_columns), dtype=object).astype(str),
                    context_columns=np.asarray(list(ctx.features.context_columns), dtype=object).astype(str),
                    layout=np.asarray("intercept,context(standardised),trees"))
        # E10: our tree answers against the engine's store on the first fitted row (bit for bit)
        fv = CAPTURE["first_values"]
        same, shape = False, None
        if fv is not None:
            item, values = fv
            i_, idx, cols, drop, _v = item
            Xr = np.asarray(feats(np.concatenate([cand_keys[np.asarray(idx)], t_keys[i_:i_ + 1]])), np.float32)
            ours = answers_of(Z, cols, Xr.astype(np.float64), LA.table_kind(arm) == "corrector")
            same = bool(np.array_equal(ours, np.asarray(values, np.float32)))
            shape = [int(Xr.shape[0]), int(len(cols))]
        gate(gates, "E10_exported_trees", same, {"rows_x_trees": shape, "what": "the first fitted row's pool and "
                                                                                "test row, every tree"}, log)
        pd.DataFrame({"row": sample["row"].to_numpy(), "unit": rows}).to_csv(os.path.join(out, "rows_index.csv"),
                                                                             index=False)
        C.write_parquet(os.path.join(out, "rows.parquet"), pd.DataFrame({"row": sample["row"].to_numpy(),
                                                                         "unit": rows, "eta": eta_t}))

    def other(arm2):
        if arm2.tool is LA.Tool.TREES_OFF:             # the pass's own trees-off kernel (route() does the same)
            off = np.full(t_keys.size, np.nan)
            for pt in npass.parts:
                rows2 = npass._rows(pt, arm2.link, False)
                vals, _, _ = npass.NB._trees_off_neighbour_pass(rows2, npass.p.blocks, pools=npass._pools(pt))
                off[np.asarray(pt.score_index, dtype=np.int64)] = vals
            return off
        r2 = npass.route([arm2], point)
        return np.asarray(r2.predictions[LA.arm_name(arm2)][:, 0], np.float64)
    return {"eta": eta, "keys": keys, "save": save, "other": other}


def ST_zero(ctx):
    from treeroute.pipeline import stages as ST
    return ST.zero_filled(ctx.features)


def route_grid(a, P, state, ctx, store, masks, pool, bank, c, tol, donor_mean, weights, point, arm, saved, keep, lead,
               levels, log, PS, ST, LA, out):
    """Per-unit and region kinds: the engine's PassRouter on every saved test row of the lead (the pass's plan and
    context standardisation over every scored unit), tree-answer tables built and units solved for the sample's
    units only."""
    from treeroute.pipeline import router as PR
    from treeroute.pipeline import record as REC
    vg = state.vg
    first = vg.test_first
    t_all = ST.unit_positions(vg, state.scored_units, first, None)
    key_of = {(str(u), int(t)): int(k) for u, t, k in zip(vg.unit_ids[t_all].tolist(), vg.steps[t_all].tolist(),
                                                           t_all.tolist())}
    su = saved["unit"].astype(str).tolist()
    st_ = saved["time"].astype(np.int64).tolist()
    if P["kind"] == "region":                       # the region kind routes only the sampled units' groups
        sel = [i for i, u in enumerate(su) if keep is None or u in keep]
    else:
        sel = list(range(len(su)))
    t_keys = np.asarray([key_of[(su[i], st_[i])] for i in sel], np.int64)
    t_units = vg.unit_ids[t_keys]
    t_steps = vg.steps[t_keys]
    kinds = (LA.table_kind(arm),)
    groups_all = tuple(state.groups)
    by_group = {}
    for u in (keep if keep is not None else set(map(str, state.scored_units))):
        by_group.setdefault(state.unit_group[u], []).append(u)
    feats = ST.zero_filled(pool)
    CAPTURE["pool"] = pool

    def build(g):
        us = sorted(by_group.get(g, []))
        if us:
            ids = ST.unit_positions(vg, us, None, None)
            for k in kinds:
                store.build(g, k, ids, feats)

    def drop(g):
        store.drop_group(g)
    walk = groups_all if P["kind"] != "region" else tuple(sorted(by_group))
    sched = PR.GroupTables(groups=walk, build=build, drop=drop) if hasattr(PR, "GroupTables") and \
        getattr(state, "per_group", False) else None
    if sched is None:
        for g in walk:
            build(g)
    what, purpose = (getattr(REC, "S1_TEST_PASS", "test pass"), "router_test") if lead == 0 else \
        ("lead %d test pass" % lead, "router_lead_test")
    inp = PR.PassInput(what, ctx, store, masks, pool, t_units, t_steps, t_keys, tol, donor_mean, purpose, c,
                       schedule=sched)
    wfn = state.weights_fn(weights, pool) if weights is not None else None
    CAPTURE["keep"] = keep
    t0 = time.time()
    router = PR.PassRouter(state, inp, state.kind, weights=wfn, fallback_levels=levels)
    routed = router.route([arm], point)
    name = LA.arm_name(arm)
    eta_pass = np.asarray(routed.predictions[name][:, 0], np.float64)
    log("%s pass: %d score rows, %d units / %d regions solved in %.1f s" % (P["kind"], len(t_keys),
                                                                           len(CAPTURE["units"]),
                                                                           len(CAPTURE["regions"]), time.time() - t0))
    keys = pd.DataFrame({"unit": [su[i] for i in sel], "time": [st_[i] for i in sel]})
    keys["_pos"] = np.arange(len(sel))
    if keep is not None:
        keys = keys[keys["unit"].isin(keep)]
    proof = None
    if P["kind"] == "per_unit":
        pr = router._pr[arm.link]
        saver = per_unit_saver(state, pr, masks, feats, bank, keep, arm, LA, eta_pass, log)
    else:
        proof = region_proofs(out, masks, feats, arm, LA, eta_pass, log)
        saver = region_saver(state, masks, feats, bank, keep, arm, LA, eta_pass, t_keys, log)

    def other(arm2):
        r2 = PR.PassRouter(state, inp, state.kind, weights=wfn, fallback_levels=levels).route([arm2], point)
        return np.asarray(r2.predictions[LA.arm_name(arm2)][:, 0], np.float64)
    return {"eta": eta_pass, "keys": keys, "save": saver, "other": other, "region_proof": proof}


def per_unit_saver(state, pr, masks, feats, bank, keep, arm, LA, eta_pass, log):
    def save(out, log, gates):
        capt = CAPTURE["units"]
        units = sorted(capt)
        if keep is not None and sorted(set(map(str, keep)) - set(map(str, capt))):
            lost = sorted(set(map(str, keep)) - set(map(str, capt)))
            gate(gates, "E9_coefficients_reproduce_the_kernel", False,
                 {"sampled_units_without_a_per_unit_fit": lost[:10], "count": len(lost),
                  "why": "routed by another kernel (e.g. the R12 short-history fallback): not explained by this code"},
                 log)
        n_bank = len(bank.trees)
        rec0 = capt[units[0]]
        nl = rec0["n_unp"] + rec0["nctx"]
        B = np.zeros((len(units), n_bank))
        M = np.zeros((len(units), n_bank), bool)
        BL = np.zeros((len(units), nl))
        rows = []
        for j, u in enumerate(units):
            r = capt[u]
            unit, group, hidx, tsel, _v = r["item"]
            cols = np.asarray(masks.columns_by_group[group], np.int64)
            if r["b"].size != nl + cols.size:
                raise GateFailed("E9_coefficients_reproduce_the_kernel")
            B[j, cols] = r["b"][nl:]
            M[j, cols] = True
            BL[j] = r["b"][:nl]
            fk, ft = np.asarray(pr.fit_keys)[hidx], np.asarray(pr.fit_time)[hidx]
            sk, stt = np.asarray(pr.score_keys)[tsel], np.asarray(pr.score_time)[tsel]
            if not np.array_equal(r["eta_t"], eta_pass[np.asarray(pr.score_rows)[tsel]]):
                gate(gates, "E9_coefficients_reproduce_the_kernel", False,
                     {"unit": u, "what": "the captured fit does not give the pass's predictions"}, log)
            for role, kk, tt, lin, eta in (("fit", fk, ft, r["Xc_lin"], r["eta_c"]),
                                          ("test", sk, stt, r["Xt_lin"], r["eta_t"])):
                for q in range(kk.size):
                    rows.append((j, str(u), role, int(kk[q]), int(tt[q]), float(eta[q])) + tuple(lin[q].tolist()))
        cols_lin = ["lin_%d" % i for i in range(nl)]
        R = pd.DataFrame(rows, columns=["u", "unit", "role", "key", "time", "eta"] + cols_lin)
        X = np.asarray(feats(R["key"].to_numpy(np.int64)), np.float32)
        fv = CAPTURE["first_values"]
        same, shape = False, None
        if fv is not None:                        # E10: our exported trees against the engine's store, bit for bit
            item, values = fv
            unit, group, hidx, tsel, _v = item
            keys = np.concatenate([np.asarray(pr.fit_keys)[hidx], np.asarray(pr.score_keys)[tsel]])
            Z = load_npz(os.path.join(out, "bank.npz"))
            cols = np.asarray(masks.columns_by_group[group], np.int64)
            ours = answers_of(Z, cols, np.asarray(feats(keys), np.float32).astype(np.float64),
                              LA.table_kind(arm) == "corrector")
            same = bool(np.array_equal(ours, np.asarray(values, np.float32)))
            shape = [int(keys.size), int(cols.size)]
        gate(gates, "E10_exported_trees", same, {"unit": str(fv[0][0]) if fv else None, "rows_x_trees": shape}, log)
        ccols = list(getattr(state.pool, "context_columns", ()) or ())
        try:
            craw = np.asarray(state_pool_context(state, pr, R["key"].to_numpy(np.int64)), np.float32) if ccols \
                else np.zeros((len(R), 0), np.float32)
        except Exception as exc:                  # the raw context is only used to prove duplicate columns
            log("raw context of the rows not read (%s): duplicate context columns cannot be proven, so they stay "
                "separate players" % exc)
            craw = np.zeros((len(R), 0), np.float32)
        C.write_parquet(os.path.join(out, "rows.parquet"), R)
        C.write_npz(os.path.join(out, "routers.npz"), units=np.asarray(units, dtype=object).astype(str), b_tree=B,
                    b_mask=M, b_lin=BL, x=X, ctx_raw=craw,
                    tree_features=np.asarray(list(pool_tree_columns(feats, state)), dtype=object).astype(str),
                    context_columns=np.asarray(ccols, dtype=object).astype(str),
                    layout=np.asarray("intercept,normal-centre,context(standardised),trees"))
        log("routers saved: %d units, %d rows (fit and test), %d linear columns" % (len(units), len(R), nl))
    return save


def state_pool_context(state, pr, keys):
    """Raw (unstandardised) router context of grid rows, read from the pass's pool."""
    pool = CAPTURE.get("pool") or state.pool
    return pool.context(keys)


def pool_tree_columns(feats, state):
    try:
        return tuple(state.pool.tree_columns)
    except AttributeError:
        return tuple(state.ctx_fit.features.tree_columns)


def region_proofs(out, masks, feats, arm, LA, eta_pass, log):
    """E9 and E10 for the region kind (they were vacuous before v3): for every sampled region,
    (1) our exported trees reproduce the engine store's float32 answers of the sampled units' score rows and of their
    own rows at or before the cut, bit for bit (E10);
    (2) the engine's region_predict with the captured fit on the store's answers gives the pass's eta, and on OUR
    answers gives it too, bit for bit (E9: float32 A @ float32 w, then the intercept and the normal term, as
    region._route).
    Mismatches go to CAPTURE['mismatch'] (E9) and CAPTURE['e10_bad']."""
    from treeroute.route import region as RR
    Z = load_npz(os.path.join(out, "bank.npz"))
    corr = LA.table_kind(arm) == "corrector"
    summary = {"regions": 0, "score_rows": 0, "background_rows": 0, "answers_equal": True, "eta_store_equal": True,
               "eta_ours_equal": True, "errors": []}
    for g, rec in sorted(CAPTURE["regions"].items()):
        summary["regions"] += 1
        if "extra_error" in rec or "score_T" not in rec:
            summary["errors"].append("%s: %s" % (g, rec.get("extra_error", "no capture")))
            CAPTURE.setdefault("mismatch", []).append(g)
            continue
        cols = np.asarray(masks.columns_by_group[g], np.int64)
        sk, bk = rec["score_keys"], rec["bg_keys"]
        ours_s = answers_of(Z, cols, np.asarray(feats(sk), np.float32).astype(np.float64), corr)
        ok_s = bool(np.array_equal(ours_s, rec["score_T"]))
        ok_b = True
        if bk.size:
            ours_b = answers_of(Z, cols, np.asarray(feats(bk), np.float32).astype(np.float64), corr)
            ok_b = bool(np.array_equal(ours_b, rec["bg_T"]))
        with RR._blas_limit():
            p_ours = RR.region_predict(rec["fit"], np.ascontiguousarray(ours_s, dtype=np.float32), rec["score_normal"])
        want = eta_pass[np.asarray(rec["score_rows"], np.int64)]
        st_eq = bool(np.array_equal(rec["p_store"], want)) and bool(np.array_equal(rec["score_pred_engine"], want))
        ou_eq = bool(np.array_equal(p_ours, want))
        summary["score_rows"] += int(sk.size)
        summary["background_rows"] += int(bk.size)
        summary["answers_equal"] &= ok_s and ok_b
        summary["eta_store_equal"] &= st_eq
        summary["eta_ours_equal"] &= ou_eq
        if not (st_eq and ou_eq):
            CAPTURE.setdefault("mismatch", []).append(g)
        if not (ok_s and ok_b):
            CAPTURE.setdefault("e10_bad", []).append(g)
    log("region proofs: %s" % summary)
    if CAPTURE.get("e10_bad"):
        CAPTURE.setdefault("mismatch", []).extend(CAPTURE["e10_bad"])
    return summary


def region_saver(state, masks, feats, bank, keep, arm, LA, eta_pass, t_keys, log):
    def save(out, log, gates):
        regs = sorted(CAPTURE["regions"])
        gate(gates, "E10_exported_trees", not CAPTURE.get("e10_bad") and all(
            "score_T" in CAPTURE["regions"][g] for g in regs),
             {"regions": len(regs), "what": "every sampled unit's score rows and pre-cut rows, every tree of the "
                                            "region's columns"}, log)
        n_bank = len(bank.trees)
        W = np.zeros((len(regs), n_bank))
        Mk = np.zeros((len(regs), n_bank), bool)
        lin = np.zeros((len(regs), 3))
        rows, bgr = [], []
        for j, g in enumerate(regs):
            rec = CAPTURE["regions"][g]
            fit = rec["fit"]
            cols = np.asarray(masks.columns_by_group[g], np.int64)
            W[j, cols] = np.asarray(fit.w, np.float32).astype(np.float64)
            Mk[j, cols] = True
            lin[j] = [float(fit.intercept), float(fit.normal_coef or 0.0), float(fit.normal_centre or 0.0)]
            for k, tt, u, nn, sr in zip(rec["score_keys"], rec["score_time"], rec["score_unit"],
                                        rec["score_normal"], rec["score_rows"]):
                rows.append((j, str(u), "test", int(k), int(tt), float(eta_pass[int(sr)]), float(nn)))
            for k, tt, u, nn, pe in zip(rec["bg_keys"], rec["bg_time"], rec["bg_unit"], rec["bg_normal"],
                                        rec["p_bg"]):
                bgr.append((j, str(u), "fit", int(k), int(tt), float(pe), float(nn)))
        R = pd.DataFrame(rows + bgr, columns=["g", "unit", "role", "key", "time", "eta", "normal"])
        vg = state.vg
        units = sorted(set(R["unit"]))
        from treeroute.pipeline import stages as ST
        allk = ST.unit_positions(vg, units, None, None)
        X = np.asarray(feats(allk), np.float32)
        C.write_parquet(os.path.join(out, "rows.parquet"), R)
        C.write_npz(os.path.join(out, "routers.npz"), regions=np.asarray(regs, dtype=object).astype(str), w=W,
                    w_mask=Mk, lin=lin, all_keys=np.asarray(allk, np.int64),
                    all_units=vg.unit_ids[allk].astype(str), all_time=np.asarray(vg.steps[allk], np.int64), x=X,
                    tree_features=np.asarray(list(pool_tree_columns(feats, state)), dtype=object).astype(str),
                    layout=np.asarray("intercept + float32(A) @ float32(w) + g (normal - centre)"))
        log("region routers saved: %d regions, %d test rows and %d pre-cut rows of sampled units (engine eta of "
            "both kept for the evaluator check)" % (len(regs), len(rows), len(bgr)))
    return save


if __name__ == "__main__":
    main()
