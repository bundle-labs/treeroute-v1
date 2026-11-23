"""Rival models: load (kept) or rebuild (RF), check every saved test prediction bit for bit, then exact SHAP on the
registered sample (PROTOCOL.md sections 4.2, 5, 9, v3). One process per problem and lead, the boards' pins (8 threads).

  py -3.9 -I -B rival_shap.py --problem coral --lead 0 [--learners ridge lgbm lgbm_tweedie hgb_l1 rf]
        [--sample-root DIR] [--register FILE] [--rows K] [--out-root DIR]

Outputs out/<problem>/lead_<L>/rival_<learner>/: exactness.json, rows.parquet, background_keys.parquet, meta.json,
rows.parquet.done.json; RF trees in work/<problem>/lead_<L>/rf_trees/. A learner whose done record still matches
its inputs (the sample, the background file, the model files, the board's records and every helper module) and
its file hash is skipped.
Fail-fast gate S-ENV (v3): before any data is read, the installed library versions and the thread pins must equal
the board's board.json ('versions', 'threads'). Stop rules: S-ENV, S-EXACT (no SHAP when a saved prediction is not
reproduced bit for bit; NaN and +-inf in the same places), S-ADD, S-EVAL (explained AND background rows), S-ZERO,
S-SAMPLE, S-PATH.
Players: one per distinct column; a context column that is an exact copy of a tree column (the name rule
c__ctx:top5:<v> -> x__<v>, proven equal on every explained and background row) is the same player, in the walk
itself (a merged player's Shapley value is not the sum of two separate players'). Variable level: the same walk with
the variable map.
"""
import argparse
import gc
import json
import os
import sys
import time
import types

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapv1_common as C  # noqa: E402

PINS = 8
C.pin_threads(PINS)                            # the boards' pins (rivals/cli.py pin_threads: 8)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

sys.path.insert(1, "D:/treeroute/rivals_build")
from rivals import layout as LY  # noqa: E402

LY.import_engine(C.engine_live_root())
from rivals import harness as H  # noqa: E402
from rivals import models as M  # noqa: E402

import shapv1_rows as RW  # noqa: E402
import shapv1_treeshap as TS  # noqa: E402

KEY = ["unit", "time", "issue"]
ALL = ("ridge", "lgbm", "lgbm_tweedie", "hgb_l1", "rf")
MEMMAP_ABOVE = 1.5 * (1 << 30)
HELPERS = ("rival_shap.py", "shapv1_treeshap.py", "shapv1_rows.py", "shapv1_common.py")


