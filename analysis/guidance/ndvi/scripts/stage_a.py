"""Label-free guidance of the tool choice, NDVI, STAGE A (PROTOCOL.txt sha256 c51fc39a...).
Gates G1 and G3; builds M1-M6 (+ M6s) and the M5 / M6 / M6s placebos on test rows.
Never reads test_preds 'y' (G4): test_preds is read with the key columns and the 'arm__' columns only.
Writes ndvi/method_preds_ndvi.parquet, ndvi/stageA_ndvi.json, ndvi/stageA.sha256.txt.
"""
import hashlib, json, time
import numpy as np, pandas as pd, pyarrow.parquet as pq, psutil
import scipy.sparse as sp
from scipy.optimize import linprog
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

T0 = time.time()
PROTO = "D:/treeroute/analysis/guidance/PROTOCOL.txt"
PROTO_SHA = "c51fc39ad390204de8894fd3b50cd4f9cf0fc70a92eddf99214497fb6201eef4"
assert hashlib.sha256(open(PROTO, "rb").read()).hexdigest() == PROTO_SHA, "protocol hash mismatch"
RUN = "D:/treeroute/runs/ndvi/headline/20261016_d1de3158"
FEAT_DIR = "D:/treeroute/analysis/adv_validation/ndvi"   # read-only
OUT = "D:/treeroute/analysis/guidance/ndvi"
LEVEL, RATIO = 1.0, 0.0625                                  # adoption.json:221; run.log:754
SUF = "@level=%r,ratio=%r" % (LEVEL, RATIO)
CHOSEN = "identity_plain_unweighted"                        # verdict.json:2
TWIN = "identity_plain_gls"                                 # PROTOCOL section 2 (weighting twin)
TWIN_SIMPLER = False                                        # twin is gls, chosen unweighted -> not simpler
ELIG = ["identity_plain_unweighted", "identity_plain_gls",
        "identity_corrector_unweighted", "identity_corrector_gls"]  # adoption.json:193 candidate_order; run.log:754
OFF = "identity_trees_off_unweighted"
CAP, K, ALARM = 50000, 5, 2.0
proc = psutil.Process()


def sha_int(s):
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)


def peak_gib():
    mi = proc.memory_info()
    return getattr(mi, "peak_wset", mi.rss) / 2 ** 30


# ---------------- surface ----------------
cand = pd.read_csv(f"{RUN}/inner_candidates.csv")
sch = pq.read_schema(f"{RUN}/inner_preds.parquet").names
pred_cols = [c for c in sch if not c.startswith("pre__") and c not in ("unit", "group", "time", "y")]
S = pq.read_table(f"{RUN}/inner_preds.parquet", columns=["unit", "group", "time", "y"] + pred_cols).to_pandas()
n = len(S)
y = S["y"].to_numpy(float)
assert np.isfinite(y).all()

# ---------------- G1 ----------------
g1_rel = 0.0
own = {}
for _, r in cand.iterrows():
    col = OFF if r["arm"] == OFF else "%s@level=%r,ratio=%r" % (r["arm"], float(r["level"]), float(r["ratio"]))
    m = float(np.mean(np.abs(y - S[col].to_numpy(float))))
    g1_rel = max(g1_rel, abs(m - r["mae"]) / abs(r["mae"]))
    if r["arm"] != OFF:
        if r["arm"] not in own or m < own[r["arm"]][2]:
            own[r["arm"]] = (float(r["level"]), float(r["ratio"]), m)
off_mae = float(np.mean(np.abs(y - S[OFF].to_numpy(float))))
elig_re = [a for a in own if own[a][2] < off_mae]        # N2, decide.py:290-299 and :460 (strict)
chosen_surf = float(np.mean(np.abs(y - S[CHOSEN + SUF].to_numpy(float))))
cand_chosen = float(cand[(cand.arm == CHOSEN) & (cand.level == LEVEL) & (cand.ratio == RATIO)]["mae"].iloc[0])
G1 = {"chosen_surface_mae": chosen_surf, "inner_candidates_value": cand_chosen,
      "max_rel_diff_all_candidates": g1_rel, "own_picks": {a: list(v) for a, v in own.items()},
      "trees_off_mae": off_mae, "eligible_recomputed": elig_re}
G1["pass"] = (abs(chosen_surf - cand_chosen) / cand_chosen <= 1e-9 and g1_rel <= 1e-9 and elig_re == ELIG)
print("G1", G1, flush=True)
assert G1["pass"], "G1 failed"
point_flags = [a for a in ELIG if (own[a][0], own[a][1]) != (LEVEL, RATIO)]

PS = {a: S[a + SUF].to_numpy(float) for a in ELIG}
for a in ELIG:
    assert np.isfinite(PS[a]).all()
