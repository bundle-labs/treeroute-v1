"""Skeptic (numbers lens), round 14: minimal own code, written from PROTOCOL.md section 8 (and 10 for B1).

Readings used here (my own, from the protocol's words):
- region of a row = rows.parquet `group`; regions in sorted() order index the draw integers;
- I_m(j) = mean over regions of the within-region mean |phi_ij| (each region weighs 1);
  on a draw, a region drawn c times weighs c: I* = (1/G) sum_r c_r mean_r;
- S_m(j) the same with signed phi; shares over J;
- J = players to which some model of `models` gives more than 1e-12 of its total mean |phi|;
- strict order: I descending, ties by name ascending (Python order); average ranks for Spearman / W;
- RBO = (1-p) sum_{d=1..n} p^(d-1) X_d/d + p^n X_n/n over the two full strict rankings of J;
- TV = 1/2 sum |s_a - s_b|;
- family attribution on a row = sum of its variables' phiv on that row; family importance = region-weighted mean |.|;
  family share = importance / sum of the five families' importances.
"""
import os, json, hashlib
import numpy as np
import pyarrow.parquet as pq
from scipy.stats import rankdata

SHAP = r"D:\treeroute\analysis\shap_v1"
NB = 2000


def piece(p, m):
    return os.path.join(SHAP, "out", p, "lead_0", m)


def per_lead(p):
    with open(os.path.join(SHAP, "out", p, "lead_0", "compare", "per_lead.json"), encoding="utf-8") as f:
        return json.load(f)


def meta(p, m):
    with open(os.path.join(piece(p, m), "meta.json"), encoding="utf-8") as f:
        return json.load(f)


def load(p, m, level):
    path = os.path.join(piece(p, m), "rows.parquet")
    names = pq.ParquetFile(path).schema_arrow.names
    pref = "phi__" if level == "feature" else "phiv__"
    cols = [c for c in names if c.startswith(pref)]
    t = pq.read_table(path, columns=["row", "group", "pre"] + cols).to_pandas()
    t = t.sort_values("row", kind="stable").reset_index(drop=True)
    phi = {c[len(pref):]: t[c].to_numpy(dtype=np.float64) for c in cols}
    return t["row"].to_numpy(), t["group"].astype(str).to_numpy(), t["pre"].to_numpy(dtype=np.float64), phi


def load_draws(p):
    path = os.path.join(SHAP, "out", p, "lead_0", "compare", "bootstrap_draws.npy")
    with open(path, "rb") as f:
        raw = f.read()
    return np.load(path), hashlib.sha256(raw).hexdigest()


def regen_draws(p, G, lead=0):
    out = np.empty((NB, G), dtype=np.int64)
    for b in range(NB):
        for k in range(G):
            h = hashlib.sha256(("shap_v1|AW4|%s|%d|%d|%d" % (p, lead, b, k)).encode("utf-8")).digest()
            out[b, k] = int.from_bytes(h[:8], "big") % G
    return out


class Regions:
    def __init__(self, groups, d):
        self.names = sorted(set(groups.tolist()))
        self.G = len(self.names)
        pos = {g: i for i, g in enumerate(self.names)}
        self.ridx = np.array([pos[g] for g in groups.tolist()], dtype=np.int64)
        self.nr = np.bincount(self.ridx, minlength=self.G).astype(np.float64)
        assert d.shape[1] == self.G and d.min() >= 0 and d.max() < self.G
        self.C = np.zeros((d.shape[0], self.G))
        for b in range(d.shape[0]):
            self.C[b] = np.bincount(d[b], minlength=self.G)

    def rmeans(self, X):
        M = np.zeros((self.G, X.shape[1]))
        np.add.at(M, self.ridx, X)
        return M / self.nr[:, None]

    def full(self, M):
        return M.sum(axis=0) / self.G

    def boot(self, M):
        return (self.C @ M) / self.G


def matrix(phi, names, n):
    return np.column_stack([phi[j] if j in phi else np.zeros(n) for j in names])


def imp(phi, names, R):
    X = matrix(phi, names, len(R.ridx))
    Ma = R.rmeans(np.abs(X))
    Ms = R.rmeans(X)
    return dict(I=R.full(Ma), S=R.full(Ms), Id=R.boot(Ma), Sd=R.boot(Ms))


def active_set(models_phi, R, thr=1e-12):
    """models_phi: dict model -> phi dict. Returns sorted J and the union of names."""
    allnames = sorted(set().union(*[set(ph.keys()) for ph in models_phi.values()]))
    keep = set()
    for m, ph in models_phi.items():
        I = imp(ph, allnames, R)["I"]
        T = I.sum()
        if T > 0:
            keep |= {allnames[i] for i in np.nonzero(I > thr * T)[0]}
    return sorted(keep), allnames


def order(v):
    """strict order of a vector (or rows of a matrix) over J sorted by name: value desc, ties by name asc."""
    return np.argsort(-v, axis=-1, kind="stable")


