"""Agreement statistics between importance vectors (ruling AW4; PROTOCOL.md section 8, v3). numpy only.

Every function takes importance vectors aligned on the same players (one value per player; larger = more
important) and is deterministic: ties in ranks get average ranks; top-k sets and ranked lists break ties by the
fixed player order (the alphabetical order of the player names, passed in as 'order').

v3 (2026-11-12, after the design review): RBO is computed on the full rankings over the active set J (equal length,
ties broken by name), not on each model's nonzero list (the extrapolation of RBO_ext treats a shorter list as a
truncated prefix and overstated agreement); the mean pairwise Spearman is computed directly (the identity
(mW - 1)/(m - 1) holds only when every ranking has the same ties); percentile intervals report how many bootstrap
replicates were finite; a sign is 'determined' only when its bootstrap interval excludes 0 (decided by the caller).
"""
import numpy as np


def rankdata(a):
    """Average ranks (1 = smallest), as scipy.stats.rankdata(method='average'); vectorised."""
    a = np.asarray(a, np.float64)
    n = a.size
    if n == 0:
        return np.zeros(0)
    order = np.argsort(a, kind="mergesort")
    s = a[order]
    new = np.empty(n, bool)
    new[0] = True
    new[1:] = s[1:] != s[:-1]
    grp = np.cumsum(new) - 1                         # tie-group id in sorted order
    first = np.flatnonzero(new)
    last = np.append(first[1:], n) - 1
    avg = 0.5 * (first + last) + 1.0
    ranks = np.empty(n, np.float64)
    ranks[order] = avg[grp]
    return ranks


def _pearson(x, y):
    x = x - x.mean()
    y = y - y.mean()
    den = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / den) if den > 0 else float("nan")


def spearman(a, b):
    """Spearman's rho: Pearson's correlation of the average ranks (NaN when a vector is constant)."""
    return _pearson(rankdata(a), rankdata(b))


def sign_matrix(a):
    a = np.asarray(a, np.float64)
    return np.sign(a[:, None] - a[None, :])


def kendall_tau_b(a, b, da=None, db=None):
    """Kendall's tau-b = (nc - nd) / sqrt((n0 - n1)(n0 - n2)), ties in either vector corrected. da, db: optional
    precomputed sign matrices (sign_matrix)."""
    a = np.asarray(a, np.float64)
    da = sign_matrix(a) if da is None else da
    db = sign_matrix(b) if db is None else db
    n = a.size
    iu = np.triu_indices(n, 1)
    s = (da[iu] * db[iu])
    nc_nd = float(s.sum())
    n0 = n * (n - 1) / 2.0
    n1 = float((da[iu] == 0).sum())
    n2 = float((db[iu] == 0).sum())
    den = np.sqrt((n0 - n1) * (n0 - n2))
    return nc_nd / den if den > 0 else float("nan")


def ranked(values, order):
    """Player indices from most to least important; ties broken by 'order' (a rank per player, smaller first)."""
    values = np.asarray(values, np.float64)
    return list(np.lexsort((np.asarray(order), -values)))


def topk(values, order, k):
    return set(ranked(values, order)[:int(k)])


def jaccard_topk(a, b, order, k):
    sa, sb = topk(a, order, k), topk(b, order, k)
    u = sa | sb
    return len(sa & sb) / float(len(u)) if u else float("nan")


def rbo_ext(list1, list2, p):
    """Rank-biased overlap, extrapolated (Webber, Moffat and Zobel 2010, eq. 32), for two rankings without ties
    of possibly different lengths. list1, list2: item ids from most to least important. (Unit tests and reference
    only: the comparison uses rbo_full on rankings of equal length.)"""
    S, L = (list1, list2) if len(list1) <= len(list2) else (list2, list1)
    s, l = len(S), len(L)
    if l == 0:
        return float("nan")
    if s == 0:
        return 0.0
    seen_s, seen_l = set(), set()
    X = np.zeros(l + 1)
    overlap = 0
    for d in range(1, l + 1):
        x = L[d - 1]
        if d <= s:
            y = S[d - 1]
            if x == y:
                overlap += 1
            else:
                overlap += (x in seen_s) + (y in seen_l)
            seen_s.add(y)
            seen_l.add(x)
        else:
            overlap += (x in seen_s)
            seen_l.add(x)
        X[d] = overlap
    Xs, Xl = X[s], X[l]
    sum1 = sum(X[d] / d * p ** d for d in range(1, l + 1))
    sum2 = sum(Xs * (d - s) / (s * d) * p ** d for d in range(s + 1, l + 1))
    return float((1 - p) / p * (sum1 + sum2) + ((Xl - Xs) / l + Xs / s) * p ** l)


