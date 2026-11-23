# Implementer B, round 14: shared statistics, written from SHAP\PROTOCOL.md sections 5, 8 and 10 only.
# Every function works on a stack of "draw rows": row 0 can be the full sample and rows 1..B the bootstrap draws.
# Conventions (choices.md): average ranks for ties (exact equality), ties in an ordered ranking broken by name
# ascending (Python string order), percentile intervals by numpy's default linear interpolation.
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
V = Path(r"D:\treeroute\analysis\shap_v1\verify_v1")
VB = V / "B"
FAMILIES = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]
ACTIVE_REL = 1e-12          # section 8: "more than 1e-12 of its total mean |phi|"
N_DRAWS = 2000


def short(path):
    """Short name of a path (privacy rule): SHAP\\..., V\\..., else the path itself (no user folders here)."""
    s = str(path)
    for full, name in ((str(V), "V"), (str(SHAP), "SHAP")):
        if s.lower().startswith(full.lower()):
            return name + s[len(full):]
    return s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ draws
def generator_row(problem, lead, b, G):
    salt = "shap_v1|AW4|%s|%d" % (problem, lead)
    return [int.from_bytes(hashlib.sha256(("%s|%d|%d" % (salt, b, k)).encode("utf-8")).digest()[:8], "big") % G
            for k in range(G)]


def draw_counts(draws, G):
    """(B, G) matrix: how many times each region (column index) is in each draw (row)."""
    B = draws.shape[0]
    C = np.zeros((B, G), dtype=np.float64)
    np.add.at(C, (np.repeat(np.arange(B), draws.shape[1]), draws.ravel()), 1.0)
    return C


# ------------------------------------------------------------------ region weighting
def region_means(X, region, G):
    """Per-region mean of each column of X (rows -> regions); each row of a region weighs 1/n_r."""
    n = np.bincount(region, minlength=G).astype(np.float64)
    S = np.zeros((G, X.shape[1]), dtype=np.float64)
    np.add.at(S, region, X)
    with np.errstate(invalid="ignore", divide="ignore"):
        M = S / n[:, None]
    M[n == 0] = 0.0
    return M, n


def weighted_over_regions(Cfull, M, present=None):
    """Rows of Cfull: region multiplicities of one draw (the full sample: all ones). Each drawn copy of a region
    weighs 1; the value is the mean over the drawn regions of the region means M. With `present` (bool, G), only the
    drawn regions that are present count (item 8); a draw with none of them gives NaN."""
    if present is None:
        return (Cfull @ M) / Cfull.sum(axis=1, keepdims=True)
    W = Cfull * present[None, :].astype(np.float64)
    tot = W.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (W @ M) / tot
    out[tot[:, 0] == 0] = np.nan
    return out


# ------------------------------------------------------------------ rankings
def order_by_importance(I):
    """I: (R, n) with columns in name order (ascending). Returns (R, n) column indices in rank order: larger I
    first, ties (exact equality) kept in name order (stable sort)."""
    return np.argsort(-I, axis=1, kind="stable")


def positions(order):
    """1-based rank position of every column, from an order array."""
    R, n = order.shape
    pos = np.empty_like(order)
    pos[np.arange(R)[:, None], order] = np.arange(1, n + 1)[None, :]
    return pos


def avg_ranks(X):
    return rankdata(X, method="average", axis=1)


