"""STAGE A -- pm25 -- label-free guidance of the tool choice (PROTOCOL.txt sha256 c51fc39a...6201eef4).

Builds every method's TEST predictions (M1-M6, M6s, placebos) and writes them BEFORE any test label is read.
Reads test_preds.parquet with key columns and 'arm__' columns ONLY (never 'y'). Surface labels (inner_preds 'y')
are used, as the protocol allows. Read-only on runs / adv_validation / engine. Writes only under
D:/treeroute/analysis/guidance/pm25.
"""
import hashlib
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd
import psutil
import pyarrow.parquet as pq
import scipy.sparse as sp
from scipy.optimize import linprog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

warnings.filterwarnings("ignore", category=FutureWarning)  # sklearn 1.9 'penalty' deprecation; same model

T0 = time.time()
PROC = psutil.Process()
PKG = "pm25"
RUN = "D:/treeroute/runs/pm25/headline/20261007_74e67609"
ADV = "D:/treeroute/analysis/adv_validation/pm25"
OUT = "D:/treeroute/analysis/guidance/pm25"
PROTOCOL = "D:/treeroute/analysis/guidance/PROTOCOL.txt"
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"

CHOSEN = "log_c_corrector_unweighted"
TWIN = "log_c_corrector_gls"          # protocol section 2: weighting twin, NOT simpler (twin is gls)
TWIN_SIMPLER = False
LEVEL, RATIO = 30.0, 1.0              # adoption.json:255; run.log:1338
SUFFIX = "@level=30.0,ratio=1.0"
ALARM = 2.0
K = 5
CAP = 50_000
LOG = []


def log(msg):
    line = "[%7.1fs] %s" % (time.time() - T0, msg)
    print(line, flush=True)
    LOG.append(line)


def rss_gb():
    mi = PROC.memory_info()
    return round(getattr(mi, "peak_wset", mi.rss) / 1e9, 3)


def sha1int(s):
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16)


def file_sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- protocol hash
assert file_sha256(PROTOCOL) == PROTOCOL_SHA, "PROTOCOL.txt hash mismatch -- stop"
log("protocol hash OK %s" % PROTOCOL_SHA)

adoption = json.load(open(os.path.join(RUN, "adoption.json")))
assert adoption["penalty"] == {"level": LEVEL, "ratio": RATIO}, adoption["penalty"]
CO = [a for a in adoption["decision"]["candidate_order"] if "trees_off" not in a]
print("adoption.adopted:", adoption["adopted"])
ELIG = ["%s_%s_%s" % (e["link"], e["tool"], e["weighting"]) for e in adoption["eligible"]]
ORDER = [a for a in CO if a in ELIG]
assert sorted(ORDER) == sorted(ELIG) and len(ELIG) == 8, (ORDER, ELIG)
ELIG = ORDER
assert CHOSEN in ELIG and TWIN in ELIG
log("eligible (candidate_order): %s" % ELIG)

# ---------------------------------------------------------------- surface (inner_preds) + G1
ipf = pq.ParquetFile(os.path.join(RUN, "inner_preds.parquet"))
names = ipf.schema_arrow.names
grid_cols = [c for c in names if "@" in c and not c.startswith("pre__") and c.split("@")[0] in ELIG]
S = pq.read_table(os.path.join(RUN, "inner_preds.parquet"),
                  columns=["unit", "group", "time", "y"] + grid_cols).to_pandas()
log("surface rows %d, grid cols read %d, RAM peak %.3f GB" % (len(S), len(grid_cols), rss_gb()))
ys = S["y"].to_numpy(np.float64)
assert np.isfinite(ys).all()

cand = pd.read_csv(os.path.join(RUN, "inner_candidates.csv"))
g1 = {"max_rel_diff_all_points": 0.0, "picks": {}}
for c in grid_cols:
    arm, pt = c.split("@")
    lv, rt = pt.replace("level=", "").replace("ratio=", "").split(",")
    row = cand[(cand.arm == arm) & (cand.level == float(lv)) & (cand.ratio == float(rt))]
    assert len(row) == 1, c
    m = float(np.mean(np.abs(ys - S[c].to_numpy(np.float64))))
    rel = abs(m - float(row.mae.iloc[0])) / abs(float(row.mae.iloc[0]))
    g1["max_rel_diff_all_points"] = max(g1["max_rel_diff_all_points"], rel)
