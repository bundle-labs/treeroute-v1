"""Label-free guidance of the tool choice -- CORAL, STAGE A (method predictions). Never reads test labels.

Protocol: D:/treeroute/analysis/guidance/PROTOCOL.txt
  (SHA-256 c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4, checked at start).
Reads (read-only): the coral headline run (inner_preds.parquet, inner_candidates.csv, adoption.json, verdict.json,
plan.json, derived.json; test_preds.parquet ONLY key columns + 'arm__' columns, never 'y'), the coral package
catalog.yaml + ban.yaml (feature list, same rule as adv_validation/coral/stage_a.py:175-210), and the coral store
lead_0.parquet (row_id + feature columns only; never pct_bleached, programme or mark).
Writes only under D:/treeroute/analysis/guidance/coral/.
"""
import hashlib
import json
import os
import sys
import time as _time
import warnings

import numpy as np
import pandas as pd
import psutil
import yaml
from scipy import sparse
from scipy.optimize import linprog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

T0 = _time.time()
OUT = "D:/treeroute/analysis/guidance/coral"
RUN = "D:/treeroute/runs/coral/headline/20261020_f3b8e3da"
PKG = "C:/Users/<user>/Desktop/data set for reserch paper/engine/datasets/coral"
STORE = "D:/treeroute/coral_build/coral_store/20261020_014201/lead_0.parquet"
PROTOCOL = "D:/treeroute/analysis/guidance/PROTOCOL.txt"
PROTOCOL_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"

K = 5
CAP_ROWS = 50_000
ALARM = 2.0
CHOSEN = "arcsine_corrector_gls"            # verdict.json:2, run.log:141
TWIN = "arcsine_corrector_unweighted"       # PROTOCOL.txt section 2
TWIN_SIMPLER = True                         # gls -> unweighted
ADOPTED = (100.0, 1.0)                      # adoption.json "penalty"; run.log:141
BASE = "base__donor_median"                 # decision baseline (owner ruling V1, decide.py:468)

LOG = []


def log(msg):
    line = "[%7.1fs] %s" % (_time.time() - T0, msg)
    print(line, flush=True)
    LOG.append(line)


def sha1_int(s):
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def arm_name(d):
    return "%s_%s_%s" % (d["link"], d["tool"], d["weighting"])


def col_at(arm, pt):
    return "%s@level=%s,ratio=%s" % (arm, repr(pt[0]), repr(pt[1]))


# ------------------------------------------------------------------ protocol hash
got = sha256_file(PROTOCOL)
if got != PROTOCOL_SHA:
    sys.exit("PROTOCOL.txt hash mismatch: %s" % got)
log("protocol hash OK %s" % got)

# ------------------------------------------------------------------ run files
adoption = json.load(open(os.path.join(RUN, "adoption.json"), encoding="utf-8"))
verdict = json.load(open(os.path.join(RUN, "verdict.json"), encoding="utf-8"))
assert verdict["adopted"] == CHOSEN
assert arm_name(adoption["adopted"]) == CHOSEN
assert (adoption["penalty"]["level"], adoption["penalty"]["ratio"]) == ADOPTED
ELIG = [arm_name(e) for e in adoption["eligible"]]
ORDER = adoption["decision"]["candidate_order"]
ELIG = [a for a in ORDER if a in ELIG]                       # candidate order
assert len(ELIG) == 12 and CHOSEN in ELIG and TWIN in ELIG
cands = pd.read_csv(os.path.join(RUN, "inner_candidates.csv"))
inner = pd.read_parquet(os.path.join(RUN, "inner_preds.parquet"))
n_s = len(inner)
y_s = inner["y"].to_numpy(float)
assert np.isfinite(y_s).all()
unit_s = inner["unit"].astype(str).to_numpy()
time_s = inner["time"].to_numpy(np.int64)

# ------------------------------------------------------------------ G1
def surf_mae(col):
    return float(np.mean(np.abs(y_s - inner[col].to_numpy(float))))     # decide.py:155