def _pearson_rows(RX, RY):
    RX = RX - RX.mean(axis=1, keepdims=True)
    RY = RY - RY.mean(axis=1, keepdims=True)
    num = (RX * RY).sum(axis=1)
    den = np.sqrt((RX * RX).sum(axis=1) * (RY * RY).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[den == 0] = np.nan
    return out


def spearman_rows(X, Y):
    """Spearman's rho per row: Pearson's correlation of the average ranks (ties: exact equality)."""
    return _pearson_rows(avg_ranks(X), avg_ranks(Y))


def spearman_masked(X, Y, M):
    """Spearman's rho per row over the columns where M is True, ranks taken within that set."""
    out = np.full(X.shape[0], np.nan)
    Xm = np.where(M, X, np.nan)
    Ym = np.where(M, Y, np.nan)
    RX = rankdata(Xm, method="average", axis=1, nan_policy="omit")
    RY = rankdata(Ym, method="average", axis=1, nan_policy="omit")
    k = M.sum(axis=1).astype(np.float64)
    mid = (k + 1.0) / 2.0
    DX = np.where(M, RX - mid[:, None], 0.0)
    DY = np.where(M, RY - mid[:, None], 0.0)
    num = (DX * DY).sum(axis=1)
    den = np.sqrt((DX * DX).sum(axis=1) * (DY * DY).sum(axis=1))
    ok = den > 0
    out[ok] = num[ok] / den[ok]
    return out


def sign_matrix(X, iu, ju):
    return np.sign(X[:, iu] - X[:, ju]).astype(np.int8)


def kendall_tau_b_all(Xs, pairs, chunk=40):
    """Kendall's tau-b (tie-corrected) per row for each pair (a, b) of the stack Xs[name] (R, n)."""
    names = list(Xs)
    R, n = Xs[names[0]].shape
    iu, ju = np.triu_indices(n, 1)
    out = {pr: np.full(R, np.nan) for pr in pairs}
    for s in range(0, R, chunk):
        e = min(R, s + chunk)
        D = {m: sign_matrix(Xs[m][s:e], iu, ju) for m in names}
        Nt = {m: np.abs(D[m]).sum(axis=1).astype(np.float64) for m in names}
        for a, b in pairs:
            num = (D[a] * D[b]).sum(axis=1).astype(np.float64)
            den = np.sqrt(Nt[a] * Nt[b])
            with np.errstate(invalid="ignore", divide="ignore"):
                v = num / den
            v[den == 0] = np.nan
            out[(a, b)][s:e] = v
    return out


def rbo_rows(pos_a, pos_b, p):
    """RBO on two full rankings of the same n items (equal length k = n), eq. 32 of Webber, Moffat and Zobel (2010)
    in its finite form for equal lengths: ((1-p)/p) * sum_{d=1..k} (X_d/d) p^d + (X_k/k) p^k, X_d the overlap of the
    two top-d sets."""
    R, n = pos_a.shape
    mx = np.maximum(pos_a, pos_b)            # an item is in both top-d sets iff max(position) <= d
    H = np.zeros((R, n + 1), dtype=np.float64)
    np.add.at(H, (np.repeat(np.arange(R), n), mx.ravel()), 1.0)
    X = np.cumsum(H, axis=1)[:, 1:]           # X_d, d = 1..n
    d = np.arange(1, n + 1, dtype=np.float64)
    w = np.power(p, d) / d
    return ((1.0 - p) / p) * (X @ w) + (X[:, -1] / n) * (p ** n)


def jaccard_topk(pos_a, pos_b, k):
    A = pos_a <= k
    Bm = pos_b <= k
    inter = (A & Bm).sum(axis=1).astype(np.float64)
    union = (A | Bm).sum(axis=1).astype(np.float64)
    return inter / union


def kendall_w_rows(Is):
    """Kendall's W with the tie correction over the rankings Is (list of (R, n)): W = S / (m * sum_i V_i), which equals
    12 S / (m^2 (n^3 - n) - m sum_i T_i) because sum_j (r_ij - (n+1)/2)^2 = ((n^3 - n) - T_i) / 12 for average ranks."""
    m = len(Is)
    Rk = [avg_ranks(I) for I in Is]
    n = Rk[0].shape[1]
    tot = np.sum(Rk, axis=0)
    S = ((tot - m * (n + 1) / 2.0) ** 2).sum(axis=1)
    Vs = sum(((r - (n + 1) / 2.0) ** 2).sum(axis=1) for r in Rk)
    with np.errstate(invalid="ignore", divide="ignore"):
        W = S / (m * Vs)
    W[Vs == 0] = np.nan
    return W


def kendall_w_explicit(rankings):
    """Textbook tie-corrected W for one set of rankings (list of 1-D arrays of values), for the checks."""
    m = len(rankings)
    n = len(rankings[0])
    R = np.array([rankdata(r, method="average") for r in rankings])
    S = ((R.sum(axis=0) - m * (n + 1) / 2.0) ** 2).sum()
    T = 0.0
    for r in rankings:
        _, cnt = np.unique(np.asarray(r), return_counts=True)
        T += float(((cnt ** 3) - cnt).sum())
    return 12.0 * S / (m * m * (n ** 3 - n) - m * T)


# ------------------------------------------------------------------ intervals and output
def finite_or_none(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def interval(value, draws, value_why=None, none_why=None):
    """Interval object: value on the full sample; percentile 95% interval over the finite draws (numpy linear)."""
    d = {}
    v = finite_or_none(value)
    d["value"] = v
    if v is None:
        d["value_why"] = value_why or "Not finite on the full sample."
    if draws is None:
        why = none_why or "No interval for this number (choices.md)."
        d.update({"ci_low": None, "ci_high": None, "n_finite": None,
                  "ci_low_why": why, "ci_high_why": why, "n_finite_why": why})
        return d
    draws = np.asarray(draws, dtype=np.float64)
    fin = np.isfinite(draws)
    nf = int(fin.sum())
    d["n_finite"] = nf
    if nf == 0:
        why = "No draw gives a finite value."
        d.update({"ci_low": None, "ci_high": None, "ci_low_why": why, "ci_high_why": why})
    else:
        lo, hi = np.percentile(draws[fin], [2.5, 97.5])
        d["ci_low"] = float(lo)
        d["ci_high"] = float(hi)
    return d


def no_interval(value, why, value_why=None):
    return interval(value, None, value_why=value_why, none_why=why)


def determined(draws_S):
    """Sign determined: the percentile 95% interval of the signed mean over the finite draws excludes 0 (strictly)."""
    out = []
    for j in range(draws_S.shape[1]):
        col = draws_S[:, j]
        col = col[np.isfinite(col)]
        if col.size == 0:
            out.append(None)
            continue
        lo, hi = np.percentile(col, [2.5, 97.5])
        out.append(bool(lo > 0 or hi < 0))
    return out


def to_jsonable(o):
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        if not math.isfinite(f):
            raise ValueError("non-finite number in output")
        return f
    return o


def dump_json(obj, path):
    txt = json.dumps(to_jsonable(obj), indent=1, allow_nan=False, ensure_ascii=False)
    Path(path).write_text(txt, encoding="utf-8")


class Draws(object):
    """Collects the per-draw arrays of one npz file (keys = JSON paths below problems.<p> or b1.<p>, joined by /).
    Stacks have R = 1 + B rows: row 0 the full sample, rows 1..B the draws in the order of bootstrap_draws.npy."""

    def __init__(self):
        self.a = {}

    def iv(self, path, stack, value_why=None):
        stack = np.asarray(stack, dtype=np.float64)
        d = stack[1:].copy()
        d[~np.isfinite(d)] = np.nan
        self.a["/".join(path)] = d
        return interval(stack[0], stack[1:], value_why=value_why)

    def players(self, path, names, I, S, Sg, det):
        key = "/".join(path)
        self.a[key + "/names"] = np.array(names)
        for nm, arr in (("I", I), ("share", S), ("signed_mean", Sg)):
            d = np.array(arr[1:], dtype=np.float64)
            d[~np.isfinite(d)] = np.nan
            self.a[key + "/" + nm] = d
        out = {}
        for j, n in enumerate(names):
            e = {"I": interval(I[0, j], I[1:, j]), "share": interval(S[0, j], S[1:, j]),
                 "signed_mean": interval(Sg[0, j], Sg[1:, j]), "sign_determined": det[j]}
            if det[j] is None:
                e["sign_determined_why"] = "No finite draw of the signed mean."
            out[n] = e
        return out


def top_list(names, order_row, share_row, k):
    return [[names[i], float(share_row[i])] for i in order_row[:k]]


def model_block(I_all, S_all, jidx):
    """Per-model arrays over the columns jidx (J in name order): I, shares over J, signed means, order, positions,
    determined signs."""
    IJ = I_all[:, jidx]
    tot = IJ.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        SH = IJ / tot
    SG = S_all[:, jidx]
    ORD = order_by_importance(IJ)
    return {"IJ": IJ, "SH": SH, "SG": SG, "ORD": ORD, "POS": positions(ORD), "DET": determined(SG[1:])}


def pair_block(D, pb, J, a, b, fam_a, fam_b, tau_ab):
    """Section 8's pair statistics for two models a, b (dicts of model_block) over J; per-draw arrays into D."""
    nJ = len(J)
    e = {}
    sp = spearman_rows(a["IJ"], b["IJ"])
    e["spearman_J"] = D.iv(pb + ["spearman_J"], sp)
    u20 = (a["POS"] <= 20) | (b["POS"] <= 20)
    s20 = spearman_masked(a["IJ"], b["IJ"], u20)
    e["spearman_top20_union"] = D.iv(pb + ["spearman_top20_union"], s20)
    e["top20_union"] = sorted(J[i] for i in np.flatnonzero(u20[0]))
    e["kendall_tau_b"] = D.iv(pb + ["kendall_tau_b"], tau_ab)
    e["jaccard_top5"] = D.iv(pb + ["jaccard_top5"], jaccard_topk(a["POS"], b["POS"], 5))
    e["jaccard_top10"] = D.iv(pb + ["jaccard_top10"], jaccard_topk(a["POS"], b["POS"], 10))
    if nJ >= 200:
        e["jaccard_top20"] = D.iv(pb + ["jaccard_top20"], jaccard_topk(a["POS"], b["POS"], 20))
    else:
        e["jaccard_top20"] = None
        e["jaccard_top20_why"] = ("J has %d players, fewer than 200 (section 8: top-20 only when J has 200 or more)."
                                  % nJ)
    e["rbo_p090"] = D.iv(pb + ["rbo_p090"], rbo_rows(a["POS"], b["POS"], 0.9))
    e["rbo_p095"] = D.iv(pb + ["rbo_p095"], rbo_rows(a["POS"], b["POS"], 0.95))
    e["tv_shares"] = D.iv(pb + ["tv_shares"], 0.5 * np.abs(a["SH"] - b["SH"]).sum(axis=1))
    e["tv_family_shares"] = D.iv(pb + ["tv_family_shares"], 0.5 * np.abs(fam_a - fam_b).sum(axis=1))
    u10 = (a["POS"] <= 10) | (b["POS"] <= 10)
    detb = np.array([(x is True) and (y is True) for x, y in zip(a["DET"], b["DET"])])
    Dm = u10 & detb[None, :]
    ndet = Dm.sum(axis=1).astype(np.float64)
    agree = (Dm & (np.sign(a["SG"]) == np.sign(b["SG"]))).sum(axis=1).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        sa = agree / ndet
    sa[ndet == 0] = np.nan
    e["sign_agreement"] = D.iv(pb + ["sign_agreement"], sa,
                               value_why="No player of the union of the two top-10 sets has its sign determined in both models.")
    e["sign_n_determined"] = D.iv(pb + ["sign_n_determined"], ndet)
    e["sign_n_agree"] = D.iv(pb + ["sign_n_agree"], agree)
    e["sign_union_top10"] = sorted(J[i] for i in np.flatnonzero(u10[0]))
    e["sign_determined_both"] = sorted(J[i] for i in np.flatnonzero(Dm[0]))
    return e, sp, s20


def family_of(v, gi):
    """Section 8's five families; precedence: the seasonal normal, own history (hist_*), context and calendar
    (calendar, ctx:<name>), then the global-index rule (gi, from the lead's test set), else local drivers."""
    if v == "normal":
        return "seasonal_normal"
    if v.startswith("hist_"):
        return "own_history"
    if v == "calendar" or v.startswith("ctx:"):
        return "context_and_calendar"
    if v in gi:
        return "global_indices"
    return "local_drivers"


def family_stack(vars_m, Xv, vf, region, G, Cs):
    """Family shares per draw row: a family's attribution on a row is the sum of its variables' (variable-level) phi
    on that row; its importance the region-weighted mean of |that sum|; shares over the five families."""
    Fm = np.zeros((Xv.shape[0], len(FAMILIES)))
    for k, v in enumerate(vars_m):
        Fm[:, FAMILIES.index(vf[v])] += Xv[:, k]
    A, _ = region_means(np.abs(Fm), region, G)
    FI = weighted_over_regions(Cs, A)
    with np.errstate(invalid="ignore", divide="ignore"):
        return FI / FI.sum(axis=1, keepdims=True)


def load_rows(path, level, columns_extra=("row", "group", "pre")):
    """Rows of a piece sorted by `row`, with its phi__ (feature) or phiv__ (variable) columns."""
    import pyarrow.parquet as pq
    names = pq.read_schema(path).names
    pref = "phi__" if level == "feature" else "phiv__"
    att = [c for c in names if c.startswith(pref)]
    t = pq.read_table(path, columns=list(columns_extra) + att).to_pandas()
    t = t.sort_values("row", kind="stable").reset_index(drop=True)
    players = [c[len(pref):] for c in att]
    X = t[att].to_numpy(dtype=np.float64)
    return t[list(columns_extra)], players, X