off = {r.arm.split("_trees_off")[0]: float(r.mae) for r in cand[cand.arm.str.contains("trees_off")].itertuples()}
elig_re = []
for arm in CO:
    sub = cand[cand.arm == arm]
    best = None
    for r in sub.itertuples():           # first strictly lower, csv (grid) order -- decide.py:280-281
        if best is None or r.mae < best.mae:
            best = r
    link = "log_c" if arm.startswith("log_c") else "identity"
    ok = best.mae < off[link]            # N2, decide.py:290-299 / :460
    g1["picks"][arm] = {"level": best.level, "ratio": best.ratio, "mae": best.mae, "own_trees_off": off[link],
                        "eligible": bool(ok),
                        "at_adopted_point": bool(best.level == LEVEL and best.ratio == RATIO)}
    if ok:
        elig_re.append(arm)
chosen_mae_csv = float(cand[(cand.arm == CHOSEN) & (cand.level == LEVEL) & (cand.ratio == RATIO)].mae.iloc[0])
C_s = S[CHOSEN + SUFFIX].to_numpy(np.float64)
T_s = S[TWIN + SUFFIX].to_numpy(np.float64)
chosen_mae = float(np.mean(np.abs(ys - C_s)))
g1["chosen_surface_mae"] = chosen_mae
g1["chosen_rel_diff"] = abs(chosen_mae - chosen_mae_csv) / chosen_mae_csv
g1["eligible_recomputed"] = elig_re
g1["PASS"] = bool(g1["chosen_rel_diff"] <= 1e-9 and g1["max_rel_diff_all_points"] <= 1e-9
                  and sorted(elig_re) == sorted(ELIG))
log("G1 %s chosen rel %.2e, max rel over %d points %.2e, eligible recomputed %d" % (
    g1["PASS"], g1["chosen_rel_diff"], len(grid_cols), g1["max_rel_diff_all_points"], len(elig_re)))
assert g1["PASS"], "G1 failed -- stop"
point_flags = {a: [g1["picks"][a]["level"], g1["picks"][a]["ratio"]] for a in ELIG
               if not g1["picks"][a]["at_adopted_point"]}
log("point flags (own pick differs from adopted, used at adopted point): %s" % point_flags)

P_s = np.column_stack([S[a + SUFFIX].to_numpy(np.float64) for a in ELIG])   # surface, adopted point
assert np.isfinite(P_s).all()
S = S[["unit", "group", "time"]].copy()
S["time"] = S["time"].astype(np.int64)
assert not S.duplicated(["unit", "time"]).any()

# ---------------------------------------------------------------- test (NO y)
tcols = ["unit", "group", "time", "year", "issue"] + ["arm__" + a for a in ELIG]
assert "y" not in tcols
Tt = pq.read_table(os.path.join(RUN, "test_preds.parquet"), columns=tcols).to_pandas()
Tt["time"] = Tt["time"].astype(np.int64)
assert (Tt["time"] == Tt["issue"]).all()
P_t = np.column_stack([Tt["arm__" + a].to_numpy(np.float64) for a in ELIG])
iC, iT = ELIG.index(CHOSEN), ELIG.index(TWIN)
C_t, T_t = P_t[:, iC], P_t[:, iT]
fin_t = np.isfinite(C_t) & np.isfinite(T_t)
log("test rows %d; finite C&T %d; all-arms finite %d" % (len(Tt), fin_t.sum(), np.isfinite(P_t).all(1).sum()))

# ---------------------------------------------------------------- alarm M1/M2/M3
gap_s = float(np.mean(np.abs(C_s - T_s)))
gap_t = float(np.mean(np.abs(C_t[fin_t] - T_t[fin_t])))
ratio = gap_t / gap_s
fires = bool(ratio > ALARM)
ratio_year = {}
for yr in sorted(Tt["year"].unique()):
    m = fin_t & (Tt["year"].to_numpy() == yr)
    ratio_year[int(yr)] = float(np.mean(np.abs(C_t[m] - T_t[m])) / gap_s)
log("alarm: gap surface %.6f test %.6f ratio %.4f fires %s; per year %s" % (gap_s, gap_t, ratio, fires, ratio_year))
blend2 = 0.5 * C_t + 0.5 * T_t
M = {}
M["M1"] = T_t.copy() if (fires and TWIN_SIMPLER) else C_t.copy()
M["M2"] = blend2.copy() if fires else C_t.copy()
M["M3"] = blend2.copy()
M["M4"] = P_t.mean(axis=1)
m4_surface_mae = float(np.mean(np.abs(ys - P_s.mean(axis=1))))
log("M4 surface MAE (beside) %.6f vs chosen %.6f" % (m4_surface_mae, chosen_mae))

