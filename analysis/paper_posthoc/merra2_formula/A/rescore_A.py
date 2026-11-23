"""POST HOC re-score of the MERRA-2 PM2.5 human rivals with the GMAO formula (owner ruling AM1, 2026-10-27).
Implementer A = TOOL PATH. Spec: D:/treeroute/analysis/paper_posthoc/merra2_formula/SPEC.md

Run:  py -3.9 -I D:/treeroute/analysis/paper_posthoc/merra2_formula/A/rescore_A.py

The human-rival tool's own functions are imported read-only and called directly (never its CLI):
  x            adapters/pm25_reanalysis.build (Product reader, Grid bilinear interpolation, unit centres) through the
               tool's own IX.AdapterCtx (sha-checked product files) with a minimal log-only host ctx; the only change
               for the corrected input is options.variables OCSMASS 1.4 -> 1.0 (sulfate kept at 1.375).
  procedure    rivals_human.board: set_data, fit_candidate, predict_candidate, pick_of, _guard_labels_and_comparator,
               read_coverage, join_index, keys_frame; rivals_human.maps.candidates; harness H.inner_metrics, H.clip,
               H.saved_test_keys, H.to_saved_order; engine metrics.mae and decide.n2_eligible (the refit path of
               board._refit_one, step by step, with the board's sets tune -> inner, refit -> test).
  contrast     board._ours_frame + engine metrics.score_table + board._contrast (as board.score, the code path that
               merra2_runaway/sens_A.py reproduced exactly).
maps.py: the PRE-Part-B baseline copy (_moved/20261025T194657Z_partB_baseline/rivals_human/maps.py) is loaded as
rivals_human.maps, because maps.py changed after the PM2.5 board ran (Iso.fit signature + F6; F0-F5 unchanged).
Thread pools pinned to 8 before numpy (rivals_human/cli.py pin_threads) and limited by H.thread_state() as the board
did (load_board). sys.dont_write_bytecode is set first: no __pycache__ is written anywhere.

Gates 0a (x rebuild), 0b (locked lag1 procedure), 0c (locked deciding contrast) must pass before anything new.
Writes ONLY in this folder: result_A.json, preds_<rival>_<variant>.parquet, x_<rival>.parquet, _work/*, run log.
"""
import os
import sys

sys.dont_write_bytecode = True
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "8"                                  # rivals_human/cli.py PIN_VARS / PIN_VALUE

import copy                                              # noqa: E402
import gc                                                # noqa: E402
import hashlib                                           # noqa: E402
import importlib                                         # noqa: E402
import importlib.util                                    # noqa: E402
import json                                              # noqa: E402
import math                                              # noqa: E402
import time                                              # noqa: E402
from pathlib import Path                                 # noqa: E402
from types import SimpleNamespace                        # noqa: E402

HUMAN = Path(r"D:\treeroute\human_rivals_build\human")
BASELINE = Path(r"D:\treeroute\human_rivals_build\_moved\20261025T194657Z_partB_baseline")
CONFIG = HUMAN / "human_rivals_production.yaml"
BOARD = Path(r"D:\treeroute\rivals_human\pm25\20261007_74e67609")
INDEX = Path(r"D:\treeroute\human_index\pm25\20261007_74e67609")
RIVALS_TABLE = Path(r"D:\treeroute\rivals_table\20261025T162302876402Z\RIVALS_TABLE.csv")
OUT = Path(r"D:\treeroute\analysis\paper_posthoc\merra2_formula\A")
WORK = OUT / "_work"
SCRIPT = Path(os.path.abspath(__file__))
LEAD = 0
THRESH = 1000.0
YAK_UNIT, YAK_MONTH = "yakutia_larch_3553_2232", "2021-08"
RIVALS = ("merra2_lag1", "merra2_same", "merra2_lag1_placebo")
SO4_GMAO = 132.14 / 96.06
LOCKED_GUARD = {"rival_mae": 3.5208945819429056, "comparator_mae": 3.5256518387286944, "rows": 68559, "passed": True}

sys.path.insert(0, str(HUMAN))
import numpy as np                                       # noqa: E402
import pandas as pd                                      # noqa: E402
import pyarrow.parquet as pq                             # noqa: E402

import rivals_human                                      # noqa: E402
from rivals_human import config as C                     # noqa: E402

# the pre-Part-B maps.py as rivals_human.maps (before board.py imports it)
_spec = importlib.util.spec_from_file_location("rivals_human.maps", str(BASELINE / "rivals_human" / "maps.py"))
MP = importlib.util.module_from_spec(_spec)
sys.modules["rivals_human.maps"] = MP
_spec.loader.exec_module(MP)
rivals_human.maps = MP
from rivals_human import common as CM                    # noqa: E402
from rivals_human import slim as S                       # noqa: E402
from rivals_human import index as IX                     # noqa: E402
from rivals_human import lockfile as LK                  # noqa: E402
from rivals_human import board as B                      # noqa: E402
AD = importlib.import_module("adapters.pm25_reanalysis")
assert B.MP is MP, "board.py did not take the baseline maps.py"
assert Path(AD.__file__).resolve() == (HUMAN / "adapters" / "pm25_reanalysis.py").resolve()

LOGP = OUT / "rescore_A.log"


def log(msg):
    line = "%s | %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOGP, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return float(o) if math.isfinite(float(o)) else str(float(o))
    if isinstance(o, Path):
        return str(o)
    return o


def dump(path, obj):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(clean(obj), fh, indent=1)