g1 = {"checks": [], "pass": True}
own_pick = {}
for arm in ELIG:
    sub = cands[cands["arm"] == arm].reset_index(drop=True)
    best = 0
    for k in range(1, len(sub)):
        if sub.loc[k, "mae"] < sub.loc[best, "mae"]:
            best = k
    pt = (float(sub.loc[best, "level"]), float(sub.loc[best, "ratio"]))
    own_pick[arm] = {"point": pt, "csv_mae": float(sub.loc[best, "mae"])}
    mine = surf_mae(col_at(arm, pt))
    rel = abs(mine - own_pick[arm]["csv_mae"]) / abs(own_pick[arm]["csv_mae"])
    ok = rel <= 1e-9
    g1["checks"].append({"arm": arm, "own_point": pt, "mae": mine, "csv": own_pick[arm]["csv_mae"], "rel": rel,
                         "ok": ok})
    g1["pass"] &= ok
row = cands[(cands["arm"] == CHOSEN) & (cands["level"] == ADOPTED[0]) & (cands["ratio"] == ADOPTED[1])]
chosen_surf = surf_mae(col_at(CHOSEN, ADOPTED))
rel = abs(chosen_surf - float(row["mae"].iloc[0])) / float(row["mae"].iloc[0])
g1["chosen_at_adopted"] = {"mae": chosen_surf, "csv": float(row["mae"].iloc[0]), "rel": rel}
g1["pass"] &= rel <= 1e-9
base_mae = float(cands.loc[cands["arm"] == BASE, "mae"].iloc[0])
# N2 against the donor median for every tree arm (own picked point)
recomputed = []
for arm in ORDER:
    sub = cands[cands["arm"] == arm]
    if "trees_off" in arm or len(sub) == 0:
        continue
    if float(sub["mae"].min()) < base_mae:
        recomputed.append(arm)
g1["eligible_recomputed"] = recomputed
g1["eligible_adoption"] = ELIG
g1["donor_median_mae"] = base_mae
g1["pass"] &= recomputed == ELIG
log("G1 pass=%s chosen surface MAE %.9f (csv %.9f); eligible %d" % (g1["pass"], chosen_surf,
                                                                    g1["chosen_at_adopted"]["csv"], len(ELIG)))
if not g1["pass"]:
    json.dump(g1, open(os.path.join(OUT, "G1_fail.json"), "w"), indent=1, default=float)
    sys.exit("G1 failed -> coral not run")
point_flag = [{"arm": a, "own_pick": own_pick[a]["point"], "used": ADOPTED}
              for a in ELIG if own_pick[a]["point"] != ADOPTED]
log("point flag (arm used at the adopted point although its own pick differs): %s" % point_flag)

# ------------------------------------------------------------------ test inputs (never y)
KEYS = ["unit", "group", "time", "year", "issue"]
tcols = KEYS + ["arm__%s" % a for a in ELIG]
test = pd.read_parquet(os.path.join(RUN, "test_preds.parquet"), columns=tcols)
assert "y" not in test.columns
n_t = len(test)
unit_t = test["unit"].astype(str).to_numpy()
time_t = test["time"].to_numpy(np.int64)
year_t = test["year"].to_numpy(int)
PS = np.column_stack([inner[col_at(a, ADOPTED)].to_numpy(float) for a in ELIG])     # surface, adopted point
PT = np.column_stack([test["arm__%s" % a].to_numpy(float) for a in ELIG])          # test, adopted point
iC, iT = ELIG.index(CHOSEN), ELIG.index(TWIN)
C_s, T_s = PS[:, iC], PS[:, iT]
C_t, T_t = PT[:, iC], PT[:, iT]
assert np.isfinite(PS).all()
log("test rows %d; finite C %d, finite T %d, all arms finite %d" % (
    n_t, np.isfinite(C_t).sum(), np.isfinite(T_t).sum(), np.isfinite(PT).all(axis=1).sum()))