s_unit = S["unit"].to_numpy(); s_time = S["time"].to_numpy(); s_group = S["group"].astype(str).to_numpy()
del S
CS, TS = PS[CHOSEN], PS[TWIN]

# ---------------- test (NO y) ----------------
tcols = ["unit", "group", "time", "year", "issue"] + ["arm__" + a for a in ELIG]
assert "y" not in tcols
T = pq.read_table(f"{RUN}/test_preds.parquet", columns=tcols).to_pandas()
assert (T["time"] == T["issue"]).all()
PT = {a: T["arm__" + a].to_numpy(float) for a in ELIG}
CT, TT = PT[CHOSEN], PT[TWIN]
t_year = T["year"].to_numpy()

# ---------------- M1 / M2 / M3 ----------------
gap_s = float(np.mean(np.abs(CS - TS)))
ft = np.isfinite(CT) & np.isfinite(TT)
gap_t = float(np.mean(np.abs(CT[ft] - TT[ft])))
ratio = gap_t / gap_s
fires = ratio > ALARM
ratio_by_year = {int(yr): float(np.mean(np.abs(CT[ft & (t_year == yr)] - TT[ft & (t_year == yr)]))) / gap_s
                 for yr in sorted(np.unique(t_year))}
M = {}
M["M1"] = TT.copy() if (fires and TWIN_SIMPLER) else CT.copy()
M["M2"] = 0.5 * CT + 0.5 * TT if fires else CT.copy()
M["M3"] = 0.5 * CT + 0.5 * TT
print("alarm ratio %.4f fires=%s" % (ratio, fires), ratio_by_year, flush=True)

# ---------------- M4 ----------------
M["M4"] = np.mean([PT[a] for a in ELIG], axis=0)
m4_surf = float(np.mean(np.abs(y - np.mean([PS[a] for a in ELIG], axis=0))))

# ---------------- folds, cap, placebo permutation ----------------
fold_of_group = {g: sha_int(g) % K for g in np.unique(s_group)}
s_fold = np.array([fold_of_group[g] for g in s_group])
s_key = np.array([sha_int("%s|%s" % (u, str(int(t)))) for u, t in zip(s_unit, s_time)], dtype=object)
s_keyb = np.array([sha_int("placebo|%s|%s" % (u, str(int(t)))) for u, t in zip(s_unit, s_time)], dtype=object)
ord_a = np.array(sorted(range(n), key=lambda i: s_key[i]))
ord_b = np.array(sorted(range(n), key=lambda i: s_keyb[i]))
rank_a = np.empty(n, dtype=np.int64); rank_a[ord_a] = np.arange(n)


def cap_idx(idx):
    """keep the CAP rows with the lowest sha1(unit|time) among idx (no seeds)."""
    if len(idx) <= CAP:
        return np.sort(idx)
    return np.sort(idx[np.argsort(rank_a[idx], kind="stable")[:CAP]])


# ---------------- M5 ----------------
PSm = np.column_stack([PS[a] for a in ELIG])
PTm = np.column_stack([PT[a] for a in ELIG])
m = PSm.shape[1]


def lp_weights(idx, yy):
    idx = cap_idx(idx)
    P = PSm[idx]; yv = yy[idx]; nn = len(idx)
    c = np.concatenate([np.zeros(m), np.ones(nn)])
    I = sp.identity(nn, format="csr")
    A_ub = sp.vstack([sp.hstack([sp.csr_matrix(-P), -I]), sp.hstack([sp.csr_matrix(P), -I])], format="csr")
    b_ub = np.concatenate([-yv, yv])
    A_eq = sp.csr_matrix(np.concatenate([np.ones(m), np.zeros(nn)])[None, :])
    bounds = [(0, None)] * m + [(None, None)] * nn
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0], bounds=bounds, method="highs")
    assert res.status == 0, res.message
    w = res.x[:m].copy(); w[w < 1e-9] = 0.0; w = w / w.sum()
    return w, len(idx)


def m5_run(yy):
    oof = np.empty(n); fold_w = {}
    for k in range(K):
        tr = np.where(s_fold != k)[0]; te = np.where(s_fold == k)[0]
        w, ntr = lp_weights(tr, yy)
        oof[te] = PSm[te] @ w
        fold_w[k] = {"w": dict(zip(ELIG, w.tolist())), "train_rows": ntr, "test_rows": len(te)}
    cf = float(np.mean(np.abs(yy - oof)))
    w_full, nfull = lp_weights(np.arange(n), yy)
    return cf, fold_w, w_full, nfull