def rbo_full(a, b, order, p):
    """RBO of the two FULL rankings of the same players (every player of J, ties broken by 'order'): equal length k,
    so eq. 32 reduces to RBO = (X_k / k) p^k + (1 - p)/p sum_{d=1..k} (X_d / d) p^d, X_d = |top_d(a) & top_d(b)|.
    Vectorised: a player is in both top-d sets once d >= max(its two positions)."""
    a = np.asarray(a, np.float64)
    k = a.size
    if k == 0:
        return float("nan")
    pa = np.empty(k, np.int64)
    pb = np.empty(k, np.int64)
    pa[np.asarray(ranked(a, order), np.int64)] = np.arange(1, k + 1)
    pb[np.asarray(ranked(b, order), np.int64)] = np.arange(1, k + 1)
    m = np.maximum(pa, pb)
    X = np.cumsum(np.bincount(m, minlength=k + 1)[1:]).astype(np.float64)     # X_d, d = 1..k
    d = np.arange(1, k + 1, dtype=np.float64)
    pw = p ** d
    return float(X[-1] / k * p ** k + (1 - p) / p * np.sum(X / d * pw))


def n_nonzero(v):
    return int(np.count_nonzero(np.asarray(v) > 0))


def shares(v):
    v = np.asarray(v, np.float64)
    t = v.sum()
    return v / t if t > 0 else np.full(v.size, np.nan)


def tvd(a, b):
    """Total-variation distance 0.5 * sum |s_a - s_b| between the two vectors' shares."""
    return float(0.5 * np.abs(shares(a) - shares(b)).sum())


def sign_agreement(sa, sb, keep, det_a=None, det_b=None):
    """Share of the players in 'keep' whose signed mean attributions have the same sign in both models, among the
    players whose sign is determined in both (det_a, det_b: boolean masks, e.g. the bootstrap interval of the signed
    mean excludes 0; default: nonzero). Returns (share, players compared)."""
    keep = np.asarray(sorted(keep), np.int64)
    a, b = np.sign(np.asarray(sa)[keep]), np.sign(np.asarray(sb)[keep])
    da = (a != 0) if det_a is None else (np.asarray(det_a)[keep] & (a != 0))
    db = (b != 0) if det_b is None else (np.asarray(det_b)[keep] & (b != 0))
    det = da & db
    n = int(det.sum())
    return (float((a[det] == b[det]).mean()) if n else float("nan")), n


def kendall_w(M):
    """Kendall's coefficient of concordance W of m rankings (rows of M, m x n scores) with the tie correction:
    W = 12 S / (m^2 (n^3 - n) - m sum_k T_k), T_k = sum over tie groups of (t^3 - t) in ranking k."""
    M = np.asarray(M, np.float64)
    m, n = M.shape
    if m < 2 or n < 2:
        return float("nan")
    R = np.vstack([rankdata(r) for r in M])
    Rj = R.sum(0)
    S = float(((Rj - Rj.mean()) ** 2).sum())
    T = 0.0
    for r in M:
        _, cnt = np.unique(r, return_counts=True)
        T += float((cnt ** 3 - cnt).sum())
    den = m * m * (n ** 3 - n) - m * T
    return 12.0 * S / den if den > 0 else float("nan")