# ------------------------------------------------------------------ M1 / M2 / M3
gap_s = float(np.mean(np.abs(C_s - T_s)))
ok_t = np.isfinite(C_t) & np.isfinite(T_t)
gap_t = float(np.mean(np.abs(C_t[ok_t] - T_t[ok_t])))
ratio = gap_t / gap_s
fires = ratio > ALARM
ratio_by_year = {int(Y): float(np.mean(np.abs(C_t[ok_t & (year_t == Y)] - T_t[ok_t & (year_t == Y)])) / gap_s)
                 for Y in sorted(set(year_t))}
log("alarm: gap surface %.6f, gap test %.6f, ratio %.4f -> fires %s; per year %s"
    % (gap_s, gap_t, ratio, fires, ratio_by_year))
blend = 0.5 * C_t + 0.5 * T_t
M1 = T_t.copy() if (fires and TWIN_SIMPLER) else C_t.copy()
M2 = blend.copy() if fires else C_t.copy()
M3 = blend.copy()

# ------------------------------------------------------------------ M4
M4 = PT.mean(axis=1)
M4_surface_mae = float(np.mean(np.abs(y_s - PS.mean(axis=1))))
log("M4 equal-weight %d arms: surface MAE %.6f (beside)" % (len(ELIG), M4_surface_mae))

# ------------------------------------------------------------------ folds, cap, placebo order
site_s = np.array([u.split("|")[0] for u in unit_s])
fold_s = np.array([sha1_int(s) % K for s in site_s])
hkey_s = np.array([sha1_int("%s|%s" % (u, t)) for u, t in zip(unit_s, time_s)], dtype=object)
hkey_p = np.array([sha1_int("placebo|%s|%s" % (u, t)) for u, t in zip(unit_s, time_s)], dtype=object)
ord_a = np.array(sorted(range(n_s), key=lambda i: hkey_s[i]))
ord_b = np.array(sorted(range(n_s), key=lambda i: hkey_p[i]))
PERM = np.empty(n_s, dtype=int)
PERM[ord_a] = ord_b                     # row a[k] receives row b[k]
log("sites %d; fold sizes %s; placebo moves %d of %d rows" % (
    len(set(site_s)), np.bincount(fold_s).tolist(), int(np.sum(PERM != np.arange(n_s))), n_s))


def cap(idx):
    idx = np.asarray(idx)
    if len(idx) <= CAP_ROWS:
        return idx
    keep = sorted(idx, key=lambda i: hkey_s[i])[:CAP_ROWS]
    return np.array(sorted(keep))


# ------------------------------------------------------------------ M5 exact LP
def lp_weights(P, y):
    n, m = P.shape
    Ps = sparse.csr_matrix(P)
    I = sparse.identity(n, format="csr")
    A_ub = sparse.vstack([sparse.hstack([-Ps, -I]), sparse.hstack([Ps, -I])], format="csr")
    b_ub = np.r_[-y, y]
    A_eq = sparse.csr_matrix(np.r_[np.ones(m), np.zeros(n)][None, :])
    c = np.r_[np.zeros(m), np.ones(n)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0],
                  bounds=[(0, None)] * (m + n), method="highs")
    if res.status != 0:
        raise RuntimeError("linprog failed: %s" % res.message)
    w = res.x[:m].copy()
    w[w < 1e-9] = 0.0
    w = w / w.sum()
    return w, float(res.fun) / n


def m5(y):
    oof = np.full(n_s, np.nan)
    fold_w = {}
    for k in range(K):
        tr = cap(np.where(fold_s != k)[0])
        w, _ = lp_weights(PS[tr], y[tr])
        fold_w[k] = w.tolist()
        te = fold_s == k
        oof[te] = PS[te] @ w
    cf = float(np.mean(np.abs(y - oof)))
    full = cap(np.arange(n_s))
    w_all, obj = lp_weights(PS[full], y[full])
    return {"cf_mae": cf, "fold_weights": fold_w, "weights": w_all.tolist(), "lp_objective_mae": obj,
            "surface_mae_full_fit": float(np.mean(np.abs(y - PS @ w_all)))}