def pearson_rows(a, b):
    a = a - a.mean(axis=-1, keepdims=True)
    b = b - b.mean(axis=-1, keepdims=True)
    num = (a * b).sum(axis=-1)
    den = np.sqrt((a * a).sum(axis=-1) * (b * b).sum(axis=-1))
    with np.errstate(invalid="ignore", divide="ignore"):
        r = num / den
    return np.where(den > 0, r, np.nan)


def spearman(a, b):
    """a, b: (n,) or (B, n). Pearson of average ranks."""
    ra = rankdata(a, method="average", axis=-1)
    rb = rankdata(b, method="average", axis=-1)
    return pearson_rows(ra, rb)


def topk_set(v, k):
    return set(order(v)[:k].tolist())


def spearman_top20_union(a, b):
    """a, b (n,) -> rho over the union of the two top-20 sets, ranks taken within the union."""
    u = sorted(topk_set(a, 20) | topk_set(b, 20))
    return float(spearman(a[u], b[u])), u


def spearman_top20_union_draws(A, Bm):
    out = np.empty(A.shape[0])
    oa = order(A)[:, :20]
    ob = order(Bm)[:, :20]
    for i in range(A.shape[0]):
        u = np.union1d(oa[i], ob[i])
        out[i] = spearman(A[i, u], Bm[i, u])
    return out


def rbo_orders(oa, ob, p):
    """oa, ob: (B, n) or (n,) arrays of indices in rank order (full permutations of range(n))."""
    oa = np.atleast_2d(oa)
    ob = np.atleast_2d(ob)
    Bn, n = oa.shape
    pa = np.empty_like(oa)
    pb = np.empty_like(ob)
    rows = np.arange(Bn)[:, None]
    pa[rows, oa] = np.arange(n)[None, :]
    pb[rows, ob] = np.arange(n)[None, :]
    depth = np.maximum(pa, pb)  # 0-based depth at which item is in both prefixes
    cnt = np.zeros((Bn, n))
    np.add.at(cnt, (np.repeat(np.arange(Bn), n), depth.ravel()), 1.0)
    X = np.cumsum(cnt, axis=1)
    d = np.arange(1, n + 1, dtype=np.float64)
    A = X / d[None, :]
    w = (1 - p) * p ** (d - 1)
    r = (A * w[None, :]).sum(axis=1) + (p ** n) * A[:, -1]
    return r


def rbo(a, b, p):
    return rbo_orders(order(a), order(b), p)


def tv(sa, sb):
    return 0.5 * np.abs(sa - sb).sum(axis=-1)


def kendall_w(Is):
    """Is: list of (n,) importance vectors (one per rater) over J. Tie-corrected W."""
    m = len(Is)
    n = len(Is[0])
    R = np.vstack([rankdata(v, method="average") for v in Is])
    Rj = R.sum(axis=0)
    S = ((Rj - m * (n + 1) / 2.0) ** 2).sum()
    T = 0.0
    for v in Is:
        _, c = np.unique(v, return_counts=True)
        T += (c.astype(np.float64) ** 3 - c).sum()
    den = m * m * (n ** 3 - n) - m * T
    return 12.0 * S / den if den > 0 else np.nan


def kendall_w_draws(Ids):
    """Ids: list of (B, n) arrays."""
    m = len(Ids)
    Bn, n = Ids[0].shape
    Rs = [rankdata(X, method="average", axis=1) for X in Ids]
    Rj = sum(Rs)
    S = ((Rj - m * (n + 1) / 2.0) ** 2).sum(axis=1)
    # sum_i V_i where V_i = sum_j (r_ij - (n+1)/2)^2 = (n^3 - n)/12 - T_i/12
    V = sum(((Rr - (n + 1) / 2.0) ** 2).sum(axis=1) for Rr in Rs)
    with np.errstate(invalid="ignore", divide="ignore"):
        W = S / (m * V)
    return np.where(V > 0, W, np.nan)


def ci(x):
    x = np.asarray(x, dtype=np.float64)
    f = x[np.isfinite(x)]
    if f.size == 0:
        return (None, None, 0)
    lo, hi = np.percentile(f, [2.5, 97.5])
    return (float(lo), float(hi), int(f.size))


def iv(value, draws):
    lo, hi, n = ci(draws)
    return dict(value=(None if value is None or not np.isfinite(value) else float(value)), ci_low=lo, ci_high=hi, n_finite=n)


# ---------- families ----------

def family_of(v, global_vars):
    if v == "normal":
        return "seasonal_normal"
    if v.startswith("hist_"):
        return "own_history"
    if v == "calendar" or v.startswith("ctx:"):
        return "context_and_calendar"
    if v in global_vars:
        return "global_indices"
    return "local_drivers"


FAMS = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]


def family_imp(phiv, global_vars, R):
    """phiv: dict variable -> (n,) phi. Returns full (5,) and draws (B,5) family importances."""
    n = len(R.ridx)
    F = np.zeros((n, len(FAMS)))
    for v, x in phiv.items():
        F[:, FAMS.index(family_of(v, global_vars))] += x
    Ma = R.rmeans(np.abs(F))
    return R.full(Ma), R.boot(Ma)


def shares_of(I):
    return I / I.sum(axis=-1, keepdims=True)
