"""Label-free guidance of the tool choice -- DEFO, STAGE A (test labels are NEVER read here).

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt (sha256 c51fc39a..., checked below). Sections cited as P<n>.
Read-only on the run, the engine and D:/treeroute/analysis/adv_validation. Writes only under
D:/treeroute/analysis/guidance/defo.

Builds every method's TEST predictions (M1-M6, M6s, the M5 and M6/M6s placebos, ungated and gated) and the surface
diagnostics, writes method_preds_defo.parquet + stageA_defo.json and their SHA-256 in stageA.sha256.txt (P3 G4).
test_preds.parquet is read with the key columns and the 'arm__' columns only, never 'y'.
"""
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import scipy
import scipy.sparse as sp
import sklearn
from scipy.optimize import linprog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore", category=FutureWarning)

PROTOCOL = Path("D:/treeroute/analysis/guidance/PROTOCOL.txt")
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"
RUN = Path("D:/treeroute/runs/defo/headline/20261017_d71c61f4")
ADV = Path("D:/treeroute/analysis/adv_validation/defo")
OUT = Path("D:/treeroute/analysis/guidance/defo")
PT = "@level=0.1,ratio=None"                 # adopted point (adoption.json "penalty"; run.log:496)
CHOSEN = "log_c_corrector_unweighted"        # verdict.json:2 "adopted"
TWIN = "log_c_plain_unweighted"              # P2: tool twin (no gls arm, run.log:495)
TWIN_SIMPLER = True                          # P2: twin tool 'plain', chosen 'corrector'
LABEL_BUILT = ["h_nbr1", "h_nbr2", "h_nbr_cum", "h_yrs_since"]   # P4 M6 defo; catalog.yaml:144
CAP = 50_000
K = 5
ALARM = 2.0
REL = 1e-9

T0 = time.time()
PROC = psutil.Process()


def log(msg):
    print("[%6.1fs] %s" % (time.time() - T0, msg), flush=True)


def sha1_hex(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def fold_of(g):
    return int(sha1_hex(g), 16) % K


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def cap_rows(idx, keys):
    """P4 M5: keep the CAP rows with the lowest int(sha1(unit|time)) (fixed-length hex => same order)."""
    if idx.size <= CAP:
        return idx
    order = np.argsort(keys[idx], kind="stable")
    return np.sort(idx[order[:CAP]])


def arm_name(spec):
    return "%s_%s_%s" % (spec["link"], spec["tool"], spec["weighting"])


# ----------------------------------------------------------------------------------------------- M5: exact LAD LP
def lad_weights(P, y):
    """min sum t s.t. t >= y - Pw, t >= Pw - y, w >= 0, sum w = 1 (P4 M5), HiGHS, default options."""
    n, m = P.shape
    I = sp.identity(n, format="csr")
    Ps = sp.csr_matrix(P)
    A_ub = sp.vstack([sp.hstack([-Ps, -I]), sp.hstack([Ps, -I])], format="csr")
    b_ub = np.concatenate([-y, y])
    A_eq = sp.csr_matrix(np.concatenate([np.ones(m), np.zeros(n)])[None, :])
    c = np.concatenate([np.zeros(m), np.ones(n)])
    bounds = [(0, None)] * m + [(None, None)] * n
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0], bounds=bounds, method="highs")
    if r.status != 0:
        raise SystemExit("linprog failed: %s" % r.message)
    w = r.x[:m].copy()
    w[w < 1e-9] = 0.0
    w = w / w.sum()
    return w, float(r.fun) / n