def parse():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True, choices=sorted(C.PROBLEMS))
    ap.add_argument("--lead", type=int, required=True)
    ap.add_argument("--learners", nargs="*", default=None)
    ap.add_argument("--sample-root", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--rows", type=int, default=0, help="smoke: explain only the first K sample rows")
    ap.add_argument("--out-root", default=None, help="smoke: a folder under smoke/")
    return ap.parse_args()


class Ctx(object):
    pass


def env_gate(board, log):
    """S-ENV: the board's library versions and thread count, before any data is read."""
    have = C.versions()
    want = board.get("versions") or {}
    diff = {k: [v, have.get(k)] for k, v in want.items() if have.get(k) != v}
    pins = {v: os.environ.get(v) for v in C.PIN_VARS[:4]}
    bad_pins = {k: v for k, v in pins.items() if v != str(board.get("threads"))}
    if diff or bad_pins or int(board.get("threads", -1)) != PINS:
        raise SystemExit("STOP S-ENV: the environment is not the board's (versions %s; pins %s; board threads %s)"
                         % (diff, bad_pins, board.get("threads")))
    log("S-ENV: library versions and thread pins equal the board's (%d threads)" % PINS)


def load_context(a, log):
    P = C.PROBLEMS[a.problem]
    c = Ctx()
    c.P = P
    c.lead = a.lead
    c.board = C.read_json(os.path.join(P["board"], "board.json"))
    env_gate(c.board, log)
    c.picks = C.read_json(os.path.join(P["board"], "picks.json"))["picks"]
    sroot = a.sample_root or C.sample_dir(a.problem)
    c.ident = C.sample_identity(a.problem, sroot, a.register, lead=a.lead)
    c.run = H.Run(P["run"])
    c.ex = H.ExportLead(H._lead_export_dir(c.board, a.lead), a.lead, c.run)
    c.ldir = os.path.join(P["board"], "lead_%d" % a.lead)
    t0 = time.time()
    c.K, _, c.X, c.nm = c.ex.read_set("test")
    log("test set: %d rows x %d features (%s), read and hash-checked in %.1f s"
        % (len(c.K), c.X.shape[1], c.ex.dir, time.time() - t0))
    S = pq.read_table(os.path.join(sroot, "sample.parquet")).to_pandas()
    B = pq.read_table(os.path.join(sroot, "background_lead_%d.parquet" % a.lead)).to_pandas()
    if a.rows:
        S = S.iloc[:a.rows].copy()
        B = B[B["row"].isin(S["row"])].copy()
    c.S, c.B = S.reset_index(drop=True), B.reset_index(drop=True)
    # explained rows: positions in the test set
    pos = pd.DataFrame({"unit": c.K["unit"].to_numpy(), "time": c.K["time"].to_numpy(np.int64),
                        "p": np.arange(len(c.K))})
    j = c.S[["unit", "time"]].merge(pos, on=["unit", "time"], how="left")
    if j["p"].isna().any():
        raise SystemExit("REFUSED: %d sample rows are not test rows of the lead-%d export" % (int(j["p"].isna().sum()),
                                                                                              a.lead))
    c.epos = j["p"].to_numpy(np.int64)
    # background rows: the refit rows of the sample's background keys, read group by group (hash-checked files)
    c.Kb, c.Xb, c.nmb = read_refit_rows(c.ex, c.B[["unit", "time"]].drop_duplicates())
    bpos = pd.DataFrame({"unit": c.Kb["unit"].to_numpy(), "time": c.Kb["time"].to_numpy(np.int64),
                         "q": np.arange(len(c.Kb))})
    jb = c.B.merge(bpos, on=["unit", "time"], how="left")
    if jb["q"].isna().any():
        raise SystemExit("STOP S-BG: %d background keys are not refit rows of the lead-%d export"
                         % (int(jb["q"].isna().sum()), a.lead))
    c.bg_lists = [jb.loc[jb["row"] == r, "q"].to_numpy(np.int64) for r in c.S["row"].tolist()]
    log("sample: %d explained rows, %d distinct background rows (per row: min %d, median %.0f, max %d)"
        % (len(c.S), len(c.Kb), min(map(len, c.bg_lists)), np.median(list(map(len, c.bg_lists))),
           max(map(len, c.bg_lists))))
    c.players, c.poc = players_of(c, log)
    c.vmap, c.variables = C.variable_map(c.players)
    vidx = {v: i for i, v in enumerate(c.variables)}
    c.pocv = np.asarray([vidx[c.vmap[c.players[p]]] for p in c.poc], np.int64)
    return c


def read_refit_rows(ex, keys):
    """Refit rows (flag r_refit) with the given (unit, time) keys: (keys, X float32, {link: normal})."""
    want = set(zip(keys["unit"].astype(str), keys["time"].astype(np.int64)))
    Ks, Xs, Ns = [], [], {l: [] for l in ex.run.links}
    cols = list(H.KEYS) + list(H.FLAGS) + ["y"] + ex.features + [H.NFIT_PREFIX + l for l in ex.run.links]
    for stem in ex.groups:
        t = ex.read_table(H.TRAIN_DIR, stem, cols)
        flag = t["r_refit"].to_numpy(bool)
        hit = np.array([(u, int(tt)) in want for u, tt in zip(t["unit"].astype(str), t["time"])], bool) & flag
        if not hit.any():
            continue
        Ks.append(t.loc[hit, list(H.KEYS)].reset_index(drop=True))
        Xs.append(t.loc[hit, ex.features].to_numpy(np.float32))
        for l in ex.run.links:
            Ns[l].append(t.loc[hit, H.NFIT_PREFIX + l].to_numpy(np.float64))
    return (pd.concat(Ks, ignore_index=True), np.concatenate(Xs, 0), {l: np.concatenate(v) for l, v in Ns.items()})


def players_of(c, log):
    """(players, poc): one player per distinct column of the tree matrix [features | normal]; an exact duplicate
    context column (name rule, then bitwise equality on every explained and background row) shares its tree
    column's player."""
    feats = [str(f) for f in c.ex.features]
    Xe, Xb = c.X[c.epos], c.Xb
    players, poc, merged = [], [], {}
    for j, f in enumerate(feats):
        tgt = C.duplicate_target(f, feats)
        if tgt is not None:
            k = feats.index(tgt)
            same = (np.array_equal(Xe[:, j].view(np.uint32), Xe[:, k].view(np.uint32))
                    and np.array_equal(Xb[:, j].view(np.uint32), Xb[:, k].view(np.uint32)))
            if same:
                merged[f] = tgt
                continue
            log("%s is not an exact copy of %s on the sample's rows: kept as its own player" % (f, tgt))
        players.append(f)
    pid = {p: i for i, p in enumerate(players)}
    for f in feats:
        poc.append(pid[merged.get(f, f)])
    players.append("normal")
    poc.append(len(players) - 1)
    c.merged = merged
    if merged:
        log("exact duplicate columns merged into one player: %s" % merged)
    return players, np.asarray(poc, np.int64)


def saved_pre(c, learner):
    p = pq.read_table(os.path.join(c.ldir, "preds_%s.parquet" % learner)).to_pandas()
    j = c.K[KEY].merge(p[KEY + ["pre__rival_" + learner]], on=KEY, how="left", validate="one_to_one")
    return j["pre__rival_" + learner].to_numpy(np.float64)


def bit_check(pre, ref):
    """Bit identity on every row: NaN in the same places, +-inf in the same places with the same sign, every
    finite value equal."""
    pre, ref = np.asarray(pre, np.float64), np.asarray(ref, np.float64)
    same_nan = bool(np.array_equal(np.isnan(pre), np.isnan(ref)))
    inf_ok = bool(np.array_equal(np.isinf(ref), np.isinf(pre)) and np.array_equal(pre[np.isinf(ref)],
                                                                                    ref[np.isinf(ref)]))
    fin = np.isfinite(ref) & np.isfinite(pre)
    d = np.abs(pre[fin] - ref[fin])
    return {"rows": int(ref.size), "rows_finite": int(fin.sum()), "same_nan": same_nan, "inf_equal": inf_ok,
            "rows_inf": int(np.isinf(ref).sum()), "bit_equal_rows": int((pre[fin] == ref[fin]).sum()),
            "max_abs_diff": float(d.max()) if d.size else 0.0,
            "pass": bool(same_nan and inf_ok and np.array_equal(pre[fin], ref[fin])
                         and np.array_equal(np.isfinite(ref), np.isfinite(pre)))}


def score_data(c, X, nm, name):
    return M.ScoreData(name=name, X=X, normal=nm)


def tree_shap_rows(c, trees, Xe, Xb, scale=1.0):
    """Interventional TreeSHAP of a sum of trees (times scale) on the sample with its backgrounds, at both levels."""
    px, pb, pw = TS.pairs_for(c.bg_lists)
    phi = np.zeros((Xe.shape[0], len(c.players)))
    phiv = np.zeros((Xe.shape[0], len(c.variables)))
    for T in trees:
        TS.itreeshap(T, Xe, Xb, px, pb, pw, c.poc, len(c.players), phi)
        TS.itreeshap(T, Xe, Xb, px, pb, pw, c.pocv, len(c.variables), phiv)
    return phi * scale, phiv * scale


def masks(c, Xe, Xb, z0e, z0b):
    """S-ZERO masks at both levels: the player's columns (and, for 'normal', the offset) equal on every background
    row."""
    px, pb, pw = TS.pairs_for(c.bg_lists)
    const = RW.constant_mask(Xe, Xb, px, pb, c.poc, len(c.players))
    constv = RW.constant_mask(Xe, Xb, px, pb, c.pocv, len(c.variables))
    off_const = np.ones(Xe.shape[0], bool)
    neq = np.asarray(z0e)[px] != np.asarray(z0b)[pb]
    off_const[np.unique(px[neq])] = False
    const[:, c.players.index("normal")] &= off_const
    constv[:, c.variables.index("normal")] &= off_const
    return const, constv


def finish(c, a, learner, params, phi, phiv, raw_e, raw_b, z0e, z0b, raw_model_e, raw_model_b, exact, extra, log,
           out, const, constv):
    """Offset term on 'normal' (per-pair differences), base, eta, pre; then the shared writer."""
    px, pb, pw = TS.pairs_for(c.bg_lists)
    n = phi.shape[0]
    off = np.bincount(px, weights=(np.asarray(z0e)[px] - np.asarray(z0b)[pb]) * pw, minlength=n)
    phi[:, c.players.index("normal")] += off
    phiv[:, c.variables.index("normal")] += off
    base = np.bincount(px, weights=(np.asarray(z0b)[pb] + np.asarray(raw_b)[pb]) * pw, minlength=n)
    eta = z0e + raw_e
    eta_model = z0e + raw_model_e
    pre = M._to_y(learner, params, z0e, raw_model_e)
    meta = {"model": "rival_%s" % learner, "problem": a.problem, "lead": a.lead,
            "link": "log_mu" if learner == "lgbm_tweedie" else params.get("link"),
            "c": params.get("c"), "ub": params.get("ub"), "background": "B2 (PROTOCOL.md 5)",
            "exactness": exact, "guard": extra.get("guard"), "value_function": "interventional, per-row background",
            "duplicates_merged": c.merged, "variable_map": c.vmap, "sample_sha256": c.ident["sample_sha256"]}
    meta.update({k: v for k, v in extra.items() if k != "guard"})
    bg_ours = None if raw_model_b is None else np.asarray(raw_b)
    rec = RW.write(out, c.S, c.players, phi, c.variables, phiv, base, eta, eta_model, pre, None, meta, log, c.B,
                   const=const, constv=constv, eta_bg=bg_ours, eta_bg_model=raw_model_b)
    return rec


def run_tree_model(c, a, learner, log, out):
    pick = c.picks[learner]
    params = H.trial_params(c.board, H._pick_trial(learner, pick), a.lead)
    pinned = int(H._pinned(learner, pick))
    done = C.read_json(os.path.join(c.ldir, "done_%s.json" % learner))
    s = score_data(c, c.X, c.nm, "test")
    cn, z0, _ = M._target_and_offset(learner, params, s, None)
    Xs = M._tree_matrix(c.X, None, cn)
    t0 = time.time()
    if learner in ("lgbm", "lgbm_tweedie"):
        import lightgbm as lgb
        bst = lgb.Booster(model_file=os.path.join(c.ldir, "model_%s.txt" % learner))
        raw = bst.predict(Xs, num_iteration=pinned, raw_score=True)
        trees = [TS.from_lgbm(t) for t in bst.dump_model(num_iteration=pinned)["tree_info"]]
        base_const = 0.0
        model_raw = lambda Z: bst.predict(Z, num_iteration=pinned, raw_score=True)  # noqa: E731
    else:
        import pickle
        with open(os.path.join(c.ldir, "model_%s.pkl" % learner), "rb") as fh:
            mdl = pickle.load(fh)
        raw = mdl.predict(Xs)
        trees = [TS.from_hgb(pr[0].nodes) for pr in mdl._predictors]
        base_const = float(np.ravel(mdl._baseline_prediction)[0])
        model_raw = mdl.predict
    pre_all = M._to_y(learner, params, z0, raw)
    exact = bit_check(np.asarray(pre_all, np.float64), saved_pre(c, learner))
    exact.update({"model_file": "model_%s" % learner, "pinned": pinned, "trees": len(trees),
                  "seconds": round(time.time() - t0, 1)})
    log("%s: %d trees; saved predictions reproduced on %d of %d test rows (max |diff| %.3g): %s"
        % (learner, len(trees), exact["bit_equal_rows"], exact["rows_finite"], exact["max_abs_diff"],
           "PASS" if exact["pass"] else "FAIL"))
    C.write_json(os.path.join(out, "exactness.json"), exact)
    if not exact["pass"]:
        log("STOP S-EXACT: %s does not reproduce its saved predictions; no SHAP value" % learner)
        return None
    se = score_data(c, c.X[c.epos], {l: v[c.epos] for l, v in c.nm.items()}, "explained")
    sb = score_data(c, c.Xb, c.nmb, "background")
    cne, z0e, _ = M._target_and_offset(learner, params, se, None)
    cnb, z0b, _ = M._target_and_offset(learner, params, sb, None)
    Xe32 = M._tree_matrix(se.X, None, cne)
    Xb32 = M._tree_matrix(sb.X, None, cnb)
    Xe, Xb = Xe32.astype(np.float64), Xb32.astype(np.float64)
    raw_e = base_const + sum(TS.predict(T, Xe) for T in trees)
    raw_b = base_const + sum(TS.predict(T, Xb) for T in trees)
    t1 = time.time()
    phi, phiv = tree_shap_rows(c, trees, Xe, Xb)
    log("%s: interventional TreeSHAP over %d trees on %d rows (2 levels) in %.1f s" % (
        learner, len(trees), Xe.shape[0], time.time() - t1))
    rme = np.asarray(model_raw(Xe32), np.float64)
    rmb = np.asarray(model_raw(Xb32), np.float64)
    const, constv = masks(c, Xe, Xb, z0e, z0b)
    return finish(c, a, learner, params, phi, phiv, raw_e, raw_b, z0e, z0b, rme, rmb, exact,
                  {"guard": done.get("guard"), "shap_seconds": round(time.time() - t1, 1)}, log, out, const, constv)


def ridge_design(c, mj, X, cn):
    names = mj["names"]
    raw_names = list(c.ex.features) + ["__normal__"]
    values = [n for n in names if not n.startswith("missing__")]
    flags = [n for n in names if n.startswith("missing__")]
    mu = np.asarray(mj["mean"], np.float64)
    imp = np.zeros(len(raw_names))
    keep = np.array([raw_names.index(n) for n in values], np.int64)
    imp[keep] = mu[:len(values)]
    d = types.SimpleNamespace(p_raw=len(raw_names), mean_impute=imp, keep_value=keep,
                              flag_cols=np.array([raw_names.index(n[len("missing__"):]) for n in flags], np.int64))
    scn = np.asarray(cn, np.float64)
    out = np.empty((X.shape[0], len(names)))
    for a0 in range(0, X.shape[0], M.RIDGE_BLOCK_ROWS):
        b0 = min(X.shape[0], a0 + M.RIDGE_BLOCK_ROWS)
        out[a0:b0] = M.RidgeDesign.block(d, np.asarray(X[a0:b0]), scn[a0:b0]) - mu[None, :]
    return out, names


def run_ridge(c, a, log, out):
    learner = "ridge"
    pick = c.picks[learner]
    params = H.trial_params(c.board, H._pick_trial(learner, pick), a.lead)
    pinned = H._pinned(learner, pick)
    done = C.read_json(os.path.join(c.ldir, "done_ridge.json"))
    mj = C.read_json(os.path.join(c.ldir, "model_ridge.json"))
    coef = np.asarray(mj["coef"][H.ck_label(pinned)], np.float64)
    tbar = float(mj["intercept"])
    s = score_data(c, c.X, c.nm, "test")
    cn, z0, _ = M._target_and_offset(learner, params, s, None)
    Z, names = ridge_design(c, mj, c.X, cn)
    outv = np.empty(Z.shape[0])
    for a0 in range(0, Z.shape[0], M.RIDGE_BLOCK_ROWS):
        b0 = min(Z.shape[0], a0 + M.RIDGE_BLOCK_ROWS)
        outv[a0:b0] = tbar + Z[a0:b0] @ coef
    exact = bit_check(np.asarray(M._to_y(learner, params, z0, outv), np.float64), saved_pre(c, learner))
    exact.update({"model_file": "model_ridge.json", "design_columns": len(names), "dropped": mj.get("dropped")})
    log("ridge: %d design columns; saved predictions reproduced on %d of %d test rows (max |diff| %.3g): %s"
        % (len(names), exact["bit_equal_rows"], exact["rows_finite"], exact["max_abs_diff"],
           "PASS" if exact["pass"] else "FAIL"))
    C.write_json(os.path.join(out, "exactness.json"), exact)
    if not exact["pass"]:
        log("STOP S-EXACT: ridge does not reproduce its saved predictions; no SHAP value")
        return None
    se = score_data(c, c.X[c.epos], {l: v[c.epos] for l, v in c.nm.items()}, "explained")
    sb = score_data(c, c.Xb, c.nmb, "background")
    cne, z0e, _ = M._target_and_offset(learner, params, se, None)
    cnb, z0b, _ = M._target_and_offset(learner, params, sb, None)
    Ze, _ = ridge_design(c, mj, se.X, cne)
    Zb, _ = ridge_design(c, mj, sb.X, cnb)
    raw_e = tbar + Ze @ coef
    raw_b = tbar + Zb @ coef
    feats = [str(f) for f in c.ex.features]
    pcol = []                                          # design column -> player (a missing flag -> its column)
    for nme in names:
        bse = nme[len("missing__"):] if nme.startswith("missing__") else nme
        pcol.append(len(c.players) - 1 if bse == "__normal__" else int(c.poc[feats.index(bse)]))
    pcol = np.asarray(pcol, np.int64)
    vcol = np.asarray([c.variables.index(c.vmap[c.players[p]]) for p in pcol], np.int64)
    px, pb, pw = TS.pairs_for(c.bg_lists)
    phi = np.zeros((Ze.shape[0], len(c.players)))
    phiv = np.zeros((Ze.shape[0], len(c.variables)))
    for i, lst in enumerate(c.bg_lists):
        contrib = coef * (Ze[i][None, :] - Zb[lst]).mean(0)       # per-pair differences first: equal -> exactly 0
        np.add.at(phi[i], pcol, contrib)
        np.add.at(phiv[i], vcol, contrib)
    # S-ZERO masks on the design columns (a player is constant when all its design columns are)
    const = np.ones((Ze.shape[0], len(c.players)), bool)
    constv = np.ones((Ze.shape[0], len(c.variables)), bool)
    for i, lst in enumerate(c.bg_lists):
        diff_cols = np.flatnonzero((Zb[lst] != Ze[i][None, :]).any(0))
        const[i, np.unique(pcol[diff_cols])] = False
        constv[i, np.unique(vcol[diff_cols])] = False
        if (np.asarray(z0b)[lst] != z0e[i]).any():
            const[i, len(c.players) - 1] = False
            constv[i, c.variables.index("normal")] = False
    return finish(c, a, learner, params, phi, phiv, raw_e, raw_b, z0e, z0b, raw_e, None, exact,
                  {"guard": done.get("guard"), "method": "exact linear SHAP; a missing flag folds into its column"},
                  log, out, const, constv)


class _FileStore(M.RFStore):
    def __init__(self, path):
        self.path = path

    def load(self):
        return open(self.path, "rb").read() if os.path.isfile(self.path) else None

    def save(self, data):
        C.assert_writable(self.path)
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, self.path)


