"""The architecture on coral: per-donor specialists + a LOCALLY-CALIBRATED router, three arms.

    py -3.9 -u coral_architecture.py --quick        # small grid, ~minutes
    py -3.9 -u coral_architecture.py                # full sweep
    py -3.9 -u coral_architecture.py --arms spatial,driver,combined

WHAT IS BUILT, AND WHAT IS DELIBERATELY LEFT OUT.

  IN   Stage 1  one specialist bank per donor region -- trees fitted ONLY on their own region, so the
                bank is a set of regional opinions rather than one pooled model.
  IN   Stage 3  the router: for each test row, select a CALIBRATION NEIGHBOURHOOD and solve a small
                block-penalised ridge over it. This is the only mechanism in the design that can
                express "this reef tolerates heat differently", and it is the thing being tested.
  IN   Stage 5  sigma-hat GLS row weights (swept on/off).

  OUT  correctors  -- a corrector fits the base tree's OUT-OF-BAG residual. With 6,831 donor rows a
                     disjoint half leaves ~3,415, and more importantly the corrector exists to
                     amplify SURGES, which we cannot label yet.
  OUT  gate A / eta -- the surge gate needs a month-on-month jump label. 66% of coral sites are
                     visited once, so that label cannot be computed at all. Severity > 50% is the
                     eventual analogue (base rate 4.18%, close to NDVI's 3.2%), but it is not built
                     here.
  OUT  EVT head   -- tied to the same surge definition.
  These come back once surge/anomaly labels exist. Leaving them out now means a null result is
  attributable to the router rather than smeared across five untested components.

THE THREE ROUTER ARMS. For a test row t, the calibration pool is
    (all donor-region rows)  UNION  (target-region rows STRICTLY EARLIER than t).
The target's own future is never in the pool -- that is the leak guard, and it is why the arms are
evaluated per row rather than per region.

  spatial   rank the pool by great-circle distance to t, take the k nearest.
  driver    rank the pool by Euclidean distance in STANDARDISED driver space, take the k nearest.
  combined  take the 3k spatially nearest, then rank THOSE by driver distance and keep k.

SWEEPS. max_features on the specialist bank (the decorrelation knob -- NDVI's 15-of-528 is 2.8% per
split and does not scale to a 40-column pool), neighbourhood size k, ridge alpha on the tree block,
and GLS on/off. Alpha is swept for every bank size because ridge shrinkage is NOT scale-invariant in
column count -- a fixed alpha silently collapses when the bank changes width.

TARGET is the continuous percent bleached. Ridge on a 0/1 target is a linear probability model; the
continuous target is where a ridge is natural, and the binary is derived from it by thresholding so
both metric families are reported from one fit.
"""
import argparse
import itertools
import os
import re
import sys
import time
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

import numpy as np
import pandas as pd

try:
    from sklearnex import patch_sklearn
    patch_sklearn(verbose=False)
except Exception:
    pass

from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coral_smoke_regress import continuous_target

FEAT = "dhw_features.parquet"
R_EARTH = 6371.0