m5r = m5(y_s)
m5r["chosen_surface_mae"] = chosen_surf
m5r["gate_pass"] = m5r["cf_mae"] < chosen_surf
M5raw = PT @ np.array(m5r["weights"])
M5 = M5raw.copy() if m5r["gate_pass"] else C_t.copy()
m5r["flag"] = None if m5r["gate_pass"] else "FALLBACK:CF"
log("M5: CF-MAE %.6f vs chosen %.6f -> gate %s; weights %s" % (
    m5r["cf_mae"], chosen_surf, m5r["gate_pass"],
    {a: round(w, 4) for a, w in zip(ELIG, m5r["weights"]) if w > 0}))

y_pl = y_s[PERM]                         # y_placebo[a[k]] = y[b[k]]
m5p = m5(y_pl)
chosen_surf_pl = float(np.mean(np.abs(y_pl - C_s)))
m5p["chosen_surface_mae_on_y_placebo"] = chosen_surf_pl
m5p["gate_pass"] = m5p["cf_mae"] < chosen_surf_pl
M5plac = PT @ np.array(m5p["weights"])
M5plac_gated = M5plac.copy() if m5p["gate_pass"] else C_t.copy()
log("M5 placebo: CF-MAE %.6f vs chosen-on-y_placebo %.6f -> gate %s; weights %s" % (
    m5p["cf_mae"], chosen_surf_pl, m5p["gate_pass"],
    {a: round(w, 4) for a, w in zip(ELIG, m5p["weights"]) if w > 0}))

# ------------------------------------------------------------------ M6 features
cat = yaml.safe_load(open(os.path.join(PKG, "catalog.yaml"), encoding="utf-8"))["columns"]
ban = yaml.safe_load(open(os.path.join(PKG, "ban.yaml"), encoding="utf-8"))["verdicts"]
tree = [c for c, v in cat.items() if v["role"] in ("driver", "engineered")
        and ban[c]["verdict"] not in ("ban", "conditional")]          # engine io/apply.py:58 LEAVE
plan = json.load(open(os.path.join(RUN, "plan.json")))
derived = json.load(open(os.path.join(RUN, "derived.json")))
ctx = list(derived["R14"]["inputs"]["context_columns"])
assert ctx == plan["context"] == ["ctx_month", "ctx_doy_sin", "ctx_doy_cos", "ctx_abslat", "ctx_mmm"]
assert len(tree) == plan["tree_features"] == 63
FEATS = tree + ctx
for bad in ("pct_bleached", "programme", "mark"):
    assert bad not in FEATS
store = pd.read_parquet(STORE, columns=["row_id"] + FEATS)
assert store["row_id"].is_unique
store = store.set_index("row_id")
G3 = {"surface_joined": float(pd.Series(unit_s).isin(store.index).mean()),
      "test_joined": float(pd.Series(unit_t).isin(store.index).mean())}
G3["pass"] = G3["surface_joined"] == 1.0 and G3["test_joined"] == 1.0
log("G3 %s; features %d (63 tree + 5 context)" % (G3, len(FEATS)))
XS = store.loc[unit_s, FEATS].to_numpy(float)
XT = store.loc[unit_t, FEATS].to_numpy(float)
del store

# ------------------------------------------------------------------ M6 chooser
eC = np.abs(y_s - C_s)
eT = np.abs(y_s - T_s)
z = np.full(n_s, -1)
z[eT < eC] = 1
z[eC < eT] = 0
nontie = z >= 0


def prep_fit(X):
    miss = np.isnan(X).mean(axis=0)
    const = np.array([np.unique(c[~np.isnan(c)]).size <= 1 for c in X.T])
    keep = ~((miss > 0.5) | const)
    A = X[:, keep]
    med = np.nanmedian(A, axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    A = np.where(np.isnan(A), med, A)
    mu = A.mean(axis=0)
    sd = A.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)

    def tf(B):
        B = B[:, keep]
        B = np.where(np.isnan(B), med, B)
        return np.clip((B - mu) / sd, -10, 10)
    return tf, keep