def month_of_time(t):
    t = int(t)
    return "%04d-%02d" % ((t - 1) // 12, (t - 1) % 12 + 1)


def maxdiff(a, b):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    na, nb = np.isnan(a), np.isnan(b)
    same_nan = bool(np.array_equal(na, nb))
    ok = ~na & ~nb
    d = np.abs(a[ok] - b[ok])
    den = np.maximum(np.abs(b[ok]), 1e-300)
    return {"max_abs_diff": float(d.max()) if d.size else 0.0,
            "max_rel_diff": float((d / den).max()) if d.size else 0.0,
            "nan_positions_equal": same_nan, "bitwise_equal": same_nan and a[ok].tobytes() == b[ok].tobytes(),
            "rows_compared": int(ok.sum())}


class HostCtx(object):
    """Minimal host context: the tool's functions read ctx.H (guard comparator) and an adapter ctx logs through
    hctx.log. Every write method refuses (this script never writes through the tool)."""

    def __init__(self, H):
        self.H = H

    def log(self, stage, learner="", trial="", seconds=None, message="", echo=True):
        log("tool | %s | %s | %s | %s" % (stage, learner, trial, message))

    def _no(self, *a, **k):
        raise RuntimeError("the post hoc script never writes through the tool")

    mkdir = replace_bytes = replace_json = write_parquet = write_once_json = move_aside = _no


# ===================================================================================================== setup
def setup():
    cfg = C.load_config(str(CONFIG))
    LY, H = CM.load(cfg)
    hc = H.load_config(cfg.roots_mapping())
    eng = H.Engine(hc)
    th = H.thread_state()                                 # as board.load_board: pools limited to 8
    board = C.read_json(BOARD / C.BOARD_FILE)
    run = H.Run(board["run"]["folder"])
    registry = C.load_registry(cfg, run.package)
    products = C.load_products(cfg)
    token = LK.verify_lock(BOARD)                         # read-only: lock file, picks sha, ledger
    by_id = B.rival_by_id(registry)
    # tool code sha with the baseline maps.py in place of the current one (recipe of common.tool_code_sha)
    parts = []
    for p in C.code_files():
        src = BASELINE / "rivals_human" / "maps.py" if (p.parent.name, p.name) == ("rivals_human", "maps.py") else p
        parts.append(["%s/%s" % (p.parent.name, p.name), hashlib.sha256(src.read_bytes()).hexdigest()])
    tcs = hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode("ascii")).hexdigest()
    # the board-time tool (32ec5df0): Part 621 T-F15 a recipe (no adapters/fire_*.py, baseline maps.py) with the
    # pre-Part-618 refs.py (Part 618: 32ec5df0 -> cd956f1d changed refs.py only; old copy kept in _moved/)
    old_refs = BASELINE.parent / "refs.py.before_offset_fix_20261025"
    parts_b = []
    for p in C.code_files():
        if p.parent.name == "adapters" and p.name.startswith("fire_"):
            continue
        src = {("rivals_human", "maps.py"): BASELINE / "rivals_human" / "maps.py",
               ("rivals_human", "refs.py"): old_refs}.get((p.parent.name, p.name), p)
        parts_b.append(["%s/%s" % (p.parent.name, p.name), hashlib.sha256(src.read_bytes()).hexdigest()])
    tcs_b = hashlib.sha256(json.dumps(parts_b, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True).encode("ascii")).hexdigest()
    rfs = H.run_file_shas(run)
    base_prod = C._yaml(BASELINE / "registry" / "_products.yaml")["products"]
    cur_prod = C._yaml(cfg.path("on_disk_products"))["products"]
    env = {
        "tool_code_sha256_board": board["tool_code_sha256"],
        "tool_code_sha256_now_current_files": CM.tool_code_sha(),
        "tool_code_sha256_now_with_baseline_maps": tcs,
        "tool_code_sha256_with_baseline_maps_equals_board": tcs == board["tool_code_sha256"],
        "tool_code_sha256_board_recipe": tcs_b,
        "tool_code_sha256_board_recipe_equals_board": tcs_b == board["tool_code_sha256"],
        "tool_code_board_recipe": "every rivals_human/*.py and adapters/*.py except adapters/fire_*.py (added in "
                                  "Part B after the board), with maps.py = the Part-B baseline copy and refs.py = "
                                  "_moved/refs.py.before_offset_fix_20261025 (refs.py is not imported here)",
        "tool_files_sha256_used": {a: b for a, b in parts},
        "baseline_maps_py": str(BASELINE / "rivals_human" / "maps.py"),
        "baseline_maps_py_sha256": sha256(BASELINE / "rivals_human" / "maps.py"),
        "current_maps_py_sha256": sha256(HUMAN / "rivals_human" / "maps.py"),
        "harness_code_sha256": H.harness_code_sha(), "harness_equals_board": H.harness_code_sha() == board[
            "common_harness_sha256"],
        "engine_live_file_sha": H.engine_file_sha(),
        "engine_equals_board": H.engine_file_sha() == board["engine"]["live_file_sha"],
        "library_versions": H.library_versions(),
        "library_versions_equal_board": H.library_versions() == board["versions"],
        "thread_state": th, "thread_state_equals_board": th == board["threadpool_info"],
        "run_fingerprint_equals_board": run.fingerprint == board["run"]["fingerprint"],
        "run_file_sha256": rfs,
        "run_file_sha256_equal_board": rfs == board["run"]["file_sha256"],
        "config_equals_board": cfg.as_dict() == board["config"],
        "registry_shas_now": B._registry_shas(cfg, registry),
        "registry_shas_board": {k: v for k, v in board["registry"].items() if k != "file"},
        "products_registry_baseline_sha256": sha256(BASELINE / "registry" / "_products.yaml"),
        "pm25_product_entries_equal_baseline": all(base_prod[k] == cur_prod[k]
                                                    for k in ("merra2_aer_monthly", "pm25_static_cells")),
        "picks_sha256": token.picks_sha256,
        "slim_lead0_manifest_equals_board": S.open_slim(cfg, run, 0).manifest_sha == board["slim"]["0"][
            "manifest_sha256"],
    }
    log("setup: tool sha (board recipe) %s board %s; engine eq %s; harness eq %s; threads eq %s; libs eq %s"
        % (tcs_b[:12], board["tool_code_sha256"][:12], env["engine_equals_board"], env["harness_equals_board"],
           env["thread_state_equals_board"], env["library_versions_equal_board"]))
    return SimpleNamespace(cfg=cfg, H=H, eng=eng, board=board, run=run, registry=registry, products=products,
                           token=token, by_id=by_id, hctx=HostCtx(H), env=env)


# ===================================================================================================== x (adapter)
def build_x(T, rival, variables):
    """adapters.pm25_reanalysis.build with options.variables replaced; returns (frame, opened files)."""
    r = copy.deepcopy(rival)
    r["options"]["variables"] = dict(variables)
    sl = S.open_slim(T.cfg, T.run, LEAD)
    actx = IX.AdapterCtx(T.cfg, T.hctx, T.run, T.registry, T.products, r, LEAD, C.STAGE_ALL, sl, None)
    t0 = time.time()
    out = AD.build(actx, r, LEAD, "all")
    log("x build %s %s: %d rows in %.1f s" % (rival["id"], variables, len(out), time.time() - t0))
    return out, actx.opened


def variables_of(rival, oc=None, so4=None):
    v = dict(rival["options"]["variables"])
    if oc is not None:
        v["OCSMASS"] = oc
    if so4 is not None:
        v["SO4SMASS"] = so4
    return v


