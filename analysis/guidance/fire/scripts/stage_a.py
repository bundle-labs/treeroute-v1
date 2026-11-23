"""Label-free guidance of the tool choice, FIRE, STAGE A (builds every method's test predictions).

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt (SHA-256 c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4).
Read-only on the run, the package, the stores, the engine and D:/treeroute/analysis/adv_validation.
Writes only under D:/treeroute/analysis/guidance/fire.
Gate G4: test_preds.parquet is read with the key columns and the 'arm__' columns ONLY; its 'y' is never read here.
Surface labels (inner_preds 'y') are training data and are used, as the protocol allows.
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
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import sparse
from scipy.optimize import linprog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

T0 = time.time()
PROC = psutil.Process()
PEAK = [0]


def mem():
    rss = PROC.memory_info().rss
    PEAK[0] = max(PEAK[0], rss)
    return rss / 2**30


GUIDE = Path("D:/treeroute/analysis/guidance")
OUT = GUIDE / "fire"
RUN = Path("D:/treeroute/runs/fire/headline/20261017_869d1f38")
FEAT = Path("D:/treeroute/analysis/adv_validation/fire")
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"

LEVEL, RATIO = 100.0, 1.0                      # adoption.json "penalty"; run.log:477
PT = "@level=100.0,ratio=1.0"
C_ARM = "arcsine_corrector_gls"                # verdict.json "adopted"
T_ARM = "arcsine_corrector_unweighted"         # protocol section 2 (weighting twin, SIMPLER)
T_SIMPLER = True
ELIGIBLE = ["arcsine_plain_gls", "arcsine_corrector_gls"]   # adoption.json "eligible" (candidate order)
ALL_ARMS = [f"{l}_{t}_{w}" for l in ("identity", "log_c", "arcsine")
            for t in ("plain", "corrector") for w in ("unweighted", "gls")]
FIRE_HISTORY = ["tslf_months", "tslf_censored", "n_burns_12mo", "n_burns_60mo", "burn_rate_120mo",
                "nbr25km_12mo_lag3", "nbr75km_12mo_lag3", "nbr25km_12mo_lag6", "nbr75km_12mo_lag6"]
CAP = 50_000
K = 5
ALARM = 2.0


def sha_hex(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel_eq(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-300)


def cap_rows(idx, order_key):
    """idx: integer row indices of a training set. Keep the CAP with the lowest sha1 hash (fixed, no seed)."""
    if len(idx) <= CAP:
        return idx
    keys = order_key[idx]
    keep = np.argsort(keys, kind="stable")[:CAP]
    return np.sort(idx[keep])


# ------------------------------------------------------------------ load surface (labels allowed)
assert sha_file(GUIDE / "PROTOCOL.txt") == PROTOCOL_SHA, "protocol file changed"
cols = ["unit", "group", "time", "y"] + [a + PT for a in ALL_ARMS]
S = pq.read_table(RUN / "inner_preds.parquet", columns=cols).to_pandas()
n_s = len(S)
y_s = S["y"].to_numpy(np.float64)
print(f"surface rows {n_s}; RAM {mem():.2f} GB", flush=True)

# ------------------------------------------------------------------ G1 surface reproduction
cand = pd.read_csv(RUN / "inner_candidates.csv")
g1 = {}
row = cand[(cand.arm == C_ARM) & (cand.level == LEVEL) & (cand.ratio == RATIO)].iloc[0]
c_surf_mae = float(np.mean(np.abs(y_s - S[C_ARM + PT].to_numpy())))
g1["chosen_adopted"] = {"recomputed": c_surf_mae, "csv": float(row.mae), "ok": rel_eq(c_surf_mae, float(row.mae))}
own_pick = {}
for arm in ALL_ARMS:
    sub = cand[cand.arm == arm].reset_index(drop=True)
    b = sub.loc[sub.mae.idxmin()]
    own_pick[arm] = {"level": float(b.level), "ratio": float(b.ratio), "mae": float(b.mae)}
need = {f"{a}@level={own_pick[a]['level']},ratio={own_pick[a]['ratio']}" for a in ELIGIBLE}
P_own = pq.read_table(RUN / "inner_preds.parquet", columns=sorted(need)).to_pandas()
for a in ELIGIBLE:
    c = f"{a}@level={own_pick[a]['level']},ratio={own_pick[a]['ratio']}"
    m = float(np.mean(np.abs(y_s - P_own[c].to_numpy())))
    g1["eligible_own_" + a] = {"point": c, "recomputed": m, "csv": own_pick[a]["mae"],
                               "ok": rel_eq(m, own_pick[a]["mae"])}
del P_own
off = {r.arm.split("_trees_off")[0]: float(r.mae) for r in cand[cand.arm.str.contains("trees_off")].itertuples()}
def link_of(a):
    return a.split("_plain")[0].split("_corrector")[0]


elig_re = [a for a in ALL_ARMS if own_pick[a]["mae"] < off[link_of(a)]]   # N2, decide.py:290-299
adoption = json.load(open(RUN / "adoption.json"))
elig_adopt = [f"{e['link']}_{e['tool']}_{e['weighting']}" for e in adoption["eligible"]]
g1["eligible_set"] = {"recomputed": sorted(elig_re), "adoption_json": sorted(elig_adopt),
                      "ok": sorted(elig_re) == sorted(elig_adopt) == sorted(ELIGIBLE)}
g1["twin_own_pick"] = own_pick[T_ARM]
g1["twin_surface_mae_adopted_point"] = float(np.mean(np.abs(y_s - S[T_ARM + PT].to_numpy())))
g1["arcsine_trees_off_mae"] = off["arcsine"]
g1["twin_eligible"] = own_pick[T_ARM]["mae"] < off["arcsine"]
G1_OK = all(v["ok"] for v in g1.values() if isinstance(v, dict) and "ok" in v)
print("G1", G1_OK, json.dumps(g1, default=str)[:600], flush=True)
if not G1_OK:
    sys.exit("G1 failed: fire 'not run'")

point_flags = [{"arm": a, "own_pick": own_pick[a], "used": {"level": LEVEL, "ratio": RATIO}}
               for a in ELIGIBLE + [T_ARM]
               if (own_pick[a]["level"], own_pick[a]["ratio"]) != (LEVEL, RATIO)]

# ------------------------------------------------------------------ load test (NO y)
tcols = ["unit", "group", "time", "year", "issue"] + ["arm__" + a for a in ALL_ARMS]
schema_names = pq.read_schema(RUN / "test_preds.parquet").names
assert all(c in schema_names for c in tcols) and "y" not in tcols
Tt = pq.read_table(RUN / "test_preds.parquet", columns=tcols).to_pandas()
n_t = len(Tt)
assert (Tt["time"] == Tt["issue"]).all()
print(f"test rows {n_t}; RAM {mem():.2f} GB", flush=True)

Cs, Ts = S[C_ARM + PT].to_numpy(np.float64), S[T_ARM + PT].to_numpy(np.float64)
Ct, Tt_ = Tt["arm__" + C_ARM].to_numpy(np.float64), Tt["arm__" + T_ARM].to_numpy(np.float64)
P_s = np.column_stack([S[a + PT].to_numpy(np.float64) for a in ELIGIBLE])
P_t = np.column_stack([Tt["arm__" + a].to_numpy(np.float64) for a in ELIGIBLE])
assert np.isfinite(P_s).all() and np.isfinite(Cs).all() and np.isfinite(Ts).all()

# fixed hash orders and folds
key_s = np.array([sha_hex(f"{u}|{t}") for u, t in zip(S["unit"], S["time"])])
key_b = np.array([sha_hex(f"placebo|{u}|{t}") for u, t in zip(S["unit"], S["time"])])
gfold = {g: int(sha_hex(g), 16) % K for g in S["group"].unique()}
fold = S["group"].map(gfold).to_numpy(np.int64)
order_a = np.argsort(key_s, kind="stable")
order_b = np.argsort(key_b, kind="stable")
perm_src = np.empty(n_s, dtype=np.int64)            # row a[k] takes from row b[k]
perm_src[order_a] = order_b
fold_sizes = {int(k): int((fold == k).sum()) for k in range(K)}
fold_groups = {int(k): sorted(g for g, f in gfold.items() if f == k) for k in range(K)}

# ------------------------------------------------------------------ M1 / M2 / M3
fin_t = np.isfinite(Ct) & np.isfinite(Tt_)
gap_s = float(np.mean(np.abs(Cs - Ts)))
gap_t = float(np.mean(np.abs(Ct[fin_t] - Tt_[fin_t])))
ratio = gap_t / gap_s
fires = ratio > ALARM
ratio_by_year = {int(yr): float(np.mean(np.abs(Ct[fin_t & (Tt.year.to_numpy() == yr)]
                                                - Tt_[fin_t & (Tt.year.to_numpy() == yr)])) / gap_s)
                 for yr in sorted(Tt.year.unique())}
blend = 0.5 * Ct + 0.5 * Tt_
M1 = Tt_.copy() if (fires and T_SIMPLER) else Ct.copy()
M2 = blend.copy() if fires else Ct.copy()
M3 = blend.copy()
print(f"alarm ratio {ratio:.4f} fires={fires}", flush=True)

# ------------------------------------------------------------------ M4
M4 = P_t.mean(axis=1)
m4_surface_mae = float(np.mean(np.abs(y_s - P_s.mean(axis=1))))


# ------------------------------------------------------------------ M5 (exact LP)
def lp_weights(P, y):
    n, k = P.shape
    I = sparse.identity(n, format="csr")
    Pm = sparse.csr_matrix(P)
    A_ub = sparse.vstack([sparse.hstack([-Pm, -I]), sparse.hstack([Pm, -I])], format="csr")
    b_ub = np.concatenate([-y, y])
    c = np.concatenate([np.zeros(k), np.ones(n)])
    A_eq = sparse.csr_matrix(np.concatenate([np.ones(k), np.zeros(n)])[None, :])
    r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0], method="highs")
    assert r.status == 0, r.message
    w = np.asarray(r.x[:k], dtype=np.float64)
    w[w < 1e-9] = 0.0
    w = w / w.sum()
    return w, r.message


def fit_m5(y_train):
    """Cross-fitted weights (K group folds) + full-surface weights, on the given surface labels."""
    oof = np.empty(n_s)
    fw = {}
    for k in range(K):
        tr = cap_rows(np.flatnonzero(fold != k), key_s)
        w, _ = lp_weights(P_s[tr], y_train[tr])
        fw[k] = w.tolist()
        te = fold == k
        oof[te] = P_s[te] @ w
        mem()
    full = cap_rows(np.arange(n_s), key_s)
    w_full, msg = lp_weights(P_s[full], y_train[full])
    cf = float(np.mean(np.abs(y_train - oof)))
    return {"fold_weights": fw, "full_weights": w_full.tolist(), "cf_mae": cf, "n_full_train": int(len(full)),
            "lp_message": msg}


t5 = time.time()
m5 = fit_m5(y_s)
m5["chosen_surface_mae"] = c_surf_mae
m5["applied"] = m5["cf_mae"] < c_surf_mae
M5raw = P_t @ np.array(m5["full_weights"])
M5 = M5raw.copy() if m5["applied"] else Ct.copy()
m5["status"] = "APPLIED" if m5["applied"] else "FALLBACK:CF"
y_pl = y_s[perm_src]
m5p = fit_m5(y_pl)
c_mae_on_ypl = float(np.mean(np.abs(y_pl - Cs)))
m5p["chosen_surface_mae_on_placebo_y"] = c_mae_on_ypl
m5p["applied_gated"] = m5p["cf_mae"] < c_mae_on_ypl
M5p_ung = P_t @ np.array(m5p["full_weights"])
M5p_gat = M5p_ung.copy() if m5p["applied_gated"] else Ct.copy()
m5["seconds"] = time.time() - t5
print(f"M5 w={m5['full_weights']} cf={m5['cf_mae']:.7f} vs C {c_surf_mae:.7f} -> {m5['status']}; "
      f"placebo w={m5p['full_weights']}; RAM {mem():.2f} GB", flush=True)

# ------------------------------------------------------------------ M6 features
fmeta = json.load(open(FEAT / "features_meta.json"))
feat_cols = [c for c in fmeta["tree_features"] if c not in FIRE_HISTORY] + fmeta["context"]
assert len(fmeta["tree_features"]) == 125 and len(feat_cols) == 118, len(feat_cols)
assert set(FIRE_HISTORY) <= set(fmeta["tree_features"])
FS = pq.read_table(FEAT / "features_surface.parquet", columns=["unit", "time"] + feat_cols).to_pandas()
FT = pq.read_table(FEAT / "features_test.parquet", columns=["unit", "issue"] + feat_cols).to_pandas()
js = S[["unit", "time"]].merge(FS, on=["unit", "time"], how="left", indicator=True, validate="one_to_one")
jt = Tt[["unit", "issue"]].merge(FT, on=["unit", "issue"], how="left", indicator=True, validate="one_to_one")
g3 = {"surface_joined": int((js["_merge"] == "both").sum()), "surface_rows": n_s,
      "test_joined": int((jt["_merge"] == "both").sum()), "test_rows": n_t}
G3_OK = g3["surface_joined"] == n_s and g3["test_joined"] == n_t
X_s = js[feat_cols].to_numpy(np.float64)
X_t = jt[feat_cols].to_numpy(np.float64)
del FS, FT, js, jt
print(f"G3 {G3_OK} {g3}; RAM {mem():.2f} GB", flush=True)


class Prep:
    def __init__(self, X):
        miss = np.isnan(X).mean(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lo, hi = np.nanmin(X, axis=0), np.nanmax(X, axis=0)
        const = ~(hi > lo)                                 # also True for an all-NaN column
        self.keep = np.flatnonzero((miss <= 0.5) & ~const)
        self.dropped_missing = int((miss > 0.5).sum())
        self.dropped_constant = int((const & (miss <= 0.5)).sum())
        Xk = X[:, self.keep]
        self.med = np.nanmedian(Xk, axis=0)
        Xk = np.where(np.isnan(Xk), self.med, Xk)
        self.mu = Xk.mean(axis=0)
        sd = Xk.std(axis=0)
        self.sd = np.where(sd > 0, sd, 1.0)

    def __call__(self, X):
        Xk = X[:, self.keep]
        Xk = np.where(np.isnan(Xk), self.med, Xk)
        return np.clip((Xk - self.mu) / self.sd, -10, 10)


def new_lr():
    return LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, class_weight=None,
                              fit_intercept=True)


eC, eT = np.abs(y_s - Cs), np.abs(y_s - Ts)
z = np.where(eT < eC, 1, np.where(eC < eT, 0, -1))
nontie = z >= 0


def fit_m6(X):
    out = {"n_nontie": int(nontie.sum()), "n_ties": int((~nontie).sum()),
           "n_class1": int((z == 1).sum()), "n_class0": int((z == 0).sum())}
    out["base_rate"] = out["n_class1"] / out["n_nontie"]
    oof = np.full(n_s, np.nan)
    n_iter = []
    for k in range(K):
        tr = cap_rows(np.flatnonzero((fold != k) & nontie), key_s)
        pr = Prep(X[tr])
        m = new_lr().fit(pr(X[tr]), z[tr])
        n_iter.append(int(m.n_iter_[0]))
        te = np.flatnonzero((fold == k) & nontie)
        oof[te] = m.predict_proba(pr(X[te]))[:, 1]
        mem()
    nt = np.flatnonzero(nontie)
    out["acc"] = float(np.mean((oof[nt] > 0.5) == (z[nt] == 1)))
    out["auc"] = float(roc_auc_score(z[nt], oof[nt]))
    out["oof_mean_p"] = float(np.nanmean(oof[nt]))
    fb = None
    if out["n_nontie"] < 200 or min(out["n_class1"], out["n_class0"]) < 20:
        fb = "FALLBACK:ROWS"
    elif out["acc"] < 0.55:
        fb = "FALLBACK:ACC"
    out["status"] = fb or "APPLIED"
    full = cap_rows(nt, key_s)
    pr = Prep(X[full])
    m = new_lr().fit(pr(X[full]), z[full])
    n_iter.append(int(m.n_iter_[0]))
    out["n_full_train"] = int(len(full))
    out["n_iter"] = n_iter
    out["features_used"] = int(len(pr.keep))
    out["dropped_missing"] = pr.dropped_missing
    out["dropped_constant"] = pr.dropped_constant
    p = m.predict_proba(pr(X_t))[:, 1]
    coef = m.coef_[0]
    kept = [feat_cols[i] for i in pr.keep]
    top = np.argsort(-np.abs(coef))[:10]
    out["top10_coef"] = [[kept[i], float(coef[i])] for i in top]
    return out, p


if G3_OK:
    t6 = time.time()
    m6, p = fit_m6(X_s)
    hard = np.where(p > 0.5, Tt_, Ct)
    soft = (1 - p) * Ct + p * Tt_
    M6raw, M6sraw = hard, soft
    M6 = hard.copy() if m6["status"] == "APPLIED" else Ct.copy()
    M6s = soft.copy() if m6["status"] == "APPLIED" else Ct.copy()
    m6["test_share_switched_to_T_raw"] = float(np.mean(p > 0.5))
    m6["test_mean_p"] = float(np.mean(p))
    print(f"M6 {m6['status']} acc={m6['acc']:.4f} base={m6['base_rate']:.4f} auc={m6['auc']:.4f} "
          f"switch={m6['test_share_switched_to_T_raw']:.4f}; RAM {mem():.2f} GB", flush=True)
    X_pl = X_s[perm_src]
    m6p, pp = fit_m6(X_pl)
    del X_pl
    M6p_ung = np.where(pp > 0.5, Tt_, Ct)
    M6sp_ung = (1 - pp) * Ct + pp * Tt_
    M6p_gat = M6p_ung.copy() if m6p["status"] == "APPLIED" else Ct.copy()
    M6sp_gat = M6sp_ung.copy() if m6p["status"] == "APPLIED" else Ct.copy()
    m6p["test_share_switched_to_T_raw"] = float(np.mean(pp > 0.5))
    m6p["test_mean_p"] = float(np.mean(pp))
    m6["seconds"] = time.time() - t6
    print(f"M6 placebo {m6p['status']} acc={m6p['acc']:.4f} auc={m6p['auc']:.4f} "
          f"switch={m6p['test_share_switched_to_T_raw']:.4f}; RAM {mem():.2f} GB", flush=True)
else:
    m6 = m6p = {"status": "NOT RUN (G3)"}
    p = pp = np.full(n_t, np.nan)
    M6 = M6s = M6raw = M6sraw = M6p_ung = M6sp_ung = M6p_gat = M6sp_gat = np.full(n_t, np.nan)

# ------------------------------------------------------------------ write stage A
preds = pd.DataFrame({
    "unit": Tt["unit"].astype(str), "group": Tt["group"].astype(str), "time": Tt["time"], "year": Tt["year"],
    "C": Ct, "T": Tt_, "M1": M1, "M2": M2, "M3": M3, "M4": M4, "M5": M5, "M5raw": M5raw,
    "M5_placebo_ungated": M5p_ung, "M5_placebo_gated": M5p_gat,
    "M6": M6, "M6s": M6s, "M6raw": M6raw, "M6sraw": M6sraw, "M6_p": p,
    "M6_placebo_ungated": M6p_ung, "M6s_placebo_ungated": M6sp_ung,
    "M6_placebo_gated": M6p_gat, "M6s_placebo_gated": M6sp_gat, "M6_placebo_p": pp,
})
pq.write_table(pa.Table.from_pandas(preds, preserve_index=False), OUT / "method_preds_fire.parquet")
stage = {
    "protocol_sha256": PROTOCOL_SHA, "problem": "fire", "run": str(RUN),
    "adopted_point": {"level": LEVEL, "ratio": RATIO}, "chosen": C_ARM, "twin": T_ARM, "twin_simpler": T_SIMPLER,
    "eligible": ELIGIBLE, "G1": g1, "G3": g3, "point_flags": point_flags,
    "surface_rows": n_s, "test_rows": n_t, "test_rows_finite_C_T": int(fin_t.sum()),
    "folds": {"by": "group (sha1(group) mod 5)", "sizes": fold_sizes, "groups": fold_groups},
    "alarm": {"gap_surface": gap_s, "gap_test": gap_t, "ratio": ratio, "threshold": ALARM, "fires": bool(fires),
              "ratio_by_test_year": ratio_by_year},
    "M1": {"uses": "T" if (fires and T_SIMPLER) else "C"}, "M2": {"uses": "blend" if fires else "C"},
    "M3": {"uses": "0.5C+0.5T"},
    "M4": {"arms": ELIGIBLE, "surface_mae": m4_surface_mae, "chosen_surface_mae": c_surf_mae},
    "M5": m5, "M5_placebo": m5p, "M6": m6, "M6_placebo": m6p,
    "M6_features": {"n": len(feat_cols), "excluded_target_derived": FIRE_HISTORY, "columns": feat_cols},
    "test_y_read": False,
    "seconds": time.time() - T0, "peak_rss_gb": max(PEAK[0], PROC.memory_info().rss) / 2**30,
}
with open(OUT / "stageA_fire.json", "w") as f:
    json.dump(stage, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
with open(OUT / "stageA.sha256.txt", "w") as f:
    for name in ("method_preds_fire.parquet", "stageA_fire.json"):
        f.write(f"{sha_file(OUT / name)}  {name}\n")
print(f"stage A done in {time.time() - T0:.1f} s; peak RSS {stage['peak_rss_gb']:.2f} GB", flush=True)