# ======================================================================================
# THE LINK FUNCTION -- the scale the local ridge is solved on. ONE definition, imported
# everywhere. It lived as a copy-pasted block in seven experiment scripts before this.
#
# WHY IT EXISTS. The target is a percentage: bounded [0, 100] and, on the donor rows the
# ridge actually fits, 37.5% exactly zero and heavily right-skewed. An additive ridge
# assumes an unbounded response, so solved on the raw target it drove 19.9% of test
# predictions NEGATIVE, rescued by a clip -- one prediction in five produced by max(0, .)
# rather than by the model.
#
# `sqrt`, `fourth` and `arcsine` invert through a square or a sine, so their inverse
# CANNOT return a negative number and the low-end clip becomes unreachable rather than
# load-bearing. `arcsine` additionally respects the upper bound of 100 without a clip and
# is the variance-stabilising transform for a proportion: it gives the ends of the scale
# more room than the middle, because a survey reading 2% is measured more precisely than
# one reading 50%.
#
# READ THIS BEFORE QUOTING A GAIN (Part 429). The link is a TRADE, not a free win.
# On the region-blocked split, 115% of its MAE gain sits on the rows whose truth is
# exactly zero; re-weighting the test rows to the donor label mix reduces the gain to
# -0.108 (ns). It is significantly WORSE on rows that actually bleached (+0.451 MAE) and
# on severe rows (+2.287). What survives re-weighting unconditionally is the RANKING
# gain, AUC(y>0) +0.0244, CI [+0.0127, +0.0359], and on the YEAR-blocked split the MAE
# gain survives matching too (-0.353). Quote the ranking gain; quote the MAE gain with
# the test set's zero rate attached.
#
# DEFAULT IS "identity", deliberately. Every driver A/B from Part 417 to Part 423 called
# route() without a link argument, and silently changing what those calls compute would
# invalidate the comparisons they were used for. Pass link="arcsine" explicitly; that is
# what the shipped configuration does.
# ======================================================================================
LINKS = {
    "identity": (lambda y: np.asarray(y, dtype="float64"),
                 lambda p: np.clip(p, 0, 100)),
    "sqrt":     (lambda y: np.sqrt(np.clip(y, 0, None)),
                 lambda p: np.clip(np.clip(p, 0, None) ** 2, 0, 100)),
    "fourth":   (lambda y: np.clip(y, 0, None) ** 0.25,
                 lambda p: np.clip(np.clip(p, 0, None) ** 4, 0, 100)),
    "log1p":    (lambda y: np.log1p(np.clip(y, 0, None)),
                 lambda p: np.clip(np.expm1(np.clip(p, 0, None)), 0, 100)),
    "arcsine":  (lambda y: np.arcsin(np.sqrt(np.clip(y, 0, 100) / 100.0)),
                 lambda p: 100.0 * np.sin(np.clip(p, 0, np.pi / 2)) ** 2),
    # logit needs an epsilon offset: 37.5% of donor rows are exactly zero and logit(0) is -inf.
    # Part 436 measured it as statistically indistinguishable from arcsine on AUC (+0.0031,
    # CI [-0.0026, +0.0090]) while giving up markedly more on the severe tail (46.27 against
    # 43.22). The three links form a monotone series in compression strength and every metric
    # moves with it: y=0 MAE 2.177 -> 1.079 -> 0.760 across identity/arcsine/logit while severe
    # MAE rises 39.75 -> 43.22 -> 46.27. Compression buys the calm rows and sells the severe ones.
    "logit":    (lambda y, _e=0.005: (lambda q: np.log(q) - np.log(1 - q))(
                     np.clip(y, 0, 100) / 100.0 * (1 - 2 * _e) + _e),
                 lambda p, _e=0.005: np.clip(
                     (1.0 / (1.0 + np.exp(-np.clip(p, -30, 30))) - _e) / (1 - 2 * _e) * 100.0,
                     0, 100)),
}


def apply_link(name):
    """Return (forward, inverse) for a named link. Fails loudly on a typo."""
    if name not in LINKS:
        raise KeyError("unknown link %r; known: %s" % (name, sorted(LINKS)))
    return LINKS[name]


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), m), flush=True)


def haversine(lat1, lon1, lat2, lon2):
    p = np.pi / 180.0
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def build_bank(tr, fcols, n_per_donor, max_features, seed=0):
    """One specialist bank per donor region. Each tree sees ONLY its own region's rows."""
    trees, owner = [], []
    for e, g in tr.groupby("eco"):
        Xg = g[fcols].fillna(0).values.astype(np.float32)
        yg = g["y"].values
        n = len(g)
        for j in range(n_per_donor):
            rs = np.random.RandomState(seed * 1000 + int(e) * 17 + j)
            idx = rs.choice(n, size=max(30, int(0.8 * n)), replace=True)   # bagged within the region
            t = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5,
                                      max_features=max_features, random_state=seed * 100 + j)
            t.fit(Xg[idx], yg[idx])
            trees.append(t)
            owner.append(int(e))
    return trees, np.array(owner)


def tree_columns(trees, X, fcols):
    A = np.empty((len(X), len(trees)), np.float32)
    V = X[fcols].fillna(0).values.astype(np.float32)
    for j, t in enumerate(trees):
        A[:, j] = t.predict(V)
    return A


USE_DUAL = True          # set False to force the primal; see solve_local()