def x_tables(T, res):
    """Gate 0a and the corrected inputs. Returns {rival: frame(keys, x_locked, x_new[, x_gmao])}."""
    xt = {}
    gate = {}
    opened_all = {}
    for rid in RIVALS:
        rival = T.by_id[rid]
        assert rival["options"]["variables"] == {"DUSMASS25": 1.0, "SSSMASS25": 1.0, "BCSMASS": 1.0, "OCSMASS": 1.4,
                                                 "SO4SMASS": 1.375}, rival["options"]["variables"]
        xp = OUT / ("x_%s.parquet" % rid)
        idx = IX.read_index(T.cfg, T.run, rival, LEAD, stages=[C.STAGE_ALL])      # sha-checked vs its manifest
        if xp.is_file() and (WORK / ("x_%s.json" % rid)).is_file():
            rec = C.read_json(WORK / ("x_%s.json" % rid))
            if rec["sha256"] == sha256(xp) and rec["script_sha256"] == res["script_sha256"]:
                xt[rid] = pq.read_table(str(xp)).to_pandas()
                gate[rid] = rec["gate"]
                opened_all.update(rec["opened"])
                log("x %s: reused %s" % (rid, xp))
                continue
        fl, op = build_x(T, rival, variables_of(rival))
        opened_all.update({k: dict(v) for k, v in op.items()})
        keys_equal = all(np.array_equal(fl[k].astype(str).to_numpy() if k in ("unit", "group") else fl[k].to_numpy(),
                                        idx[k].astype(str).to_numpy() if k in ("unit", "group") else idx[k].to_numpy())
                         for k in C.KEYS)
        g = maxdiff(fl["x__pm25"], idx["x__pm25"])
        g.update(keys_equal_row_by_row=bool(keys_equal), rows=int(len(fl)),
                 info_end_equal=bool(np.array_equal(fl["info_end"].to_numpy(), idx["info_end"].to_numpy())),
                 product_cell_equal=bool(np.array_equal(fl["product_cell"].astype(str).to_numpy(),
                                                        idx["product_cell"].astype(str).to_numpy())),
                 src_equal=bool(np.array_equal(fl["src"].astype(str).to_numpy(), idx["src"].astype(str).to_numpy())))
        g["pass"] = bool(keys_equal and g["nan_positions_equal"] and g["max_rel_diff"] <= 1e-6)
        gate[rid] = g
        log("gate 0a %s: %s" % (rid, g))
        frame = idx[["unit", "time", "issue", "lead"]].copy()
        frame["x_locked_index"] = idx["x__pm25"].to_numpy(np.float64)
        frame["x_locked_rebuilt"] = fl["x__pm25"].to_numpy(np.float64)
        del fl
        gc.collect()
        if not g["pass"]:
            xt[rid] = frame
            continue
        fn, _ = build_x(T, rival, variables_of(rival, oc=1.0))
        assert np.array_equal(fn["unit"].astype(str).to_numpy(), frame["unit"].astype(str).to_numpy())
        assert np.array_equal(fn["time"].to_numpy(), frame["time"].to_numpy())
        assert np.array_equal(fn["issue"].to_numpy(), frame["issue"].to_numpy())
        frame["x_new"] = fn["x__pm25"].to_numpy(np.float64)
        del fn
        if rid == "merra2_lag1":
            fg, _ = build_x(T, rival, variables_of(rival, oc=1.0, so4=SO4_GMAO))
            assert np.array_equal(fg["unit"].astype(str).to_numpy(), frame["unit"].astype(str).to_numpy())
            frame["x_gmao"] = fg["x__pm25"].to_numpy(np.float64)
            del fg
        gc.collect()
        frame.to_parquet(str(xp), index=False)
        dump(WORK / ("x_%s.json" % rid), {"sha256": sha256(xp), "script_sha256": res["script_sha256"], "gate": g,
                                         "opened": opened_all})
        xt[rid] = frame
    res["gate_0a"] = gate
    res["inputs"]["products_opened_sha256_verified_by_tool"] = opened_all
    return xt


def idx_with(T, rid, xt, col):
    """The locked index table with x__pm25 replaced by column `col` of the x table (same row order, checked)."""
    idx = IX.read_index(T.cfg, T.run, T.by_id[rid], LEAD, stages=[C.STAGE_ALL])
    f = xt[rid]
    assert np.array_equal(idx["unit"].astype(str).to_numpy(), f["unit"].astype(str).to_numpy())
    assert np.array_equal(idx["time"].to_numpy(), f["time"].to_numpy())
    assert np.array_equal(idx["issue"].to_numpy(), f["issue"].to_numpy())
    if col != "x_locked_index":
        idx["x__pm25"] = f[col].to_numpy(np.float64)
    return idx