def m5_fit(P, y, folds, keys, tag):
    oof = np.full(len(y), np.nan)
    fw = []
    for k in range(K):
        te = np.flatnonzero(folds == k)
        if te.size == 0:
            fw.append(None)
            continue
        tr = cap_rows(np.flatnonzero(folds != k), keys)
        w, _ = lad_weights(P[tr], y[tr])
        oof[te] = P[te] @ w
        fw.append(w.tolist())
        log("  %s fold %d: train %d rows, w %s" % (tag, k, tr.size, np.round(w, 4).tolist()))
    cf = float(np.mean(np.abs(y - oof)))
    tr = cap_rows(np.arange(len(y)), keys)
    w_full, _ = lad_weights(P[tr], y[tr])
    log("  %s full: train %d rows, w %s, CF-MAE %.9f" % (tag, tr.size, np.round(w_full, 4).tolist(), cf))
    return w_full, cf, fw


# --------------------------------------------------------------------------------------- M6: per-row chooser
def prep_fit(Xtr):
    """P4 M6 preprocessing, fitted on the training rows only. Returns (keep, med, mu, sd)."""
    miss = np.isnan(Xtr)
    keep = []
    for j in range(Xtr.shape[1]):
        if miss[:, j].mean() > 0.5:
            continue
        a = Xtr[~miss[:, j], j]
        if a.size == 0 or np.all(a == a[0]):
            continue
        keep.append(j)
    keep = np.array(keep)
    X = Xtr[:, keep].copy()
    med = np.nanmedian(X, axis=0)
    m = np.isnan(X)
    X[m] = np.take(med, np.nonzero(m)[1])
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    return keep, med, mu, sd


def prep_apply(X, prm):
    keep, med, mu, sd = prm
    Z = X[:, keep].astype(np.float64)
    m = np.isnan(Z)
    Z[m] = np.take(med, np.nonzero(m)[1])
    return np.clip((Z - mu) / sd, -10, 10)


def new_clf():
    return LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, class_weight=None,
                              fit_intercept=True)


def get_rows(Xmm, rows, cols):
    """rows of the surface matrix (memmap) -> float64 in memory, only the feature columns."""
    o = np.argsort(rows, kind="stable")
    out = np.empty((rows.size, cols.size), dtype=np.float64)
    out[o] = Xmm[rows[o]][:, cols]
    return out


def m6_fit(Xmm, cols, src, z, nontie, folds, keys, tag):
    """src maps surface row -> the row whose features it gets (identity, or the placebo pairing)."""
    oof = np.full(len(z), np.nan)
    info = []
    for k in range(K):
        te = np.flatnonzero((folds == k) & nontie)
        if te.size == 0:
            info.append(None)
            continue
        tr = cap_rows(np.flatnonzero((folds != k) & nontie), keys)
        Xtr = get_rows(Xmm, src[tr], cols)
        prm = prep_fit(Xtr)
        clf = new_clf().fit(prep_apply(Xtr, prm), z[tr])
        del Xtr
        oof[te] = clf.predict_proba(prep_apply(get_rows(Xmm, src[te], cols), prm))[:, 1]
        info.append({"train_rows": int(tr.size), "test_rows": int(te.size), "n_iter": int(clf.n_iter_[0]),
                     "kept_columns": int(prm[0].size)})
        log("  %s fold %d: train %d, oof %d, iter %d, kept %d" % (tag, k, tr.size, te.size, clf.n_iter_[0],
                                                                  prm[0].size))
    nt = np.flatnonzero(nontie)
    acc = float(np.mean((oof[nt] > 0.5) == (z[nt] == 1)))
    base = float(np.mean(z[nt] == 1))
    auc = float(roc_auc_score(z[nt], oof[nt]))
    n1 = int((z[nt] == 1).sum())
    n0 = int((z[nt] == 0).sum())
    if nt.size < 200 or n1 < 20 or n0 < 20:
        fb = "FALLBACK:ROWS"
    elif acc < 0.55:
        fb = "FALLBACK:ACC"
    else:
        fb = None
    tr = cap_rows(nt, keys)
    Xtr = get_rows(Xmm, src[tr], cols)
    prm = prep_fit(Xtr)
    clf = new_clf().fit(prep_apply(Xtr, prm), z[tr])
    del Xtr
    log("  %s: ACC %.4f base %.4f AUC %.4f non-tie %d (z1 %d, z0 %d) -> %s; full fit %d rows, iter %d"
        % (tag, acc, base, auc, nt.size, n1, n0, fb or "APPLY", tr.size, clf.n_iter_[0]))
    return clf, prm, {"ACC": acc, "base_rate_twin_wins": base, "AUC": auc, "non_tie_rows": int(nt.size),
                      "z1": n1, "z0": n0, "fallback": fb, "folds": info, "full_train_rows": int(tr.size),
                      "full_n_iter": int(clf.n_iter_[0]), "full_kept_columns": int(prm[0].size),
                      "oof_mean_p": float(np.mean(oof[nt]))}