def fit_lr(X, yz):
    tf, keep = prep_fit(X)
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        m = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, class_weight=None,
                               fit_intercept=True)
        m.fit(tf(X), yz)
    return m, tf, keep, sorted({"%s: %s" % (w.category.__name__, str(w.message)[:120]) for w in wl})


def m6(X):
    """Cross-fitted chooser on non-tie surface rows of feature matrix X; full fit -> test p on XT."""
    idx_nt = np.where(nontie)[0]
    n1 = int(np.sum(z[idx_nt] == 1))
    n0 = int(np.sum(z[idx_nt] == 0))
    oof = np.full(n_s, np.nan)
    warn = set()
    dropped = {}
    for k in range(K):
        tr = cap(idx_nt[fold_s[idx_nt] != k])
        m, tf, keep, wl = fit_lr(X[tr], z[tr])
        warn |= set(wl)
        dropped[k] = [FEATS[j] for j in range(len(FEATS)) if not keep[j]]
        te = idx_nt[fold_s[idx_nt] == k]
        oof[te] = m.predict_proba(tf(X[te]))[:, 1]
    acc = float(np.mean((oof[idx_nt] > 0.5) == (z[idx_nt] == 1)))
    auc = float(roc_auc_score(z[idx_nt], oof[idx_nt]))
    base_rate = float(np.mean(z[idx_nt] == 1))
    full = cap(idx_nt)
    m, tf, keep, wl = fit_lr(X[full], z[full])
    warn |= set(wl)
    p_t = m.predict_proba(tf(XT))[:, 1]
    coef = np.zeros(len(FEATS))
    coef[keep] = m.coef_[0]
    top = [{"feature": FEATS[j], "coef": float(coef[j])} for j in np.argsort(-np.abs(coef))[:10]]
    if len(idx_nt) < 200 or n1 < 20 or n0 < 20:
        flag = "FALLBACK:ROWS"
    elif acc < 0.55:
        flag = "FALLBACK:ACC"
    else:
        flag = None
    hard = np.where(p_t > 0.5, T_t, C_t)
    soft = (1 - p_t) * C_t + p_t * T_t
    diag = {"n_nontie": int(len(idx_nt)), "n_ties": int(n_s - len(idx_nt)), "n_twin_wins": n1, "n_chosen_wins": n0,
            "cf_accuracy": acc, "base_rate_twin_wins": base_rate, "majority_rate": max(base_rate, 1 - base_rate),
            "cf_auc": auc, "flag": flag, "test_share_switched_to_twin": float(np.mean(p_t > 0.5)),
            "test_mean_p": float(np.mean(p_t)), "test_p_quantiles": np.quantile(p_t, [0, .1, .5, .9, 1]).tolist(),
            "full_fit_dropped_columns": [FEATS[j] for j in range(len(FEATS)) if not keep[j]],
            "fold_dropped_columns": dropped, "top10_coef_full_fit": top, "fit_warnings": sorted(warn)}
    return hard, soft, p_t, diag


if G3["pass"]:
    M6raw, M6sraw, p6, d6 = m6(XS)
    M6 = M6raw.copy() if d6["flag"] is None else C_t.copy()
    M6s = M6sraw.copy() if d6["flag"] is None else C_t.copy()
    log("M6: non-tie %d (twin wins %d), CF ACC %.4f (base %.4f) AUC %.4f -> %s; test switched %.3f mean p %.3f" % (
        d6["n_nontie"], d6["n_twin_wins"], d6["cf_accuracy"], d6["base_rate_twin_wins"], d6["cf_auc"],
        d6["flag"] or "APPLIED", d6["test_share_switched_to_twin"], d6["test_mean_p"]))
    XS_pl = XS[PERM]                       # feature row of b[k] given to row a[k]
    M6pl_raw, M6spl_raw, p6pl, d6pl = m6(XS_pl)
    M6pl_gated = M6pl_raw.copy() if d6pl["flag"] is None else C_t.copy()
    M6spl_gated = M6spl_raw.copy() if d6pl["flag"] is None else C_t.copy()
    log("M6 placebo: CF ACC %.4f AUC %.4f -> %s; test switched %.3f mean p %.3f" % (
        d6pl["cf_accuracy"], d6pl["cf_auc"], d6pl["flag"] or "APPLIED", d6pl["test_share_switched_to_twin"],
        d6pl["test_mean_p"]))