# ---------------------------------------------------------------- keys: cap order, folds, placebo permutation
skey = np.array([sha1int(u + "|" + str(t)) for u, t in zip(S["unit"], S["time"])], dtype=object)
pkey = np.array([sha1int("placebo|" + u + "|" + str(t)) for u, t in zip(S["unit"], S["time"])], dtype=object)
cap_rank = np.empty(len(S), np.int64)
cap_rank[np.array(sorted(range(len(S)), key=lambda i: skey[i]))] = np.arange(len(S))   # 0 = lowest sha1
grp_fold = {g: sha1int(g) % K for g in S["group"].unique()}
fold = S["group"].map(grp_fold).to_numpy(np.int64)
order_a = np.array(sorted(range(len(S)), key=lambda i: skey[i]))
order_b = np.array(sorted(range(len(S)), key=lambda i: pkey[i]))
y_plac = np.empty_like(ys)
y_plac[order_a] = ys[order_b]
fold_sizes = {int(k): int((fold == k).sum()) for k in range(K)}
log("folds by group (%d groups): rows per fold %s" % (len(grp_fold), fold_sizes))


def capped(idx):
    """idx: integer row indices; keep the CAP with lowest sha1(unit|time)."""
    if len(idx) <= CAP:
        return idx
    return idx[np.argsort(cap_rank[idx], kind="stable")[:CAP]]


# ---------------------------------------------------------------- M5 exact LP
def lp_weights(P, y):
    n, A = P.shape
    c = np.r_[np.zeros(A), np.ones(n)]
    I = sp.identity(n, format="csr")
    Ps = sp.csr_matrix(P)
    A_ub = sp.vstack([sp.hstack([-Ps, -I]), sp.hstack([Ps, -I])], format="csr")
    b_ub = np.r_[-y, y]
    A_eq = sp.csr_matrix(np.r_[np.ones(A), np.zeros(n)][None, :])
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0], method="highs")
    assert res.status == 0, res.message
    w = res.x[:A].copy()
    w[w < 1e-9] = 0.0
    w = w / w.sum()
    return w, float(res.fun) / n


def m5_run(y_train, tag):
    oof = np.full(len(ys), np.nan)
    fw = {}
    for k in range(K):
        tr = capped(np.flatnonzero(fold != k))
        w, _ = lp_weights(P_s[tr], y_train[tr])
        fw[k] = w.tolist()
        te = fold == k
        oof[te] = P_s[te] @ w
        log("  M5[%s] fold %d: train %d rows, weights %s" % (tag, k, len(tr), np.round(w, 4).tolist()))
    cf = float(np.mean(np.abs(y_train - oof)))
    full_idx = capped(np.arange(len(ys)))
    w_full, _ = lp_weights(P_s[full_idx], y_train[full_idx])
    ref = float(np.mean(np.abs(y_train - C_s)))
    return {"cf_mae": cf, "chosen_surface_mae_same_y": ref, "gate_pass": bool(cf < ref),
            "fold_weights": fw, "full_weights": dict(zip(ELIG, w_full.tolist())),
            "full_train_rows": int(len(full_idx))}, w_full


log("M5 LP (true surface y)")
m5, w5 = m5_run(ys, "true")
M["M5raw"] = P_t @ w5
M["M5"] = M["M5raw"].copy() if m5["gate_pass"] else C_t.copy()
m5["applied"] = "M5" if m5["gate_pass"] else "FALLBACK:CF"
log("M5: CF-MAE %.6f vs chosen %.6f -> %s; full weights %s" % (
    m5["cf_mae"], m5["chosen_surface_mae_same_y"], m5["applied"], {k: round(v, 4) for k, v in m5["full_weights"].items()}))
log("M5 placebo LP (shuffled surface y)")
m5p, w5p = m5_run(y_plac, "placebo")
M["M5_placebo"] = P_t @ w5p
M["M5_placebo_gated"] = M["M5_placebo"].copy() if m5p["gate_pass"] else C_t.copy()
m5p["applied"] = "M5_placebo" if m5p["gate_pass"] else "FALLBACK:CF"
log("M5 placebo: CF-MAE %.6f vs chosen-on-y_placebo %.6f -> gated %s; weights %s; RAM %.3f GB" % (
    m5p["cf_mae"], m5p["chosen_surface_mae_same_y"], m5p["applied"],
    {k: round(v, 4) for k, v in m5p["full_weights"].items()}, rss_gb()))