def mean_pairwise_spearman(M):
    """The mean of the pairwise Spearman correlations of the rows of M (reported instead of (mW - 1)/(m - 1), which
    is exact only when every ranking has the same tie structure)."""
    M = np.asarray(M, np.float64)
    v = [spearman(M[i], M[j]) for i in range(M.shape[0]) for j in range(i + 1, M.shape[0])]
    v = [x for x in v if np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def pair_stats(a, b, order, ks=(5, 10), ps=(0.9, 0.95), top_union_k=20, da=None, db=None):
    """Every pairwise rank statistic of PROTOCOL.md section 8 for importance vectors a, b (mean |phi|) over the
    players given (the active set J)."""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    out = {"spearman": spearman(a, b), "kendall_tau_b": kendall_tau_b(a, b, da, db), "tvd": tvd(a, b)}
    u = sorted(topk(a, order, top_union_k) | topk(b, order, top_union_k))
    out["spearman_top%d_union" % top_union_k] = spearman(a[u], b[u]) if len(u) > 2 else float("nan")
    for k in ks:
        out["jaccard_top%d" % k] = jaccard_topk(a, b, order, k)
    for p in ps:
        out["rbo_p%g" % p] = rbo_full(a, b, order, p)
    return out


def profile(v, order):
    """Everything the pairwise statistics need from one importance vector, computed once (the bootstrap reuses it):
    average ranks, the position in the tie-broken ranking (1 = most important), the upper-triangle sign vector of
    Kendall's tau, the shares and the tie term of Kendall's W."""
    v = np.asarray(v, np.float64)
    k = v.size
    pos = np.empty(k, np.int64)
    pos[np.asarray(ranked(v, order), np.int64)] = np.arange(1, k + 1)
    iu = np.triu_indices(k, 1)
    _, cnt = np.unique(v, return_counts=True)
    return {"v": v, "r": rankdata(v), "pos": pos, "sgn": np.sign(v[:, None] - v[None, :])[iu], "sh": shares(v),
            "T": float((cnt ** 3 - cnt).sum())}


def pair_from_profiles(pa, pb, ks=(5, 10), ps=(0.9, 0.95), top_union_k=20):
    """pair_stats computed from two profiles (identical results; checked in smoke S1)."""
    out = {"spearman": _pearson(pa["r"], pb["r"])}
    s = float((pa["sgn"] * pb["sgn"]).sum())
    n0 = float(pa["sgn"].size)
    n1, n2 = float((pa["sgn"] == 0).sum()), float((pb["sgn"] == 0).sum())
    den = np.sqrt((n0 - n1) * (n0 - n2))
    out["kendall_tau_b"] = s / den if den > 0 else float("nan")
    out["tvd"] = float(0.5 * np.abs(pa["sh"] - pb["sh"]).sum())
    u = np.flatnonzero((pa["pos"] <= top_union_k) | (pb["pos"] <= top_union_k))
    out["spearman_top%d_union" % top_union_k] = spearman(pa["v"][u], pb["v"][u]) if u.size > 2 else float("nan")
    for k in ks:
        sa, sb = pa["pos"] <= k, pb["pos"] <= k
        un = int((sa | sb).sum())
        out["jaccard_top%d" % k] = int((sa & sb).sum()) / float(un) if un else float("nan")
    K = pa["pos"].size
    m = np.maximum(pa["pos"], pb["pos"])
    X = np.cumsum(np.bincount(m, minlength=K + 1)[1:]).astype(np.float64)
    d = np.arange(1, K + 1, dtype=np.float64)
    for p in ps:
        out["rbo_p%g" % p] = float(X[-1] / K * p ** K + (1 - p) / p * np.sum(X / d * p ** d)) if K else float("nan")
    return out


def kendall_w_profiles(profs):
    m = len(profs)
    if m < 2:
        return float("nan")
    n = profs[0]["r"].size
    if n < 2:
        return float("nan")
    Rj = np.sum([p["r"] for p in profs], 0)
    S = float(((Rj - Rj.mean()) ** 2).sum())
    den = m * m * (n ** 3 - n) - m * sum(p["T"] for p in profs)
    return 12.0 * S / den if den > 0 else float("nan")


def percentile_ci(values, level=0.95):
    """(low, high, number of finite replicates): percentile interval over the finite replicates."""
    v = np.asarray(values, np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan"), float("nan"), 0
    lo = (1 - level) / 2
    return float(np.quantile(v, lo)), float(np.quantile(v, 1 - lo)), int(v.size)