# ===================================================================================================== procedure
def procedure(T, rid, idx, mode, pinned=None, keep_trials=False):
    """mode 'full': tune every candidate (tune -> inner), pick_of, then the refit path; 'pinned': the refit path of
    the given candidate (forced F5, or a placebo's parent pick). Mirrors board._tune_index + _refit_one."""
    H, eng, run, cfg = T.H, T.eng, T.run, T.cfg
    rival = T.by_id[rid]
    L, fset, gset = B.pick_sets(T.by_id[rival.get("placebo_of") or rid])
    assert (L, fset, gset) == (0, "tune", "inner")
    t0 = time.time()
    fit = B.set_data(cfg, run, rival, L, fset, idx)
    sc = B.set_data(cfg, run, rival, L, gset, idx)
    cover = np.isfinite(sc.x[list(rival["stats"])].to_numpy(np.float64)).all(axis=1)
    scc = sc.subset(cover)
    trials, tpred = [], {}
    if mode == "full":
        assert not rival.get("placebo_of")
        for cand in MP.candidates(rival, run.links):
            rec = {"rival": rid, "candidate": cand["id"], "stat": cand["stat"], "family": cand["family"],
                   "link": cand["link"], "order": cand["order"], "lead": L, "fit_set": fset, "score_set": gset,
                   "rows_score": int(scc.y.size)}
            try:
                if not scc.y.size:
                    raise MP.NotCalibratable("no %s row is covered by every stat" % gset)
                model = B.fit_candidate(cand, fit, run, L)
            except MP.NotCalibratable as exc:
                rec.update(status="not_calibratable", reason=str(exc))
                trials.append(rec)
                continue
            pre, pred = B.predict_candidate(model, cand, scc, run, L, eng, H)
            met = H.inner_metrics(eng, scc.y, pred, run.legal)
            rec.update(status="ok", pick_mae=met["mae"], metrics=met, rows_fit=int(model.info.get("rows", 0)))
            trials.append(rec)
            tpred[cand["id"]] = pred
            log("  trial %s %s: inner MAE %r" % (rid, cand["id"], met["mae"]))
            del model
        best = B.pick_of(trials)
        if best is None:
            return {"status": "not_calibratable", "trials": trials}
        cand = {"id": best["candidate"], "stat": best["stat"], "family": best["family"], "link": best["link"]}
    else:
        cand = {k: pinned[k] for k in ("id", "stat", "family", "link")}
    # ---- refit path (board._refit_one, index rival, lead 0)
    gsc = sc
    gcov = np.isfinite(gsc.x[cand["stat"]].to_numpy(np.float64))
    gsc_c = gsc.subset(gcov)
    gmodel = B.fit_candidate(cand, fit, run, L)
    del fit
    gc.collect()
    rfit = B.set_data(cfg, run, rival, L, "refit", idx)
    model = B.fit_candidate(cand, rfit, run, L)
    refit_info = dict(model.info)
    del rfit
    gc.collect()
    g_pre, g_pred = B.predict_candidate(gmodel, cand, gsc_c, run, L, eng, H)
    gkeys = gsc_c.keys[list(C.KEYS)]
    sl = S.open_slim(cfg, run, L)
    gy, comp_name, comp = B._guard_labels_and_comparator(T.hctx, run, L, gset, gkeys, gsc_c, sl, cand["link"])
    if not np.array_equal(gy, gsc_c.y):
        raise SystemExit("internal: the guard labels differ from the slim labels")
    determinism = None
    if cand["id"] in tpred:                                # board._check_trial_reproduces (lead-0 own pick)
        determinism = bool(tpred[cand["id"]].tobytes() == np.asarray(g_pred, np.float64).tobytes())
    m = eng.metrics
    g_mae, c_mae = m.mae(gy, g_pred), m.mae(gy, comp)
    passed = bool(eng.decide.n2_eligible(g_mae, c_mae))
    # ---- test rows
    fb_name, saved = H.saved_test_keys(run, L)
    skeys = saved[["unit", "group", "time", "issue", "lead"]].reset_index(drop=True).copy()
    skeys["unit"] = skeys["unit"].astype(str)
    lp = T.token.doc["picks"][rid]
    cov = B.read_coverage(BOARD, lp, rid, L)              # the LOCKED coverage mask (sha-checked)
    if not (cov["unit"].astype(str).to_numpy() == skeys["unit"].to_numpy()).all() or \
            not np.array_equal(cov["time"].to_numpy(np.int64), skeys["time"].to_numpy(np.int64)):
        raise SystemExit("the coverage mask is not in the saved test order")
    mask = cov["covered"].to_numpy(bool)
    fb = saved[fb_name].to_numpy(np.float64)
    ts = B.set_data(cfg, run, rival, L, "test", idx, token=T.token)
    pos = H.to_saved_order(saved, ts.keys, "the saved test rows (%s)" % rid)
    ts = B.SetData(ts.keys.iloc[pos].reset_index(drop=True), None, {l: v[pos] for l, v in ts.normal.items()},
                   ts.x.iloc[pos].reset_index(drop=True))
    xs = ts.x[cand["stat"]].to_numpy(np.float64)
    coverage_equal = bool(np.array_equal(np.isfinite(xs), mask))
    if not coverage_equal:
        raise SystemExit("rival %s: the index's test coverage differs from the locked mask" % rid)
    tc = ts.subset(mask)
    t_pre_c, _ = B.predict_candidate(model, cand, tc, run, L, eng, H)
    t_pre = np.full(len(skeys), np.nan)
    t_pre[mask] = t_pre_c
    pc = B.join_index(ts.keys, idx, [C.COL_PRODUCT_CELL], "product cells of %s" % rid)
    t_raw = np.full(len(skeys), np.nan)
    t_raw[mask] = H.clip(eng, t_pre[mask], run.legal)
    guarded = np.where(mask, t_raw if passed else fb, np.nan)
    filled = np.where(mask, guarded, fb)
    pframe = skeys.copy()
    xsv = np.full(len(skeys), np.nan)
    xsv[mask] = tc.x[cand["stat"]].to_numpy(np.float64)
    pframe["x"] = xsv
    pframe["covered"] = mask
    pframe["pre"] = t_pre
    pframe["raw"] = t_raw
    pframe["guarded"] = guarded
    pframe["filled"] = filled
    pframe["guard_passed"] = passed
    pframe["product_cell"] = pc[C.COL_PRODUCT_CELL].astype(str).to_numpy()
    out = {"status": "ok", "candidate": cand, "picked_family": cand["family"], "picked_link": cand["link"],
           "guard": {"rows": int(gy.size), "rival_mae": g_mae, "comparator": comp_name, "comparator_mae": c_mae,
                     "passed": passed, "source": "the pick fitted on the %s rows, scored on the covered %s rows"
                                                 % (fset, gset)},
           "determinism_guard_fit_reproduces_tune_trial": determinism, "test_coverage_equals_locked_mask": coverage_equal,
           "covered_rows": int(mask.sum()), "test_rows": int(mask.size), "fallback": fb_name,
           "refit_map_info": {k: v for k, v in refit_info.items() if k != "xbar_rows"},
           "guard_map_info": {k: v for k, v in gmodel.info.items() if k != "xbar_rows"},
           "seconds": time.time() - t0}
    if trials:
        out["trials"] = trials
    if keep_trials:
        out["_tpred"] = tpred
        out["_scc_keys"] = scc.keys[["unit", "time", "issue"]].copy()
    out["_pframe"] = pframe
    log("procedure %s %s %s: guard %r vs %s %r -> %s (%.1f s)" % (rid, mode, cand["id"], g_mae, comp_name, c_mae,
                                                                  "passed" if passed else "failed", time.time() - t0))
    return out


# ===================================================================================================== contrast
def ours_frame(T):
    run = T.run
    headline, raw = run.ours(LEAD)
    cols = ["unit", "group", "time", "year", "lead", "issue", "y", "normal", "legal_min", "legal_max",
            "base__guess_normal"]
    for c in (headline, raw):
        cols.append(c)
    tp = run.test_preds_path(LEAD)
    saved = pq.read_table(str(tp), columns=list(dict.fromkeys(cols))).to_pandas()
    return saved, B._ours_frame(run, LEAD, saved)


def score_rival(T, saved, frame, pf, name):
    """board.score for one rival (guarded_vs_headline and raw_vs_raw rows) + raw_vs_headline (extra)."""
    H, eng, run = T.H, T.eng, T.run
    m = eng.metrics
    tol, floor, kind = run.tol, run.floor, run.kind
    j = H._join(saved[["unit", "time", "lead"]], pf, ["unit", "time", "lead"], name)
    cov = j["covered"].to_numpy(bool)
    f = frame.copy()
    f["arm__rival"] = j["guarded"].to_numpy(np.float64)
    f["arm__rival_raw"] = j["raw"].to_numpy(np.float64)
    f["pre__rival_raw"] = j["pre"].to_numpy(np.float64)
    f["arm__rival_filled"] = j["filled"].to_numpy(np.float64)
    fc = f.loc[cov].reset_index(drop=True)
    gcount = fc.groupby("group").size()
    dec_groups = sorted(gcount.index[gcount >= C.MIN_GROUP_TEST_ROWS].astype(str).tolist())
    fd = fc[fc["group"].astype(str).isin(dec_groups)].reset_index(drop=True)
    gt = m.score_table(fd, ("group",), tol, floor, kind)
    pt = m.score_table(fd, (), tol, floor, kind)
    nmae = H._pooled(pt, "base__guess_normal")["mae"]
    common = {"rows": int(len(fd)), "rows_covered": int(cov.sum()), "rows_total": int(cov.size),
              "groups": len(dec_groups), "normal_mae_same_rows": nmae}
    out = {}
    for cname, rcol, ocol in (("guarded_vs_headline", "arm__rival", "arm__ours"),
                              ("raw_vs_raw", "arm__rival_raw", "arm__ours_raw"),
                              ("raw_vs_headline", "arm__rival_raw", "arm__ours")):
        res = B._contrast(eng, H, run, gt, pt, rcol, ocol, "%s %s" % (name, cname))
        out[cname] = dict(common, **res)
    return out