def m6_predict_test(clf, prm, Xt_mm, cols):
    out = np.empty(Xt_mm.shape[0])
    for s in range(0, Xt_mm.shape[0], 50_000):
        e = min(s + 50_000, Xt_mm.shape[0])
        out[s:e] = clf.predict_proba(prep_apply(np.asarray(Xt_mm[s:e][:, cols], dtype=np.float64), prm))[:, 1]
    return out


def main():
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == PROTOCOL_SHA, "protocol hash mismatch"
    log("protocol hash OK")
    adoption = json.load(open(RUN / "adoption.json"))
    verdict = json.load(open(RUN / "verdict.json"))
    assert verdict["adopted"] == CHOSEN
    assert adoption["penalty"] == {"level": 0.1, "ratio": None}
    order = adoption["decision"]["candidate_order"]
    elig = [arm_name(e) for e in adoption["eligible"]]
    elig = [a for a in order if a in elig]                      # P1: listed in candidate_order
    assert len(elig) == 6 and CHOSEN in elig and TWIN in elig, elig

    # ------------------------------------------------------------------ G1 surface reproduction (P3)
    cand = pd.read_csv(RUN / "inner_candidates.csv")
    tree = cand[~cand.arm.str.contains("trees_off")]
    off = {r.arm.split("_trees_off")[0]: r.mae for r in cand[cand.arm.str.contains("trees_off")].itertuples()}
    cols_s = ["unit", "group", "time", "y"] + [a + PT for a in elig]
    S = pd.read_parquet(RUN / "inner_preds.parquet", columns=cols_s)
    y = S["y"].to_numpy(np.float64)
    assert np.isfinite(y).all()
    Ps = np.column_stack([S[a + PT].to_numpy(np.float64) for a in elig])
    assert np.isfinite(Ps).all()
    ic, it = elig.index(CHOSEN), elig.index(TWIN)
    C_s, T_s = Ps[:, ic], Ps[:, it]
    g1 = {"rows": len(S)}
    mae_c = float(np.mean(np.abs(y - C_s)))
    csv_c = float(tree[(tree.arm == CHOSEN) & (tree.level == 0.1)].mae.iloc[0])
    g1["chosen_surface_mae"] = mae_c
    g1["chosen_csv"] = csv_c
    g1["chosen_rel"] = rel(mae_c, csv_c)
    own_pick, point_flag, own_rel = {}, [], {}
    recomputed_elig = []
    for a in tree.arm.unique():
        sub = tree[tree.arm == a].reset_index(drop=True)          # rows in grid order
        b = 0
        for i in range(1, len(sub)):
            if sub.mae[i] < sub.mae[b]:
                b = i
        own_pick[a] = {"level": float(sub.level[b]), "mae": float(sub.mae[b])}
        link = a.split("_plain")[0].split("_corrector")[0]
        if sub.mae[b] < off[link]:
            recomputed_elig.append(a)
        if a in elig:
            col = "%s@level=%r,ratio=None" % (a, float(sub.level[b]))
            if col == a + PT:
                m = float(np.mean(np.abs(y - Ps[:, elig.index(a)])))
            else:
                m = float(np.mean(np.abs(y - pd.read_parquet(RUN / "inner_preds.parquet", columns=[col])[col])))
                point_flag.append({"arm": a, "own_level": float(sub.level[b]), "used_level": 0.1})
            own_rel[a] = rel(m, float(sub.mae[b]))
    g1["own_pick"] = own_pick
    g1["own_pick_rel"] = own_rel
    g1["recomputed_eligible"] = sorted(recomputed_elig)
    g1["pass"] = bool(g1["chosen_rel"] <= REL and all(v <= REL for v in own_rel.values())
                      and sorted(recomputed_elig) == sorted(elig))
    log("G1 %s: chosen surface MAE %.12f vs csv %.12f (rel %.1e); own-pick max rel %.1e; eligible %s"
        % ("PASS" if g1["pass"] else "FAIL", mae_c, csv_c, g1["chosen_rel"], max(own_rel.values()),
           sorted(recomputed_elig) == sorted(elig)))
    if not g1["pass"]:
        raise SystemExit("G1 failed: defo not run")

    # ------------------------------------------------------------------ test inputs (no 'y')
    tcols = ["unit", "group", "time", "year", "issue"] + ["arm__" + a for a in elig]
    T = pd.read_parquet(RUN / "test_preds.parquet", columns=tcols)
    assert "y" not in T.columns
    Pt = np.column_stack([T["arm__" + a].to_numpy(np.float64) for a in elig])
    C_t, T_t = Pt[:, ic], Pt[:, it]
    fin_ct = np.isfinite(C_t) & np.isfinite(T_t)
    log("test rows %d; finite C&T %d; finite all eligible %d" % (len(T), fin_ct.sum(), np.isfinite(Pt).all(1).sum()))

    # ------------------------------------------------------------------ alarm (M1, M2), M3, M4
    gap_s = float(np.mean(np.abs(C_s - T_s)))
    gap_t = float(np.mean(np.abs(C_t[fin_ct] - T_t[fin_ct])))
    ratio = gap_t / gap_s
    fires = ratio > ALARM
    yr = T["year"].to_numpy()
    ratio_year = {int(v): float(np.mean(np.abs(C_t[fin_ct & (yr == v)] - T_t[fin_ct & (yr == v)]))) / gap_s
                  for v in sorted(np.unique(yr))}
    log("alarm: gap surface %.6e, test %.6e, ratio %.4f -> %s; per year %s"
        % (gap_s, gap_t, ratio, "FIRES" if fires else "silent", {k: round(v, 3) for k, v in ratio_year.items()}))
    M1 = T_t.copy() if (fires and TWIN_SIMPLER) else C_t.copy()
    M2 = 0.5 * C_t + 0.5 * T_t if fires else C_t.copy()
    M3 = 0.5 * C_t + 0.5 * T_t
    M4 = Pt.mean(axis=1)
    m4_surface = float(np.mean(np.abs(y - Ps.mean(axis=1))))
    log("M4 surface MAE (beside) %.9f vs chosen %.9f" % (m4_surface, mae_c))

    # ------------------------------------------------------------------ folds, keys, placebo pairing
    folds = np.array([fold_of(g) for g in S["group"]])
    keys = np.array([sha1_hex("%s|%d" % (u, t)) for u, t in zip(S["unit"], S["time"])])
    keys_b = np.array([sha1_hex("placebo|%s|%d" % (u, t)) for u, t in zip(S["unit"], S["time"])])
    a_ord = np.argsort(keys, kind="stable")
    b_ord = np.argsort(keys_b, kind="stable")
    src_pl = np.empty(len(S), dtype=np.int64)
    src_pl[a_ord] = b_ord                                   # row a[k] gets row b[k]
    y_pl = np.empty_like(y)
    y_pl[a_ord] = y[b_ord]
    fold_sizes = {int(k): int((folds == k).sum()) for k in range(K)}
    log("folds by group: %s" % fold_sizes)

    # ------------------------------------------------------------------ M5 stacking + placebo
    log("M5 (LAD LP, HiGHS)")
    w5, cf5, fw5 = m5_fit(Ps, y, folds, keys, "M5")
    gate5 = cf5 < mae_c
    M5raw = Pt @ w5
    M5 = M5raw.copy() if gate5 else C_t.copy()
    log("M5 gate: CF-MAE %.9f %s chosen surface MAE %.9f -> %s"
        % (cf5, "<" if gate5 else ">=", mae_c, "APPLY" if gate5 else "FALLBACK:CF"))
    log("M5 placebo (labels shuffled)")
    w5p, cf5p, fw5p = m5_fit(Ps, y_pl, folds, keys, "M5plc")
    mae_c_pl = float(np.mean(np.abs(y_pl - C_s)))
    gate5p = cf5p < mae_c_pl
    M5plc_u = Pt @ w5p
    M5plc_g = M5plc_u.copy() if gate5p else C_t.copy()
    log("M5 placebo gate: CF-MAE %.9f vs chosen on y_placebo %.9f -> %s"
        % (cf5p, mae_c_pl, "APPLY" if gate5p else "FALLBACK:CF"))

    # ------------------------------------------------------------------ M6 chooser + placebo
    meta = json.load(open(ADV / "features_meta.json"))
    feats = meta["features"]
    assert meta["G3_surface_joined"] == meta["G3_surface_rows"] == len(S)
    assert meta["G3_test_joined"] == meta["G3_test_rows"] == len(T)
    lb_idx = [feats.index(c) for c in LABEL_BUILT]
    assert lb_idx == [34, 35, 36, 37], lb_idx
    fcols = np.array([j for j in range(len(feats)) if j not in lb_idx])
    assert fcols.size == 299
    Xs = np.load(ADV / "X_surface.npy", mmap_mode="r")
    Xt = np.load(ADV / "X_test.npy", mmap_mode="r")
    assert Xs.shape == (len(S), 303) and Xt.shape == (len(T), 303)
    g3 = {"surface_joined": meta["G3_surface_joined"], "surface_rows": len(S),
          "test_joined": meta["G3_test_joined"], "test_rows": len(T), "pass": True,
          "note": "row-aligned to inner_preds / test_preds order (adv_validation/defo/build_features.py:104-151)"}
    eC = np.abs(y - C_s)
    eT = np.abs(y - T_s)
    z = np.where(eT < eC, 1, 0)
    nontie = eT != eC
    log("M6 target: non-tie %d of %d (ties %d), twin wins %d" % (nontie.sum(), len(z), (~nontie).sum(),
                                                                 (z[nontie] == 1).sum()))
    ident = np.arange(len(S))
    log("M6 (logistic chooser)")
    clf6, prm6, d6 = m6_fit(Xs, fcols, ident, z, nontie, folds, keys, "M6")
    p6 = m6_predict_test(clf6, prm6, Xt, fcols)
    log("M6 placebo (features shuffled)")
    clf6p, prm6p, d6p = m6_fit(Xs, fcols, src_pl, z, nontie, folds, keys, "M6plc")
    p6p = m6_predict_test(clf6p, prm6p, Xt, fcols)
    M6_u = np.where(p6 > 0.5, T_t, C_t)
    M6s_u = (1 - p6) * C_t + p6 * T_t
    M6p_u = np.where(p6p > 0.5, T_t, C_t)
    M6sp_u = (1 - p6p) * C_t + p6p * T_t
    M6 = C_t.copy() if d6["fallback"] else M6_u
    M6s = C_t.copy() if d6["fallback"] else M6s_u
    M6p_g = C_t.copy() if d6p["fallback"] else M6p_u
    M6sp_g = C_t.copy() if d6p["fallback"] else M6sp_u
    d6["test_share_switched_to_twin"] = float(np.mean(p6 > 0.5))
    d6["test_mean_p"] = float(np.mean(p6))
    d6p["test_share_switched_to_twin"] = float(np.mean(p6p > 0.5))
    d6p["test_mean_p"] = float(np.mean(p6p))
    coef = clf6.coef_[0]
    kept_names = [feats[fcols[j]] for j in prm6[0]]
    top = np.argsort(-np.abs(coef))[:10]
    d6["top10_coef"] = [[kept_names[j], float(coef[j])] for j in top]
    log("M6 test: switched %.4f, mean p %.4f; placebo switched %.4f, mean p %.4f"
        % (d6["test_share_switched_to_twin"], d6["test_mean_p"], d6p["test_share_switched_to_twin"],
           d6p["test_mean_p"]))

    # ------------------------------------------------------------------ write stage A
    MP = pd.DataFrame({"unit": T["unit"].to_numpy(), "time": T["time"].to_numpy(),
                       "C_chosen": C_t, "T_twin": T_t,
                       "M1": M1, "M2": M2, "M3": M3, "M4": M4,
                       "M5": M5, "M5raw": M5raw, "M5_placebo_ungated": M5plc_u, "M5_placebo_gated": M5plc_g,
                       "M6": M6, "M6s": M6s, "M6_ungated": M6_u, "M6s_ungated": M6s_u,
                       "M6_placebo_ungated": M6p_u, "M6s_placebo_ungated": M6sp_u,
                       "M6_placebo_gated": M6p_g, "M6s_placebo_gated": M6sp_g,
                       "M6_p": p6, "M6_placebo_p": p6p})
    MP.to_parquet(OUT / "method_preds_defo.parquet", index=False)
    rep = {"protocol_sha256": PROTOCOL_SHA, "run": str(RUN), "chosen": CHOSEN, "twin": TWIN,
           "twin_simpler": TWIN_SIMPLER, "twin_eligible": TWIN in elig, "eligible": elig,
           "adopted_point": PT, "point_flag": point_flag,
           "G1": g1, "G3": g3,
           "alarm": {"gap_surface": gap_s, "gap_test": gap_t, "ratio": ratio, "fires": bool(fires),
                     "ratio_per_test_year": ratio_year, "threshold": ALARM,
                     "M1_uses": "T" if (fires and TWIN_SIMPLER) else "C", "M2_uses": "blend" if fires else "C"},
           "M4": {"surface_mae_blend": m4_surface, "chosen_surface_mae": mae_c},
           "M5": {"weights_full": dict(zip(elig, w5.tolist())), "fold_weights": fw5, "CF_MAE": cf5,
                  "chosen_surface_mae": mae_c, "gate_pass": bool(gate5),
                  "status": "APPLY" if gate5 else "FALLBACK:CF"},
           "M5_placebo": {"weights_full": dict(zip(elig, w5p.tolist())), "fold_weights": fw5p, "CF_MAE": cf5p,
                          "chosen_surface_mae_on_y_placebo": mae_c_pl, "gate_pass": bool(gate5p),
                          "status": "APPLY" if gate5p else "FALLBACK:CF"},
           "M6": d6, "M6_placebo": d6p,
           "M6_features": {"n": int(fcols.size), "excluded_label_built": LABEL_BUILT,
                           "full_fit_kept": int(prm6[0].size)},
           "folds_rows": fold_sizes, "fold_groups": {int(k): sorted({g for g in S["group"] if fold_of(g) == k})
                                                     for k in range(K)},
           "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
                        "sklearn": sklearn.__version__, "pandas": pd.__version__},
           "seconds": time.time() - T0,
           "peak_ram_gb": PROC.memory_info().peak_wset / 2**30}
    with open(OUT / "stageA_defo.json", "w") as f:
        json.dump(rep, f, indent=1)
    lines = []
    for p in (OUT / "method_preds_defo.parquet", OUT / "stageA_defo.json", OUT / "scripts" / "stage_a.py"):
        lines.append("%s  %s" % (hashlib.sha256(p.read_bytes()).hexdigest(), p.name))
    (OUT / "stageA.sha256.txt").write_text("\n".join(lines) + "\n")
    log("stage A written; peak RAM %.2f GB" % rep["peak_ram_gb"])


if __name__ == "__main__":
    main()