t5 = time.time()
cf5, fw5, w5, n5 = m5_run(y)
M["M5raw"] = PTm @ w5
gate5 = cf5 < chosen_surf
M["M5"] = M["M5raw"].copy() if gate5 else CT.copy()
y_pl = np.empty(n); y_pl[ord_a] = y[ord_b]
cf5p, fw5p, w5p, _ = m5_run(y_pl)
chosen_surf_pl = float(np.mean(np.abs(y_pl - CS)))
M["M5_placebo"] = PTm @ w5p
gate5p = cf5p < chosen_surf_pl
M["M5_placebo_gated"] = M["M5_placebo"].copy() if gate5p else CT.copy()
print("M5 cf %.6f vs chosen %.6f gate=%s w=%s (%.0fs)" % (cf5, chosen_surf, gate5, w5, time.time() - t5), flush=True)
print("M5 placebo cf %.6f vs chosen-on-placebo %.6f w=%s" % (cf5p, chosen_surf_pl, w5p), flush=True)

# ---------------- M6 features + G3 ----------------
meta = json.load(open(f"{FEAT_DIR}/features_ndvi_meta.json"))
FEATS = meta["context"] + meta["first20"]                   # 9 + 20 = 29, the fixed fallback subset
assert len(FEATS) == 29
F = pd.read_parquet(f"{FEAT_DIR}/features_ndvi.parquet", columns=["unit", "step"] + FEATS).rename(columns={"step": "time"})
Sx = pd.DataFrame({"unit": s_unit, "time": s_time}).merge(F, on=["unit", "time"], how="left", indicator=True)
Tx = T[["unit", "issue"]].rename(columns={"issue": "time"}).merge(F, on=["unit", "time"], how="left", indicator=True)
assert len(Sx) == n and len(Tx) == len(T)
G3 = {"surface_joined": int((Sx["_merge"] == "both").sum()), "surface_rows": n,
      "test_joined": int((Tx["_merge"] == "both").sum()), "test_rows": len(T)}
G3["pass"] = G3["surface_joined"] == n and G3["test_joined"] == len(T)
print("G3", G3, flush=True)
XS = Sx[FEATS].to_numpy(float); XT = Tx[FEATS].to_numpy(float)
del F, Sx, Tx

eC = np.abs(y - CS); eT = np.abs(y - TS)
z = np.full(n, -1, dtype=np.int8); z[eT < eC] = 1; z[eC < eT] = 0
nontie = np.where(z >= 0)[0]


def prep_fit(X):
    keep, med, mu, sd = [], [], [], []
    for j in range(X.shape[1]):
        col = X[:, j]; fin = np.isfinite(col)
        if fin.mean() < 0.5:   # > 50% missing
            continue
        v = col[fin]
        if v.size == 0 or v.max() == v.min():
            continue
        md = float(np.median(v)); filled = np.where(fin, col, md)
        s = float(filled.std())
        if s == 0:
            continue
        keep.append(j); med.append(md); mu.append(float(filled.mean())); sd.append(s)
    return np.array(keep, dtype=int), np.array(med), np.array(mu), np.array(sd)


def prep_apply(X, st):
    keep, med, mu, sd = st
    Z = X[:, keep].copy()
    bad = ~np.isfinite(Z)
    Z[bad] = np.broadcast_to(med, Z.shape)[bad]
    return np.clip((Z - mu) / sd, -10, 10)


def fit_lr(X, idx):
    idx = cap_idx(idx)
    st = prep_fit(X[idx])
    lr = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=2000, class_weight=None, fit_intercept=True)
    lr.fit(prep_apply(X[idx], st), z[idx])
    return lr, st, len(idx)


def m6_run(X):
    """cross-fit on non-tie rows; returns diagnostics and test p (ungated) from a full fit."""
    oof = np.full(n, np.nan); fold_info = {}
    for k in range(K):
        tr = nontie[s_fold[nontie] != k]; te = nontie[s_fold[nontie] == k]
        lr, st, ntr = fit_lr(X, tr)
        oof[te] = lr.predict_proba(prep_apply(X[te], st))[:, 1]
        fold_info[k] = {"train_rows": ntr, "test_rows": int(len(te)), "kept_cols": int(len(st[0]))}
    zz = z[nontie]; pp = oof[nontie]
    acc = float(np.mean((pp > 0.5) == (zz == 1)))
    auc = float(roc_auc_score(zz, pp))
    lr, st, nfull = fit_lr(X, nontie)
    pt = lr.predict_proba(prep_apply(XT, st))[:, 1]
    return {"acc": acc, "auc": auc, "base_rate": float(np.mean(zz == 1)), "folds": fold_info,
            "full_train_rows": nfull, "kept_cols": int(len(st[0])),
            "kept_names": [FEATS[j] for j in st[0]]}, pt