def solve_local(Xc, yc, w, ntree, nctx, a_tree, a_ctx):
    """Block-penalised weighted ridge. Intercept and MMM unpenalised; each block trace-normalised on
    its OWN columns -- one shared penalty crushes a 7-column context block against a 50-column tree
    block.

    DISPATCHES TO THE DUAL WHEN k < p, WHICH IS ALWAYS. The primal below forms G = Xc' W Xc, which
    is (p x p) for p = ntree + nctx + 2, and Choleskys it ONCE PER TEST ROW. That is fine at 120 or
    2,500 trees and catastrophic at 10,000: G becomes 10,006^2 = 801 MB and O(p^3) makes it 7.9 s
    per row measured here -- roughly 6 hours for one seed of the full-scale run, which is where the
    2026-08 run stalled. But the ridge is fitted from only k=50 neighbours, so it has an exact dual
    in k-space where G is (50 x 50) regardless of bank width. Measured: predictions agree to
    9.1e-10 (the bar is 1e-9; two identical primal calls already differ by ~2e-13 from threaded BLAS
    reduction order) and it is 463x faster at 10,000 trees, 117x at 2,500.
    """
    if USE_DUAL and Xc.shape[0] < Xc.shape[1]:
        return _solve_local_dual(Xc, yc, w, ntree, nctx, a_tree, a_ctx)
    W = w[:, None]
    G = Xc.T @ (Xc * W)
    rhs = Xc.T @ (yc * w)
    reg = np.zeros(Xc.shape[1])
    o = 2                                            # [intercept, mmm] unpenalised
    if nctx:
        blk = np.arange(o, o + nctx)
        tr_ = float(np.trace(G[np.ix_(blk, blk)])) / max(nctx, 1)
        reg[blk] = a_ctx * tr_
    if ntree:
        blk = np.arange(o + nctx, o + nctx + ntree)
        tr_ = float(np.trace(G[np.ix_(blk, blk)])) / max(ntree, 1)
        reg[blk] = a_tree * tr_
    G.flat[:: G.shape[0] + 1] += reg + 1e-8
    try:
        L = np.linalg.cholesky(G)                    # NOT scipy cho_factor -- 570x slower here
        from scipy.linalg import solve_triangular
        z = solve_triangular(L, rhs, lower=True)
        return solve_triangular(L.T, z, lower=False)
    except Exception:
        return np.linalg.lstsq(G, rhs, rcond=None)[0]


def _solve_local_dual(Xc, yc, w, ntree, nctx, a_tree, a_ctx):
    """k-space form of solve_local. Identical answer, cost independent of bank width.

    THE PENALTY TRACE IS TAKEN ON THE RAW BLOCK, NOT THE PROJECTED ONE, and that is the whole
    subtlety. The primal derives its penalty scale from diag(Xc'W Xc) on the raw columns; taking it
    from the post-projection block instead makes the reference 1,723x smaller on the tree block
    (which carries a large common mean the intercept absorbs), i.e. 41.5x too little shrinkage.
    Both are legitimate ridges but they are different parameterisations of alpha, and every alpha in
    this project is calibrated to the primal's. Mixing them scored 4.878 against the primal's 4.493
    on an identical configuration.
    """
    from scipy.linalg import solve_triangular
    k = Xc.shape[0]
    o = 2                                            # [intercept, mmm] unpenalised
    U, P = Xc[:, :o], Xc[:, o:]
    r = np.sqrt(w)[:, None]
    Us, Ps_, ys = U * r, P * r, yc * np.sqrt(w)
    Q, _ = np.linalg.qr(Us)                          # project the unpenalised block out
    Py = ys - Q @ (Q.T @ ys)
    PP = Ps_ - Q @ (Q.T @ Ps_)
    s = np.empty(P.shape[1])
    if nctx:
        s[:nctx] = np.sqrt(a_ctx * max(float((Ps_[:, :nctx] ** 2).sum()) / max(nctx, 1), 1e-12))
    if ntree:
        s[nctx:] = np.sqrt(a_tree * max(float((Ps_[:, nctx:] ** 2).sum()) / max(ntree, 1), 1e-12))
    Zs = PP / s
    G = Zs @ Zs.T                                    # k x k -- the point of the whole function
    G.flat[:: k + 1] += 1.0
    try:
        L = np.linalg.cholesky(G)
        z = solve_triangular(L, Py, lower=True)
        u = solve_triangular(L.T, z, lower=False)
    except Exception:
        u = np.linalg.lstsq(G, Py, rcond=None)[0]
    bP = (Zs.T @ u) / s
    bU = np.linalg.lstsq(Us, ys - Ps_ @ bP, rcond=None)[0]
    return np.r_[bU, bP]