def runaway(T, saved, pf, xcol_frame):
    """Largest guarded forecast, count > 1,000, and the yakutia 2021-08 row (lag1 variants)."""
    f = saved[["unit", "group", "time", "year", "lead", "issue", "y"]].copy()
    f["unit"] = f["unit"].astype(str)
    j = T.H._join(f[["unit", "time", "lead"]], pf, ["unit", "time", "lead"], "preds")
    f["guarded"] = j["guarded"].to_numpy(np.float64)
    f["raw"] = j["raw"].to_numpy(np.float64)
    f["x_new"] = j["x"].to_numpy(np.float64)
    xl = T.H._join(f[["unit", "time", "lead"]], xcol_frame[["unit", "time", "lead", "x_locked_index"]],
                   ["unit", "time", "lead"], "x table")
    f["x_locked"] = xl["x_locked_index"].to_numpy(np.float64)
    g = f["guarded"].to_numpy(np.float64)
    i = int(np.nanargmax(g))
    r = f.iloc[i]
    yk = f[(f["unit"] == YAK_UNIT) & (f["time"].map(month_of_time) == YAK_MONTH)]
    assert len(yk) == 1
    y1 = yk.iloc[0]
    big = f[g > THRESH].sort_values("guarded", ascending=False)
    return {
        "largest_guarded_forecast": {"value": float(r["guarded"]), "unit": r["unit"], "region": str(r["group"]),
                                     "month": month_of_time(r["time"]), "x_used": float(r["x_new"]),
                                     "x_locked": float(r["x_locked"]), "observed_y": float(r["y"])},
        "count_guarded_gt_1000": int((g > THRESH).sum()),
        "rows_gt_1000": [{"value": float(b["guarded"]), "unit": b["unit"], "month": month_of_time(b["time"]),
                          "x_used": float(b["x_new"]), "x_locked": float(b["x_locked"])} for _, b in big.iterrows()],
        "second_largest_guarded_forecast": float(np.sort(g[np.isfinite(g)])[-2]),
        "yakutia_row": {"unit": YAK_UNIT, "month": YAK_MONTH, "guarded": float(y1["guarded"]), "raw": float(y1["raw"]),
                        "x_used": float(y1["x_new"]), "x_locked": float(y1["x_locked"]), "observed_y": float(y1["y"]),
                        "locked_forecast_for_reference": 418377.52, "locked_x_for_reference": 1698.28},
    }


def x_change(T, saved, xt, rid, col):
    f = saved[["unit", "time", "lead", "issue"]].copy()
    xf = xt[rid][["unit", "time", "lead", "x_locked_index", col]]
    j = T.H._join(f[["unit", "time", "lead"]], xf, ["unit", "time", "lead"], "x table")
    a, b = j[col].to_numpy(np.float64), j["x_locked_index"].to_numpy(np.float64)
    ok = np.isfinite(a) & np.isfinite(b) & (b != 0)
    r = a[ok] / b[ok]
    return {"rows": int(ok.sum()), "rows_test": int(len(f)), "median_ratio": float(np.median(r)),
            "p99_ratio": float(np.percentile(r, 99)), "p01_ratio": float(np.percentile(r, 1)),
            "min_ratio": float(r.min()), "max_ratio": float(r.max()), "mean_ratio": float(r.mean()),
            "share_moved_gt_10pct": float(np.mean(np.abs(r - 1.0) > 0.10)),
            "count_moved_gt_10pct": int(np.sum(np.abs(r - 1.0) > 0.10)),
            "median_abs_change_ug_m3": float(np.median(np.abs(a[ok] - b[ok]))),
            "max_x_new": float(a[ok].max()), "max_x_locked": float(b[ok].max())}


def save_preds(T, pf, xt, rid, variant, xcol):
    p = OUT / ("preds_%s_%s.parquet" % (rid, variant))
    f = pf.copy()
    xf = xt[rid][["unit", "time", "lead", "x_locked_index"]]
    j = T.H._join(f[["unit", "time", "lead"]], xf, ["unit", "time", "lead"], "x table")
    f.insert(5, "x_locked", j["x_locked_index"].to_numpy(np.float64))
    f = f.rename(columns={"x": "x_new" if xcol != "x_locked_index" else "x_used"})
    f.to_parquet(str(p), index=False)
    return {"path": str(p), "sha256": sha256(p), "x_column_source": xcol}