n1 = int((z == 1).sum()); n0 = int((z == 0).sum())
rows_ok = len(nontie) >= 200 and n1 >= 20 and n0 >= 20
d6 = {"nontie": int(len(nontie)), "ties": int(n - len(nontie)), "class1_twin_wins": n1, "class0_chosen_wins": n0}
d6p = {}
if G3["pass"] and rows_ok:
    t6 = time.time()
    info, p6 = m6_run(XS)
    d6.update(info)
    fb6 = None if info["acc"] >= 0.55 else "FALLBACK:ACC"
    XSp = np.empty_like(XS); XSp[ord_a] = XS[ord_b]          # feature row of b[k] given to row a[k]
    infop, p6p = m6_run(XSp)
    del XSp
    d6p.update(infop)
    fb6p = None if infop["acc"] >= 0.55 else "FALLBACK:ACC"
    ftp = np.isfinite(CT) & np.isfinite(TT)
    M["M6_ungated"] = np.where(p6 > 0.5, TT, CT)
    M["M6s_ungated"] = (1 - p6) * CT + p6 * TT
    M["M6"] = CT.copy() if fb6 else M["M6_ungated"].copy()
    M["M6s"] = CT.copy() if fb6 else M["M6s_ungated"].copy()
    M["M6_placebo"] = np.where(p6p > 0.5, TT, CT)
    M["M6s_placebo"] = (1 - p6p) * CT + p6p * TT
    M["M6_placebo_gated"] = CT.copy() if fb6p else M["M6_placebo"].copy()
    M["M6s_placebo_gated"] = CT.copy() if fb6p else M["M6s_placebo"].copy()
    d6.update({"fallback": fb6, "test_share_switched_to_T": float(np.mean(p6 > 0.5)), "test_mean_p": float(np.mean(p6))})
    d6p.update({"fallback_if_gated": fb6p, "test_share_switched_to_T": float(np.mean(p6p > 0.5)),
                "test_mean_p": float(np.mean(p6p))})
    print("M6 acc %.4f auc %.4f base %.4f fb=%s switched %.4f (%.0fs)" % (
        info["acc"], info["auc"], info["base_rate"], fb6, d6["test_share_switched_to_T"], time.time() - t6), flush=True)
    print("M6 placebo acc %.4f auc %.4f switched %.4f" % (infop["acc"], infop["auc"], d6p["test_share_switched_to_T"]), flush=True)
else:
    fb = "NOT RUN (G3)" if not G3["pass"] else "FALLBACK:ROWS"
    d6["fallback"] = fb
    for k in ["M6", "M6s", "M6_ungated", "M6s_ungated", "M6_placebo", "M6s_placebo", "M6_placebo_gated", "M6s_placebo_gated"]:
        M[k] = CT.copy()

# ---------------- write ----------------
out = pd.DataFrame({"unit": T["unit"].to_numpy(), "time": T["time"].to_numpy(), "year": t_year, "C": CT, "T": TT})
for k, v in M.items():
    out[k] = v
mp = f"{OUT}/method_preds_ndvi.parquet"
out.to_parquet(mp, index=False)
stA = {"protocol_sha256": PROTO_SHA, "run": RUN, "adopted_point": [LEVEL, RATIO], "chosen": CHOSEN, "twin": TWIN,
       "twin_simpler": TWIN_SIMPLER, "twin_eligible": TWIN in ELIG, "eligible": ELIG, "point_flags": point_flags,
       "G1": G1, "G3": G3,
       "alarm": {"gap_surface": gap_s, "gap_test": gap_t, "ratio": ratio, "fires": bool(fires),
                 "ratio_by_year": ratio_by_year, "test_rows_used": int(ft.sum())},
       "M4": {"surface_mae": m4_surf, "chosen_surface_mae": chosen_surf},
       "M5": {"cf_mae": cf5, "chosen_surface_mae": chosen_surf, "applied": bool(gate5),
              "fallback": None if gate5 else "FALLBACK:CF", "full_weights": dict(zip(ELIG, w5.tolist())),
              "full_train_rows": n5, "fold_weights": fw5},
       "M5_placebo": {"cf_mae_on_y_placebo": cf5p, "chosen_surface_mae_on_y_placebo": chosen_surf_pl,
                      "gated_applied": bool(gate5p), "full_weights": dict(zip(ELIG, w5p.tolist())),
                      "fold_weights": fw5p},
       "M6": d6, "M6_placebo": d6p,
       "stage_a_reads_test_y": False, "runtime_s": round(time.time() - T0, 1), "peak_wset_GiB": round(peak_gib(), 3)}
sj = f"{OUT}/stageA_ndvi.json"
json.dump(stA, open(sj, "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
with open(f"{OUT}/stageA.sha256.txt", "w") as fh:
    for p in (mp, sj):
        fh.write("%s  %s\n" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), p.split("/")[-1]))
print("stage A done %.1fs peak %.2f GiB" % (time.time() - T0, peak_gib()), flush=True)