def run_rf(c, a, log, out):
    learner = "rf"
    pick = c.picks[learner]
    params = H.trial_params(c.board, H._pick_trial(learner, pick), a.lead)
    done = C.read_json(os.path.join(c.ldir, "done_rf.json"))
    work = C.makedirs(os.path.join(C.ROOT, "work", a.problem, "lead_%d" % a.lead, "rf_trees")
                      if not a.out_root else os.path.join(a.out_root, "work_rf_%s_%d" % (a.problem, a.lead)))
    n = c.ex.count("refit")
    p = len(c.ex.features)
    mm_path = None
    t0 = time.time()
    if n * p * 4 > MEMMAP_ABOVE:
        mm_path = C.assert_writable(os.path.join(work, "refit_rows.f32"))
        Xf = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n, p))
        got = c.ex.read_set("refit", into=Xf)
        Kf, yf, nmf = got[0], got[1], got[3]
        del got                                       # no second reference to the memmap (Windows delete)
        Xf.flush()
    else:
        Kf, yf, Xf, nmf = c.ex.read_set("refit")
    log("rf: refit set %d rows x %d features read in %.1f s (%s)" % (n, p, time.time() - t0,
                                                                      "memmap" if mm_path else "RAM"))
    fit = M.FitData(name="lead_%d_refit" % a.lead, X=Xf, columns=tuple(c.ex.features), y=yf, normal=nmf)
    tst = M.ScoreData(name="test", X=c.X, normal=c.nm)
    store = _FileStore(os.path.join(work, "rf_checkpoint.npz"))
    start = 0
    raw = store.load()
    if raw:
        import io
        start = int(np.load(io.BytesIO(raw), allow_pickle=False)["trees_done"])
        have = all(os.path.isfile(os.path.join(work, "tree_%03d.npz" % t)) for t in range(start))
        if not have:
            os.remove(store.path)
            start = 0
    counter = {"t": start}
    orig = M._rf_tree
    se = score_data(c, c.X[c.epos], {l: v[c.epos] for l, v in c.nm.items()}, "explained")
    sb = score_data(c, c.Xb, c.nmb, "background")
    cne, z0e, _ = M._target_and_offset(learner, params, se, None)
    cnb, z0b, _ = M._target_and_offset(learner, params, sb, None)
    Xe32 = M._tree_matrix(se.X, None, cne)
    Xb32 = M._tree_matrix(sb.X, None, cnb)

    def keep_tree(sample, target, prm, seed):
        tree = orig(sample, target, prm, seed)
        tr = tree.estimators_[0].tree_
        # the tree's arrays, and oneDAL's own prediction of the explained and background rows (the model's raw, for
        # the evaluator check; summed in tree order below as rf_forest sums its score sets)
        C.write_npz(os.path.join(work, "tree_%03d.npz" % counter["t"]),
                    left=tr.children_left.astype(np.int32), right=tr.children_right.astype(np.int32),
                    feat=tr.feature.astype(np.int32), thr=tr.threshold.astype(np.float64),
                    val=tr.value.reshape(tr.node_count, -1)[:, 0].astype(np.float64), seed=np.int64(seed),
                    pred_e=np.asarray(tree.predict(Xe32), np.float64),
                    pred_b=np.asarray(tree.predict(Xb32), np.float64))
        counter["t"] += 1
        return tree
    M._rf_tree = keep_tree
    try:
        pred, model, info = M._fit_rf("rf", params, fit, [tst], (M.RF_TREES,), rf_store=store,
                                      rf_key="shap_v1|%s|%d" % (a.problem, a.lead))
    finally:
        M._rf_tree = orig
    exact = bit_check(np.asarray(pred["test"][M.RF_TREES], np.float64), saved_pre(c, learner))
    exact.update({"samples_sha256": info["samples_sha256"],
                  "samples_sha256_board": done["fit_info"]["samples_sha256"],
                  "samples_equal": info["samples_sha256"] == done["fit_info"]["samples_sha256"],
                  "resumed_from_tree": info.get("resumed_from_tree"), "trees": info["trees"],
                  "rebuild_seconds": round(time.time() - t0, 1)})
    exact["pass"] = bool(exact["pass"] and exact["samples_equal"])
    log("rf: rebuilt %d trees in %.1f s; draws equal to the board's: %s; saved predictions reproduced on %d of %d "
        "test rows (max |diff| %.3g): %s" % (info["trees"], time.time() - t0, exact["samples_equal"],
                                             exact["bit_equal_rows"], exact["rows_finite"], exact["max_abs_diff"],
                                             "PASS" if exact["pass"] else "FAIL"))
    fit = None
    Xf = None
    gc.collect()
    if mm_path:
        os.remove(mm_path)                             # every reference dropped and collected first (Windows)
    C.write_json(os.path.join(out, "exactness.json"), exact)
    if not exact["pass"]:
        log("STOP S-EXACT: rf does not reproduce its saved predictions; no SHAP value")
        return None
    Xe, Xb = Xe32.astype(np.float64), Xb32.astype(np.float64)
    px, pb, pw = TS.pairs_for(c.bg_lists)
    phi = np.zeros((Xe.shape[0], len(c.players)))
    phiv = np.zeros((Xe.shape[0], len(c.variables)))
    acc_e, acc_b = np.zeros(Xe.shape[0]), np.zeros(Xb.shape[0])
    acc_me, acc_mb = np.zeros(Xe.shape[0]), np.zeros(Xb.shape[0])
    t1 = time.time()
    for t in range(M.RF_TREES):
        with np.load(os.path.join(work, "tree_%03d.npz" % t)) as zz:
            z = {k: zz[k] for k in zz.files}
        if "pred_b" not in z:
            raise SystemExit("REFUSED: %s predates v3 (no background predictions); delete the rf_trees folder and "
                             "re-run" % ("tree_%03d.npz" % t))
        T = TS.from_arrays(z["left"], z["right"], z["feat"], z["thr"], z["val"], leaf_float32=True)
        acc_e += TS.predict(T, Xe)
        acc_b += TS.predict(T, Xb)
        acc_me += z["pred_e"]
        acc_mb += z["pred_b"]
        TS.itreeshap(T, Xe, Xb, px, pb, pw, c.poc, len(c.players), phi)
        TS.itreeshap(T, Xe, Xb, px, pb, pw, c.pocv, len(c.variables), phiv)
        if (t + 1) % 50 == 0:
            log("rf: SHAP tree %d of %d (%.1f s)" % (t + 1, M.RF_TREES, time.time() - t1))
    phi /= float(M.RF_TREES)
    phiv /= float(M.RF_TREES)
    raw_e, raw_b = acc_e / float(M.RF_TREES), acc_b / float(M.RF_TREES)
    rme, rmb = acc_me / float(M.RF_TREES), acc_mb / float(M.RF_TREES)    # oneDAL's own raw
    const, constv = masks(c, Xe, Xb, z0e, z0b)
    return finish(c, a, learner, params, phi, phiv, raw_e, raw_b, z0e, z0b, rme, rmb, exact,
                  {"guard": done.get("guard"), "shap_seconds": round(time.time() - t1, 1)}, log, out, const, constv)