def strip(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def contrast_keys(c):
    k = ("verdict", "tag", "d_mean", "d_se", "d_low", "d_high", "n_groups", "blocked_mean", "blocked_se", "rival_mae",
         "ours_mae_same_rows", "corr2", "calibration_ratio", "anomaly_r2", "hit", "ours_corr2", "timid_win", "rows",
         "rows_covered", "groups", "normal_mae_same_rows")
    return {x: c.get(x) for x in k}


# ===================================================================================================== main
def main():
    OUT.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)
    log("start %s" % SCRIPT)
    res = {"label": "POST HOC re-score (implementer A, TOOL PATH); owner ruling AM1 2026-10-27; locked verdicts "
                    "never change", "spec": str(OUT.parent / "SPEC.md"), "spec_sha256": sha256(OUT.parent / "SPEC.md"),
           "script": str(SCRIPT), "script_sha256": sha256(SCRIPT), "problem": "pm25", "lead": LEAD, "units": "ug/m3",
           "formula_locked": "DUSMASS25 + SSSMASS25 + BCSMASS + 1.4*OCSMASS + 1.375*SO4SMASS",
           "formula_corrected": "DUSMASS25 + SSSMASS25 + BCSMASS + 1.0*OCSMASS + 1.375*SO4SMASS",
           "formula_side_check_gmao": "DUSMASS25 + SSSMASS25 + BCSMASS + 1.0*OCSMASS + (132.14/96.06)*SO4SMASS",
           "so4_gmao_factor": SO4_GMAO, "inputs": {}}
    T = setup()
    res["environment"] = T.env

    # ------------------------------------------------------------------ gate 0a + corrected x
    xt = x_tables(T, res)
    if not all(g["pass"] for g in res["gate_0a"].values()):
        res["STOPPED"] = "gate 0a failed"
        dump(OUT / "result_A.json", res)
        raise SystemExit("STOP: gate 0a failed: %s" % res["gate_0a"])

    saved, frame = ours_frame(T)
    rid = "merra2_lag1"
    # ------------------------------------------------------------------ gate 0b: locked lag1 full procedure
    idx_locked = idx_with(T, rid, xt, "x_locked_index")
    rep = procedure(T, rid, idx_locked, "full", keep_trials=True)
    del idx_locked
    lp = BOARD / "lead_0" / "preds_merra2_lag1.parquet"
    lpf = pq.read_table(str(lp)).to_pandas()
    done = C.read_json(BOARD / "lead_0" / "done_merra2_lag1.json")
    pf = rep["_pframe"]
    assert np.array_equal(lpf["unit"].astype(str).to_numpy(), pf["unit"].to_numpy())
    assert np.array_equal(lpf["time"].to_numpy(), pf["time"].to_numpy())
    trials_csv = pd.read_csv(BOARD / "trials.csv", float_precision="round_trip")
    tcsv = trials_csv[trials_csv["rival"] == rid].set_index("candidate")
    trial_cmp = {}
    for t in rep["trials"]:
        tp = BOARD / "trials" / rid / (t["candidate"] + ".parquet")
        tf = pq.read_table(str(tp)).to_pandas()
        sk = rep["_scc_keys"].copy()
        sk["unit"] = sk["unit"].astype(str)
        sk["_p"] = rep["_tpred"][t["candidate"]]
        tf["unit"] = tf["unit"].astype(str)
        jj = tf[["unit", "time", "issue", "pred"]].merge(sk, on=["unit", "time", "issue"], how="left",
                                                          validate="one_to_one")
        trial_cmp[t["candidate"]] = {
            "pick_mae": t["pick_mae"], "board_mae": float(tcsv.loc[t["candidate"], "mae"]),
            "pick_mae_equal": t["pick_mae"] == float(tcsv.loc[t["candidate"], "mae"]),
            "preds_bitwise_equal_trial_file": bool(jj["_p"].notna().all() and jj["_p"].to_numpy(np.float64).tobytes()
                                                   == jj["pred"].to_numpy(np.float64).tobytes()),
            "trial_file_sha256": sha256(tp)}
    g0b = {"picked": rep["candidate"]["id"], "picked_family": rep["picked_family"], "picked_link": rep["picked_link"],
           "guard": rep["guard"], "locked_guard": LOCKED_GUARD,
           "done_file_guard": {k: done["guard"][k] for k in ("rival_mae", "comparator_mae", "rows", "passed",
                                                              "comparator")},
           "guard_equal_exact": (rep["guard"]["rival_mae"] == done["guard"]["rival_mae"]
                                 and rep["guard"]["comparator_mae"] == done["guard"]["comparator_mae"]
                                 and rep["guard"]["rows"] == done["guard"]["rows"]
                                 and rep["guard"]["passed"] == done["guard"]["passed"]
                                 and rep["guard"]["comparator"] == done["guard"]["comparator"]),
           "guarded_vs_preds_file": maxdiff(pf["guarded"], lpf["guarded"]),
           "raw_vs_preds_file": maxdiff(pf["raw"], lpf["raw"]),
           "pre_vs_preds_file": maxdiff(pf["pre"], lpf["pre"]),
           "filled_vs_preds_file": maxdiff(pf["filled"], lpf["filled"]),
           "x_vs_preds_file": maxdiff(pf["x"], lpf["x"]),
           "covered_equal": bool(np.array_equal(pf["covered"].to_numpy(), lpf["covered"].to_numpy())),
           "product_cell_equal": bool(np.array_equal(pf["product_cell"].to_numpy(),
                                                     lpf["product_cell"].astype(str).to_numpy())),
           "determinism_guard_fit_reproduces_tune_trial": rep["determinism_guard_fit_reproduces_tune_trial"],
           "trials_vs_board": trial_cmp,
           "all_trial_maes_equal": all(v["pick_mae_equal"] for v in trial_cmp.values()),
           "all_trial_preds_bitwise_equal": all(v["preds_bitwise_equal_trial_file"] for v in trial_cmp.values())}
    g0b["pass"] = bool(g0b["picked"] == "pm25__F5__log_c" and g0b["guard_equal_exact"]
                       and g0b["guarded_vs_preds_file"]["bitwise_equal"] and g0b["raw_vs_preds_file"]["bitwise_equal"]
                       and g0b["covered_equal"] and g0b["all_trial_maes_equal"])
    res["gate_0b"] = g0b
    res["preds_files"] = {"merra2_lag1_locked_repro": save_preds(T, pf, xt, rid, "locked_repro", "x_locked_index")}
    log("gate 0b: pass=%s guarded %s guard %s" % (g0b["pass"], g0b["guarded_vs_preds_file"], rep["guard"]))
    if not g0b["pass"]:
        res["STOPPED"] = "gate 0b failed"
        dump(OUT / "result_A.json", res)
        raise SystemExit("STOP: gate 0b failed")

    # ------------------------------------------------------------------ gate 0c: locked deciding contrast
    sc0 = score_rival(T, saved, frame, pf, "preds_merra2_lag1 (reproduced)")
    scl = score_rival(T, saved, frame, lpf, "preds_merra2_lag1.parquet (locked file)")
    bl = pd.read_csv(BOARD / "human_board_lead_0.csv", float_precision="round_trip")
    rt = pd.read_csv(RIVALS_TABLE, float_precision="round_trip")
    brow = bl[(bl["rival"] == rid) & (bl["contrast"] == "guarded_vs_headline")].iloc[0]
    rrow = rt[(rt["problem"] == "pm25") & (rt["lead"] == LEAD) & (rt["rival"] == rid)
              & (rt["contrast"] == "guarded_vs_headline")].iloc[0]
    g = sc0["guarded_vs_headline"]
    fields = ("d_mean", "d_se", "d_low", "d_high", "rival_mae", "ours_mae_same_rows", "corr2", "calibration_ratio",
              "blocked_mean", "blocked_se")
    g0c = {"reproduced": contrast_keys(g),
           "board_csv": {k: float(brow[k]) for k in fields}, "board_verdict": brow["verdict"],
           "board_rows": float(brow["rows"]), "board_groups": float(brow["groups"]),
           "exact_vs_board_csv": {k: g[k] == float(brow[k]) for k in fields},
           "max_abs_diff_vs_board_csv": max(abs(g[k] - float(brow[k])) for k in fields),
           "rivals_table": {k: float(rrow[k]) for k in ("d_mean", "d_low", "d_high", "rival_mae",
                                                        "ours_mae_same_rows")},
           "max_abs_diff_vs_rivals_table": max(abs(g[k] - float(rrow[k])) for k in ("d_mean", "d_low", "d_high",
                                                                                   "rival_mae", "ours_mae_same_rows")),
           "rivals_table_verdict": rrow["verdict"],
           "locked_preds_file_scored_identically": all(scl["guarded_vs_headline"][k] == g[k] for k in fields),
           "spec_values": {"d": 4.85562, "low": -4.146349, "high": 13.857588, "verdict": "CANNOT TELL",
                           "rival_mae": 8.444332, "ours": 3.588091, "rows": 91440, "groups": 127}}
    g0c["pass"] = bool(all(g0c["exact_vs_board_csv"].values()) and g["verdict"] == brow["verdict"] == "CANNOT TELL"
                       and g["rows"] == 91440 and g["groups"] == 127 and g0c["max_abs_diff_vs_rivals_table"] < 1e-12)
    res["gate_0c"] = g0c
    log("gate 0c: pass=%s d %r [%r, %r] %s" % (g0c["pass"], g["d_mean"], g["d_low"], g["d_high"], g["verdict"]))
    if not g0c["pass"]:
        res["STOPPED"] = "gate 0c failed"
        dump(OUT / "result_A.json", res)
        raise SystemExit("STOP: gate 0c failed")
    res["locked_lag1_runaway_check"] = runaway(T, saved, lpf.assign(unit=lpf["unit"].astype(str)), xt[rid])
    del rep, sc0, scl
    gc.collect()

    # ------------------------------------------------------------------ extra checks: locked same + placebo refit
    extra = {}
    for r2 in ("merra2_same", "merra2_lag1_placebo"):
        lp2 = BOARD / "lead_0" / ("preds_%s.parquet" % r2)
        lpf2 = pq.read_table(str(lp2)).to_pandas()
        d2 = C.read_json(BOARD / "lead_0" / ("done_%s.json" % r2))
        pk = T.token.doc["picks"][r2]
        ix2 = idx_with(T, r2, xt, "x_locked_index")
        rp2 = procedure(T, r2, ix2, "pinned", pinned={"id": pk["candidate"], "stat": pk["stat"],
                                                      "family": pk["family"], "link": pk["link"]})
        del ix2
        sc2 = score_rival(T, saved, frame, rp2["_pframe"], r2)
        brow2 = bl[(bl["rival"] == r2) & (bl["contrast"] == "guarded_vs_headline")].iloc[0]
        extra[r2] = {"locked_pick": pk["candidate"], "guard": rp2["guard"],
                     "done_guard": {k: d2["guard"][k] for k in ("rival_mae", "comparator_mae", "rows", "passed")},
                     "guard_equal_exact": all(rp2["guard"][k] == d2["guard"][k] for k in
                                              ("rival_mae", "comparator_mae", "rows", "passed")),
                     "guarded_vs_preds_file": maxdiff(rp2["_pframe"]["guarded"], lpf2["guarded"]),
                     "raw_vs_preds_file": maxdiff(rp2["_pframe"]["raw"], lpf2["raw"]),
                     "d_mean": sc2["guarded_vs_headline"]["d_mean"], "board_d_mean": float(brow2["d_mean"]),
                     "d_exact": sc2["guarded_vs_headline"]["d_mean"] == float(brow2["d_mean"]),
                     "verdict": sc2["guarded_vs_headline"]["verdict"], "board_verdict": brow2["verdict"],
                     "preds_file_sha256": sha256(lp2), "done_file_sha256": sha256(BOARD / "lead_0" /
                                                                                  ("done_%s.json" % r2))}
        log("extra %s: %s" % (r2, {k: v for k, v in extra[r2].items() if k in ("guard_equal_exact", "d_exact")}))
        del rp2, lpf2
        gc.collect()
    res["extra_reproduction_locked_same_and_placebo"] = extra

    # ------------------------------------------------------------------ 1-5: corrected input
    res["x_change_test_rows"] = {r_: x_change(T, saved, xt, r_, "x_new") for r_ in RIVALS}
    res["x_change_test_rows"]["merra2_lag1_gmao_side_check"] = x_change(T, saved, xt, "merra2_lag1", "x_gmao")
    new = {}
    idx_new = idx_with(T, rid, xt, "x_new")
    full = procedure(T, rid, idx_new, "full")
    f5 = procedure(T, rid, idx_new, "pinned", pinned={"id": "pm25__F5__log_c", "stat": "x__pm25", "family": "F5",
                                                       "link": "log_c"})
    del idx_new
    for tag, rr in (("full", full), ("forcedF5", f5)):
        sc_ = score_rival(T, saved, frame, rr["_pframe"], "%s %s" % (rid, tag))
        new["merra2_lag1_" + tag] = dict(strip(rr), contrasts={k: contrast_keys(v) for k, v in sc_.items()},
                                         runaway=runaway(T, saved, rr["_pframe"], xt[rid]),
                                         preds_file=save_preds(T, rr["_pframe"], xt, rid, tag, "x_new"))
    parent_pick = full["candidate"]
    del f5
    gc.collect()
    r2 = "merra2_same"
    ix = idx_with(T, r2, xt, "x_new")
    rs = procedure(T, r2, ix, "full")
    del ix
    sc_ = score_rival(T, saved, frame, rs["_pframe"], r2)
    new["merra2_same_full"] = dict(strip(rs), contrasts={k: contrast_keys(v) for k, v in sc_.items()},
                                   preds_file=save_preds(T, rs["_pframe"], xt, r2, "full", "x_new"))
    del rs
    gc.collect()
    r2 = "merra2_lag1_placebo"
    ix = idx_with(T, r2, xt, "x_new")
    rpb = procedure(T, r2, ix, "pinned", pinned=parent_pick)
    del ix
    sc_ = score_rival(T, saved, frame, rpb["_pframe"], r2)
    new["merra2_lag1_placebo_full"] = dict(strip(rpb), parent_pick=parent_pick["id"],
                                           contrasts={k: contrast_keys(v) for k, v in sc_.items()},
                                           preds_file=save_preds(T, rpb["_pframe"], xt, r2, "full", "x_new"))
    del rpb, full
    gc.collect()
    res["corrected"] = new

    # ------------------------------------------------------------------ side check: GMAO sulfate factor too
    side = {}
    idx_g = idx_with(T, rid, xt, "x_gmao")
    gf = procedure(T, rid, idx_g, "full")
    sc_ = score_rival(T, saved, frame, gf["_pframe"], "gmao full")
    side["merra2_lag1_full"] = {"picked": gf["candidate"]["id"], "guard": gf["guard"],
                                "contrast": contrast_keys(sc_["guarded_vs_headline"]),
                                "raw_vs_raw": contrast_keys(sc_["raw_vs_raw"]),
                                "runaway": runaway(T, saved, gf["_pframe"], xt[rid]),
                                "trials": [{k: t.get(k) for k in ("candidate", "status", "pick_mae")}
                                           for t in gf["trials"]],
                                "preds_file": save_preds(T, gf["_pframe"], xt, rid, "gmao_full", "x_gmao")}
    if gf["candidate"]["id"] != "pm25__F5__log_c":
        gp = procedure(T, rid, idx_g, "pinned", pinned={"id": "pm25__F5__log_c", "stat": "x__pm25", "family": "F5",
                                                         "link": "log_c"})
        sc_ = score_rival(T, saved, frame, gp["_pframe"], "gmao forced F5")
        side["merra2_lag1_forcedF5"] = {"guard": gp["guard"], "contrast": contrast_keys(sc_["guarded_vs_headline"]),
                                        "runaway": runaway(T, saved, gp["_pframe"], xt[rid]),
                                        "preds_file": save_preds(T, gp["_pframe"], xt, rid, "gmao_forcedF5", "x_gmao")}
    else:
        side["merra2_lag1_forcedF5"] = "same as full (the full procedure picks F5 log_c)"
    del idx_g, gf
    res["side_check_gmao_sulfate_factor"] = side

    # ------------------------------------------------------------------ input file hashes
    run = T.run
    inp = res["inputs"]
    inp["test_preds"] = {"path": str(run.test_preds_path(LEAD)), "sha256": sha256(run.test_preds_path(LEAD))}
    inp["run_files"] = T.env["run_file_sha256"]
    for r_ in RIVALS:
        for ext in ("parquet", "json"):
            p = INDEX / r_ / ("lead_0.%s" % ext)
            inp["index_%s_%s" % (r_, ext)] = {"path": str(p), "sha256": sha256(p)}
        for nm in ("preds_%s.parquet", "done_%s.json", "coverage_%s.parquet"):
            p = BOARD / "lead_0" / (nm % r_)
            inp["board_" + (nm % r_)] = {"path": str(p), "sha256": sha256(p)}
    for nm in ("human_board.json", "human_picks.json", "human_picks.json.lock.json", "human_board_lead_0.csv",
               "trials.csv", "test_labels_opened_human_lead_0.json"):
        inp["board_" + nm] = {"path": str(BOARD / nm), "sha256": sha256(BOARD / nm)}
    inp["rivals_table"] = {"path": str(RIVALS_TABLE), "sha256": sha256(RIVALS_TABLE)}
    sl = S.open_slim(T.cfg, run, LEAD)
    inp["slim_lead0_manifest_sha256"] = sl.manifest_sha
    inp["slim_lead0_files_sha256_verified_by_tool"] = sl.file_shas()
    ledger = LK.ledger_path(BOARD, run.fingerprint)
    inp["human_ledger"] = {"path": str(ledger), "sha256": sha256(ledger) if Path(ledger).is_file() else None}
    for nm in ("pm25.yaml", "_products.yaml", "_schema.yaml"):
        inp["registry_" + nm] = {"path": str(HUMAN / "registry" / nm), "sha256": sha256(HUMAN / "registry" / nm)}
    inp["config"] = {"path": str(CONFIG), "sha256": sha256(CONFIG)}
    pm = IX.product_manifest_path(T.cfg, T.products, "merra2_aer_monthly")
    inp["merra2_product_manifest"] = {"path": str(pm), "sha256": sha256(pm)}
    inp["x_tables"] = {r_: {"path": str(OUT / ("x_%s.parquet" % r_)), "sha256": sha256(OUT / ("x_%s.parquet" % r_))}
                       for r_ in RIVALS}
    res["script_sha256_at_end"] = sha256(SCRIPT)
    dump(OUT / "result_A.json", res)
    log("wrote %s" % (OUT / "result_A.json"))
    summary(res)