else:
    log("G3 failed -> M6 not run")
    d6 = d6pl = {"flag": "NOT RUN (G3)"}
    M6 = M6s = M6raw = M6sraw = M6pl_raw = M6spl_raw = M6pl_gated = M6spl_gated = p6 = p6pl = np.full(n_t, np.nan)

# ------------------------------------------------------------------ write stage A
preds = pd.DataFrame({"unit": unit_t, "time": time_t, "year": year_t,
                      "C": C_t, "T": T_t,
                      "M1": M1, "M2": M2, "M3": M3, "M4": M4,
                      "M5": M5, "M5raw": M5raw, "M5_placebo": M5plac, "M5_placebo_gated": M5plac_gated,
                      "M6": M6, "M6s": M6s, "M6raw": M6raw, "M6sraw": M6sraw, "M6_p": p6,
                      "M6_placebo": M6pl_raw, "M6s_placebo": M6spl_raw,
                      "M6_placebo_gated": M6pl_gated, "M6s_placebo_gated": M6spl_gated, "M6_placebo_p": p6pl})
pp = os.path.join(OUT, "method_preds_coral.parquet")
preds.to_parquet(pp, index=False)
stage = {"protocol_sha256": PROTOCOL_SHA, "problem": "coral", "run": RUN, "chosen": CHOSEN, "twin": TWIN,
         "twin_simpler": TWIN_SIMPLER, "adopted_point": ADOPTED, "eligible": ELIG,
         "gates": {"G1": g1, "G3": G3, "G4": "stage A read test_preds columns %s only (no 'y'); store read without "
                                              "pct_bleached, programme, mark" % tcols},
         "point_flag": point_flag,
         "alarm": {"gap_surface": gap_s, "gap_test": gap_t, "ratio": ratio, "threshold": ALARM, "fires": bool(fires),
                   "ratio_by_test_year": ratio_by_year, "n_test_rows_gap": int(ok_t.sum())},
         "M1": {"uses": "twin" if (fires and TWIN_SIMPLER) else "chosen"},
         "M2": {"uses": "blend 0.5/0.5" if fires else "chosen"},
         "M4": {"n_arms": len(ELIG), "surface_mae_beside": M4_surface_mae},
         "M5": m5r, "M5_placebo": m5p, "M6": d6, "M6_placebo": d6pl,
         "features": {"n": len(FEATS), "tree": tree, "context": ctx,
                      "folds": "K=5 by reef SITE (unit before '|'), sha1(site) mod 5", "n_sites": int(len(set(site_s)))},
         "stage_a_seconds": round(_time.time() - T0, 2),
         "stage_a_peak_ram_mb": round(psutil.Process().memory_info().peak_wset / 2 ** 20, 1)}
sj = os.path.join(OUT, "stageA_coral.json")
with open(sj, "w", encoding="utf-8") as f:
    json.dump(stage, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))
with open(os.path.join(OUT, "stage_a.log"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
with open(os.path.join(OUT, "stageA.sha256.txt"), "w") as f:
    for p in (pp, sj, os.path.join(OUT, "stage_a.log")):
        f.write("%s *%s\n" % (sha256_file(p), os.path.basename(p)))
log("stage A written (%.1f s, peak RAM %.0f MB); SHA-256 in stageA.sha256.txt BEFORE any test label is opened"
    % (stage["stage_a_seconds"], stage["stage_a_peak_ram_mb"]))