def model_files(c, learner):
    """The files whose hashes enter the resume identity of a learner."""
    names = ["done_%s.json" % learner, "preds_%s.parquet" % learner]
    names += {"ridge": ["model_ridge.json"], "lgbm": ["model_lgbm.txt"], "lgbm_tweedie": ["model_lgbm_tweedie.txt"],
              "hgb_l1": ["model_hgb_l1.pkl"], "rf": []}[learner]
    return {n: C.sha256_file(os.path.join(c.ldir, n)) for n in names if os.path.isfile(os.path.join(c.ldir, n))}


def main():
    a = parse()
    log = C.Log("rival_shap_%s_lead%d" % (a.problem, a.lead))
    log("rival SHAP %s lead %d; versions %s" % (a.problem, a.lead, C.versions()))
    c = load_context(a, log)
    learners = [l for l in (a.learners or ALL) if l in c.picks]
    base_out = a.out_root or C.out_dir(a.problem, a.lead)
    summary = {}
    em = os.path.join(c.ex.dir, "export_manifest.json")
    for learner in learners:
        out = C.makedirs(os.path.join(base_out, "rival_%s" % learner))
        inputs = {"problem": a.problem, "lead": a.lead, "learner": learner, "rows": a.rows,
                  "sample": c.ident["sample_sha256"], "background_file": c.ident["background_sha256"],
                  "model_files": model_files(c, learner), "board": C.sha256_file(os.path.join(c.P["board"],
                                                                                              "board.json")),
                  "export_manifest": C.sha256_file(em) if os.path.isfile(em) else None,
                  "scripts": {f: C.sha256_file(os.path.join(HERE, f)) for f in HELPERS}}
        if C.piece_done(os.path.join(out, "rows.parquet"), inputs):
            log("%s: finished piece found with matching hashes: skipped" % learner)
            summary[learner] = "skipped (done)"
            continue
        t0 = time.time()
        try:
            if learner == "ridge":
                rec = run_ridge(c, a, log, out)
            elif learner == "rf":
                rec = run_rf(c, a, log, out)
            else:
                rec = run_tree_model(c, a, learner, log, out)
        except SystemExit as exc:                    # a stop rule of the writer (exit 3): recorded, next learner
            if exc.code != 3:
                raise
            rec = None
        if rec is not None:
            C.mark_done(os.path.join(out, "rows.parquet"), inputs, {"seconds": round(time.time() - t0, 1),
                                                                    "sample_sha256": c.ident["sample_sha256"],
                                                                    "background_keys_sha256":
                                                                        rec["background_keys_sha256"]})
        summary[learner] = "done" if rec is not None else "stopped (a stop rule)"
    log("summary: %s" % summary)
    if any(v.startswith("stopped") for v in summary.values()):
        sys.exit(3)


if __name__ == "__main__":
    main()