# ---------------------------------------------------------------- features (G3)
finfo = json.load(open(os.path.join(ADV, "features_info.json")))
FEATS = list(finfo["tree_features"]) + list(finfo["context"])
assert len(FEATS) == 118 and not any(f.startswith("hist_") for f in FEATS)
fs = pq.read_table(os.path.join(ADV, "features_surface.parquet"), columns=["unit", "time"] + FEATS).to_pandas()
fs["time"] = fs["time"].astype(np.int64)
ft = pq.read_table(os.path.join(ADV, "features_test.parquet"), columns=["unit", "issue"] + FEATS).to_pandas()
ft = ft.rename(columns={"issue": "time"})
ft["time"] = ft["time"].astype(np.int64)
assert not fs.duplicated(["unit", "time"]).any() and not ft.duplicated(["unit", "time"]).any()
Xs_df = S[["unit", "time"]].merge(fs, on=["unit", "time"], how="left", indicator=True)
Xt_df = Tt[["unit", "time"]].merge(ft, on=["unit", "time"], how="left", indicator=True)
g3 = {"surface_join": float((Xs_df["_merge"] == "both").mean()), "test_join": float((Xt_df["_merge"] == "both").mean())}
g3["PASS"] = g3["surface_join"] == 1.0 and g3["test_join"] == 1.0
assert (Xs_df["unit"].to_numpy() == S["unit"].to_numpy()).all() and (Xt_df["time"].to_numpy() == Tt["time"].to_numpy()).all()
Xs = Xs_df[FEATS].apply(pd.to_numeric, errors="coerce").to_numpy(np.float64)
Xt = Xt_df[FEATS].apply(pd.to_numeric, errors="coerce").to_numpy(np.float64)
del fs, ft, Xs_df, Xt_df
log("G3 %s (surface %.4f, test %.4f); X surface %s test %s; RAM %.3f GB" % (g3["PASS"], g3["surface_join"], g3["test_join"],
                                                                        Xs.shape, Xt.shape, rss_gb()))


# ---------------------------------------------------------------- M6 chooser
class Prep:
    def fit(self, X):
        miss = np.isnan(X).mean(0)
        keep = miss <= 0.5
        with np.errstate(all="ignore"):
            lo, hi = np.nanmin(X, 0), np.nanmax(X, 0)
        keep &= ~(np.isnan(lo) | (lo == hi))
        self.keep = np.flatnonzero(keep)
        Xk = X[:, self.keep]
        self.med = np.nanmedian(Xk, 0)
        Xk = np.where(np.isnan(Xk), self.med, Xk)
        self.mu = Xk.mean(0)
        self.sd = Xk.std(0)
        self.sd[self.sd == 0] = 1.0
        self.n_dropped = int(X.shape[1] - len(self.keep))
        return self

    def transform(self, X):
        Xk = X[:, self.keep]
        Xk = np.where(np.isnan(Xk), self.med, Xk)
        return np.clip((Xk - self.mu) / self.sd, -10, 10)


def lr():
    return LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, class_weight=None, fit_intercept=True)


eC, eT = np.abs(ys - C_s), np.abs(ys - T_s)
z = np.where(eT < eC, 1, np.where(eC < eT, 0, -1))
nontie = z >= 0


def m6_run(X, tag):
    oof = np.full(len(ys), np.nan)
    info = {"folds": {}}
    for k in range(K):
        tr = capped(np.flatnonzero(nontie & (fold != k)))
        te = np.flatnonzero(nontie & (fold == k))
        pp = Prep().fit(X[tr])
        mdl = lr().fit(pp.transform(X[tr]), z[tr])
        oof[te] = mdl.predict_proba(pp.transform(X[te]))[:, 1]
        info["folds"][k] = {"train": int(len(tr)), "test": int(len(te)), "dropped_cols": pp.n_dropped,
                            "n_iter": int(mdl.n_iter_[0])}
    nt = np.flatnonzero(nontie)
    acc = float(np.mean((oof[nt] > 0.5) == (z[nt] == 1)))
    auc = float(roc_auc_score(z[nt], oof[nt]))
    n1 = int((z[nt] == 1).sum()); n0 = int((z[nt] == 0).sum())
    info.update({"nontie_rows": int(len(nt)), "ties": int((~nontie).sum()), "class1_twin_wins": n1, "class0": n0,
                 "base_rate_twin_wins": n1 / len(nt), "acc": acc, "auc": auc,
                 "acc_majority_class": max(n1, n0) / len(nt)})
    if len(nt) < 200 or n1 < 20 or n0 < 20:
        info["gate"] = "FALLBACK:ROWS"
    elif acc < 0.55:
        info["gate"] = "FALLBACK:ACC"
    else:
        info["gate"] = "PASS"
    full = capped(nt)
    pp = Prep().fit(X[full])
    mdl = lr().fit(pp.transform(X[full]), z[full])
    p = mdl.predict_proba(pp.transform(Xt))[:, 1]
    info.update({"full_train_rows": int(len(full)), "full_dropped_cols": pp.n_dropped, "full_n_iter": int(mdl.n_iter_[0]),
                 "test_mean_p": float(np.mean(p)), "test_share_p_gt_half": float(np.mean(p > 0.5))})
    hard = np.where(p > 0.5, T_t, C_t)
    soft = (1 - p) * C_t + p * T_t
    log("  M6[%s]: nontie %d (ties %d), base rate %.4f, CF ACC %.4f (majority %.4f), AUC %.4f -> %s; test mean p %.4f, "
        "switched %.4f" % (tag, len(nt), (~nontie).sum(), info["base_rate_twin_wins"], acc, info["acc_majority_class"],
                           auc, info["gate"], info["test_mean_p"], info["test_share_p_gt_half"]))
    return info, hard, soft