def metrics(yt, yp, ytb):
    e = yp - yt
    mae = float(np.abs(e).mean())
    r2 = 1 - float(((yt - yp) ** 2).sum()) / float(((yt - yt.mean()) ** 2).sum())
    hit5 = float((np.abs(e) <= 5).mean())
    try:
        auc = roc_auc_score(ytb, yp)
    except Exception:
        auc = np.nan
    return mae, r2, hit5, auc


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default="spatial,driver,combined")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    A = ap.parse_args()

    X = pd.read_parquet(FEAT)
    X["y"] = X.sid.map(continuous_target())
    X = X.dropna(subset=["y"]).reset_index(drop=True)
    allf = [c for c in X.columns if c not in ("sid", "eco", "side", "pos", "date", "y")]
    ABS = [c for c in allf if re.match(r"^(mean|std)_\d+$", c) or c in ("abslat", "mmm", "mmm_n_years")]
    fcols = [c for c in allf if c not in ABS]          # normalised-only: the Part 415 hygiene rule
    log("rows %s | normalised features %d (dropped %d absolute-temperature columns)"
        % (format(len(X), ","), len(fcols), len(ABS)))

    ev = pd.read_parquet(r"D:\coral\target\events_dated.parquet")
    X = X.merge(ev[["lat", "lon"]], left_on="sid", right_index=True, how="left")
    tr = X[X.side == "donor"].reset_index(drop=True)
    te = X[X.side == "test"].reset_index(drop=True)
    log("donor %s rows / %d regions | test %s rows / %d regions"
        % (format(len(tr), ","), tr.eco.nunique(), format(len(te), ","), te.eco.nunique()))

    # ---- context block: MMM is separate (unpenalised); harmonics + 5 top drivers are penalised
    imp = RandomForestRegressor(120, max_depth=8, min_samples_leaf=5, n_jobs=-1,
                                random_state=0).fit(tr[fcols].fillna(0), tr.y)
    top5 = list(pd.Series(imp.feature_importances_, index=fcols).sort_values(ascending=False).head(5).index)
    log("context drivers chosen on DONORS only: %s" % ", ".join(top5))
    for d in (X, tr, te):
        doy = d["date"].dt.dayofyear.values
        d["_h1s"], d["_h1c"] = np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)
        d["_h2s"], d["_h2c"] = np.sin(4 * np.pi * doy / 365.25), np.cos(4 * np.pi * doy / 365.25)
    ctxc = ["_h1s", "_h1c", "_h2s", "_h2c"] + top5

    # ---- sigma-hat for GLS
    sg = RandomForestRegressor(120, max_depth=8, min_samples_leaf=20, n_jobs=-1, random_state=0)
    oof = imp.predict(tr[fcols].fillna(0))
    sg.fit(tr[fcols].fillna(0), np.abs(tr.y.values - oof))
    def wts(d, on):
        if not on:
            return np.ones(len(d))
        s = np.clip(sg.predict(d[fcols].fillna(0)), 1e-6, None)
        lo, hi = np.percentile(s, [5, 95])
        return 1.0 / np.clip(s, lo, hi) ** 2

    NPD = [8, 16] if A.quick else [16, 24]
    MF = [0.15, 0.35] if A.quick else [0.08, 0.15, 0.25]
    KS = [60, 120] if A.quick else [30, 60, 100]
    AL = [0.5, 4.0] if A.quick else [0.1, 0.5, 2.0]
    GL = [False] if A.quick else [False, True]
    arms = [a.strip() for a in A.arms.split(",")]
    log("sweep: n_per_donor %s x max_features %s x k %s x alpha %s x gls %s x arms %s"
        % (NPD, MF, KS, AL, GL, arms))

    ytb = (te.y.values > 0).astype(int)
    dist_geo = haversine(te.lat.values[:, None], te.lon.values[:, None],
                         np.r_[tr.lat.values, te.lat.values][None, :],
                         np.r_[tr.lon.values, te.lon.values][None, :])
    pool_eco = np.r_[tr.eco.values, te.eco.values]
    pool_date = np.r_[tr.date.values, te.date.values]
    te_eco, te_date = te.eco.values, te.date.values
    # legality mask: donor rows always allowed; target-region rows only if STRICTLY earlier
    legal = np.ones_like(dist_geo, dtype=bool)
    n_tr = len(tr)
    for i in range(len(te)):
        same = pool_eco == te_eco[i]
        legal[i] = ~same | (pool_date < te_date[i])
        legal[i, n_tr + i] = False

    Z = np.vstack([tr[fcols].fillna(0).values, te[fcols].fillna(0).values]).astype(np.float32)
    mu, sd = Z[:n_tr].mean(0), Z[:n_tr].std(0) + 1e-9
    Zs = (Z - mu) / sd
    dist_drv = np.sqrt(((Zs[None, n_tr:, :] - Zs[None, :, :]) ** 2).sum(-1))[0] if False else None

    rows = []
    for npd, mf in itertools.product(NPD, MF):
        t0 = time.time()
        trees, owner = build_bank(tr, fcols, npd, mf, A.seed)
        Atr = tree_columns(trees, tr, fcols)
        Ate = tree_columns(trees, te, fcols)
        Apool = np.vstack([Atr, Ate])
        ntree = Apool.shape[1]
        ypool = np.r_[tr.y.values, te.y.values]
        Cpool = np.vstack([tr[ctxc].values, te[ctxc].values]).astype(np.float64)
        cm, cs = Cpool[:n_tr].mean(0), Cpool[:n_tr].std(0) + 1e-9
        Cpool = (Cpool - cm) / cs
        Mpool = np.r_[tr.mmm.values, te.mmm.values] if "mmm" in tr else np.zeros(len(ypool))
        log("bank: %d trees (%d/donor, max_features=%.2f) built in %.1fs"
            % (ntree, npd, mf, time.time() - t0))

        for arm in arms:
            # rank the pool once per arm
            order = np.empty((len(te), min(600, dist_geo.shape[1])), np.int32)
            for i in range(len(te)):
                ok = np.where(legal[i])[0]
                if arm == "spatial":
                    r = ok[np.argsort(dist_geo[i, ok])]
                elif arm == "driver":
                    d = np.sqrt(((Zs[ok] - Zs[n_tr + i]) ** 2).sum(1))
                    r = ok[np.argsort(d)]
                else:
                    g = ok[np.argsort(dist_geo[i, ok])][:min(len(ok), 3 * max(KS))]
                    d = np.sqrt(((Zs[g] - Zs[n_tr + i]) ** 2).sum(1))
                    r = g[np.argsort(d)]
                order[i, :min(len(r), order.shape[1])] = r[:order.shape[1]]
                if len(r) < order.shape[1]:
                    order[i, len(r):] = r[-1] if len(r) else 0
            for k, a_tree, gls in itertools.product(KS, AL, GL):
                w_all = np.r_[wts(tr, gls), wts(te, gls)]
                pred = np.empty(len(te))
                for i in range(len(te)):
                    sel = order[i, :k]
                    Xc = np.column_stack([np.ones(len(sel)), Mpool[sel] - Mpool[sel].mean(),
                                          Cpool[sel], Apool[sel]])
                    b = solve_local(Xc, ypool[sel], w_all[sel], ntree, len(ctxc), a_tree, 0.25)
                    xt = np.r_[1.0, Mpool[n_tr + i] - Mpool[sel].mean(),
                               Cpool[n_tr + i], Apool[n_tr + i]]
                    pred[i] = float(xt @ b)
                pred = np.clip(pred, 0, 100)
                mae, r2, h5, auc = metrics(te.y.values, pred, ytb)
                rows.append(dict(arm=arm, n_per_donor=npd, max_features=mf, k=k,
                                 alpha=a_tree, gls=gls, ntree=ntree,
                                 MAE=mae, R2=r2, hit5=h5, AUC=auc))
                log("   %-9s npd=%2d mf=%.2f k=%3d a=%.1f gls=%d | MAE %6.2f  R2 %+.4f  hit5 %.3f  AUC %.4f"
                    % (arm, npd, mf, k, a_tree, gls, mae, r2, h5, auc))

    R = pd.DataFrame(rows).sort_values("MAE")
    R.to_csv("architecture_sweep.csv", index=False)
    print("\n" + "=" * 96)
    print("TOP 15 BY MAE")
    print(R.head(15).to_string(index=False))
    print("\nBEST PER ARM")
    print(R.sort_values("MAE").groupby("arm").head(1).to_string(index=False))

    # baselines on the same test rows
    d84 = te["dhw_84"].fillna(0).values if "dhw_84" in te else np.zeros(len(te))
    from sklearn.linear_model import LinearRegression
    lr = LinearRegression().fit(tr[["dhw_84"]].fillna(0), tr.y)
    bl = lr.predict(te[["dhw_84"]].fillna(0))
    rf = RandomForestRegressor(600, min_samples_leaf=5, max_features="sqrt", n_jobs=-1,
                               random_state=0).fit(tr[fcols].fillna(0), tr.y)
    bp = rf.predict(te[fcols].fillna(0))
    print("\nBASELINES on the same rows")
    for nm, p in (("DHW_84 linear", bl), ("pooled forest (mf=sqrt)", bp),
                  ("constant train mean", np.full(len(te), tr.y.mean()))):
        mae, r2, h5, auc = metrics(te.y.values, np.clip(p, 0, 100), ytb)
        print("   %-26s MAE %6.2f  R2 %+.4f  hit5 %.3f  AUC %.4f" % (nm, mae, r2, h5, auc))
    print("\nsaved -> architecture_sweep.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