def summary(res):
    def c(x):
        return x["contrasts"]["guarded_vs_headline"]
    lines = ["", "PLAIN-WORDS SUMMARY (post hoc, implementer A)"]
    lines.append("gate 0a x rebuild: " + "; ".join("%s max abs diff %r (bitwise %s)" % (k, v["max_abs_diff"],
                                                                                   v["bitwise_equal"])
                                                  for k, v in res["gate_0a"].items()))
    g = res["gate_0b"]
    lines.append("gate 0b: pick %s, guard %r vs %r rows %d passed %s; guarded column max abs diff %r (bitwise %s)"
                 % (g["picked"], g["guard"]["rival_mae"], g["guard"]["comparator_mae"], g["guard"]["rows"],
                    g["guard"]["passed"], g["guarded_vs_preds_file"]["max_abs_diff"],
                    g["guarded_vs_preds_file"]["bitwise_equal"]))
    g = res["gate_0c"]["reproduced"]
    lines.append("gate 0c: d %r [%r, %r] %s, rival %r ours %r, %d rows %d groups; max diff vs board csv %r"
                 % (g["d_mean"], g["d_low"], g["d_high"], g["verdict"], g["rival_mae"], g["ours_mae_same_rows"],
                    g["rows"], g["groups"], res["gate_0c"]["max_abs_diff_vs_board_csv"]))
    for k, v in res["corrected"].items():
        cc = c(v)
        lines.append("%s: pick %s guard %r vs %r (%d rows) %s; test rival MAE %r ours %r; d %r [%r, %r] %s"
                     % (k, v["candidate"]["id"], v["guard"]["rival_mae"], v["guard"]["comparator_mae"],
                        v["guard"]["rows"], "passed" if v["guard"]["passed"] else "failed", cc["rival_mae"],
                        cc["ours_mae_same_rows"], cc["d_mean"], cc["d_low"], cc["d_high"], cc["verdict"]))
        if "runaway" in v:
            ra = v["runaway"]
            lines.append("   largest %r at %s %s (x %r); count > 1000: %d; yakutia 2021-08 %r from x %r"
                         % (ra["largest_guarded_forecast"]["value"], ra["largest_guarded_forecast"]["unit"],
                            ra["largest_guarded_forecast"]["month"], ra["largest_guarded_forecast"]["x_used"],
                            ra["count_guarded_gt_1000"], ra["yakutia_row"]["guarded"], ra["yakutia_row"]["x_used"]))
    for k, v in res["x_change_test_rows"].items():
        lines.append("x change %s: median ratio %r, p99 %r, share moved > 10%% %r" % (k, v["median_ratio"],
                                                                                    v["p99_ratio"],
                                                                                    v["share_moved_gt_10pct"]))
    log("\n".join(lines))


if __name__ == "__main__":
    main()