log("M6 chooser (true features)")
m6, h, s = m6_run(Xs, "true")
M["M6raw"], M["M6sraw"] = h, s
M["M6"] = h.copy() if m6["gate"] == "PASS" else C_t.copy()
M["M6s"] = s.copy() if m6["gate"] == "PASS" else C_t.copy()
log("M6 placebo (features shuffled against z)")
Xp = np.empty_like(Xs)
Xp[order_a] = Xs[order_b]
m6p, hp, sp_ = m6_run(Xp, "placebo")
del Xp
M["M6_placebo"], M["M6s_placebo"] = hp, sp_
M["M6_placebo_gated"] = hp.copy() if m6p["gate"] == "PASS" else C_t.copy()
M["M6s_placebo_gated"] = sp_.copy() if m6p["gate"] == "PASS" else C_t.copy()
log("RAM peak %.3f GB" % rss_gb())

# ---------------------------------------------------------------- write stage A
out = pd.DataFrame({"unit": Tt["unit"].to_numpy(), "time": Tt["time"].to_numpy()})
out["C_chosen"] = C_t
out["T_twin"] = T_t
for k, v in M.items():
    out[k] = v
mp = os.path.join(OUT, "method_preds_%s.parquet" % PKG)
out.to_parquet(mp, index=False)
switch = {k: float(np.mean(~np.isclose(v[fin_t], C_t[fin_t], rtol=0, atol=0))) for k, v in M.items()}
stage = {
    "package": PKG, "protocol_sha256": PROTOCOL_SHA, "run": RUN, "chosen": CHOSEN, "twin": TWIN,
    "twin_simpler": TWIN_SIMPLER, "twin_eligible": TWIN in ELIG, "adopted_point": {"level": LEVEL, "ratio": RATIO},
    "eligible": ELIG, "point_flags_used_at_adopted_point": point_flags, "G1": g1, "G3": g3,
    "surface_rows": int(len(ys)), "test_rows": int(len(Tt)), "test_rows_finite_C_T": int(fin_t.sum()),
    "alarm": {"gap_surface": gap_s, "gap_test": gap_t, "ratio": ratio, "fires": fires, "ratio_by_test_year": ratio_year},
    "M1_rule": "fires and twin simpler -> T else C" , "M4_surface_mae_beside": m4_surface_mae,
    "chosen_surface_mae": chosen_mae, "M5": m5, "M5_placebo": m5p, "M6": m6, "M6_placebo": m6p,
    "share_test_rows_differing_from_C": switch, "features": {"n": len(FEATS), "list": FEATS},
    "fold_of_group": {g: int(v) for g, v in grp_fold.items()}, "fold_rows": fold_sizes,
    "seconds": time.time() - T0, "peak_ram_gb": rss_gb(),
    "y_read_from_test_preds": False,
}
sj = os.path.join(OUT, "stageA_%s.json" % PKG)
json.dump(stage, open(sj, "w"), indent=1, default=float)
log("stage A done: %s, %s; %.1f s; peak RAM %.3f GB" % (mp, sj, time.time() - T0, rss_gb()))
lg = os.path.join(OUT, "stage_a.log")
open(lg, "w").write("\n".join(LOG) + "\n")
with open(os.path.join(OUT, "stageA.sha256.txt"), "w") as f:
    for p in [mp, sj, lg, os.path.abspath(__file__)]:
        f.write("%s  %s\n" % (file_sha256(p), p))
    f.write("written %s UTC, before stage B\n" % time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
