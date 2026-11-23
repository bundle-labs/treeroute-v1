# Round 14, implementer A: shared code (own code, written from PROTOCOL.md sections 5, 8, 9 and 10).
# Nothing here is copied from SHAP\scripts. Choices are recorded in V\A\choices.md.
import hashlib
import json
import math
import os

import numpy as np
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
VDIR = os.path.join(SHAP, "verify_v1")
V_A = os.path.join(VDIR, "A")
PROBLEMS = ["coral", "defo", "fire", "pm25", "ndvi"]
STRUCT_KEYS = ["models", "main_set", "declined_by_guard", "links", "rows", "sample_sha256", "draws_sha256"]
FAMILIES = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]
THRESH = 1e-12          # section 8: "more than 1e-12 of its total mean |phi|"
N_DRAWS = 2000
KEYCOLS = ["row", "unit", "group", "time", "year"]

OPENED = set()          # every file the code opens (short paths), for README.md


def short(path):
    p = os.path.normpath(path)
    for base, name in ((VDIR, "V"), (SHAP, "SHAP")):
        b = os.path.normpath(base)
        if p.lower().startswith(b.lower() + os.sep) or p.lower() == b.lower():
            return name + p[len(b):]
    return p


def note_open(path):
    OPENED.add(short(path))


# ------------------------------------------------------------------ reading
def read_per_lead_struct(p):
    """per_lead.json: only the structural keys are kept (the rest is never printed or kept)."""
    path = os.path.join(SHAP, "out", p, "lead_0", "compare", "per_lead.json")
    note_open(path)
    with open(path, "r", encoding="utf-8") as fh:
        pl = json.load(fh)
    out = {k: pl[k] for k in STRUCT_KEYS}
    del pl
    return out


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_draws(p):
    path = os.path.join(SHAP, "out", p, "lead_0", "compare", "bootstrap_draws.npy")
    note_open(path)
    d = np.load(path, allow_pickle=False)
    return d, sha256_file(path), path


def read_meta(p, piece):
    path = os.path.join(SHAP, "out", p, "lead_0", piece, "meta.json")
    note_open(path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_done(p, piece):
    path = os.path.join(SHAP, "out", p, "lead_0", piece, "rows.parquet.done.json")
    note_open(path)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_rows(p, piece):
    """rows.parquet of one piece: keys, pre, resid_flag, phi__ (feature level) and phiv__ (variable level)."""
    path = os.path.join(SHAP, "out", p, "lead_0", piece, "rows.parquet")
    note_open(path)
    names = pq.ParquetFile(path).schema_arrow.names
    phi_cols = [c for c in names if c.startswith("phi__")]
    phiv_cols = [c for c in names if c.startswith("phiv__")]
    t = pq.read_table(path, columns=KEYCOLS + ["pre", "resid_flag"] + phi_cols + phiv_cols)
    keys = {c: t.column(c).to_numpy(zero_copy_only=False) for c in KEYCOLS}
    order = np.argsort(keys["row"], kind="stable")
    keys = {c: v[order] for c, v in keys.items()}
    pre = t.column("pre").to_numpy()[order].astype(np.float64)
    flag = t.column("resid_flag").to_numpy(zero_copy_only=False)[order].astype(bool)
    phi = np.column_stack([t.column(c).to_numpy().astype(np.float64) for c in phi_cols])[order]
    phiv = np.column_stack([t.column(c).to_numpy().astype(np.float64) for c in phiv_cols])[order]
    if len(set(phi_cols)) != len(phi_cols) or len(set(phiv_cols)) != len(phiv_cols):
        raise SystemExit("repeated column name in %s" % path)
    if not (np.isfinite(phi).all() and np.isfinite(phiv).all()):
        raise SystemExit("non-finite phi in %s" % path)
    return {"keys": keys, "pre": pre, "resid_flag": flag,
            "players": [c[len("phi__"):] for c in phi_cols], "phi": phi,
            "variables": [c[len("phiv__"):] for c in phiv_cols], "phiv": phiv}


# ------------------------------------------------------------------ regions and draws
def region_index(groups):
    """Region of a row = its `group`; regions in Python sorted() order (equal to first-appearance order here)."""
    regions = sorted(set(groups.tolist()))
    pos = {r: i for i, r in enumerate(regions)}
    return regions, np.array([pos[g] for g in groups.tolist()], dtype=np.int64)


def region_mean_matrix(reg, G, rows_mask=None):
    """M (G x n_rows): M[r, i] = 1/n_r for the rows i of region r (rows_mask: only those rows)."""
    n = len(reg)
    use = np.ones(n, bool) if rows_mask is None else rows_mask
    M = np.zeros((G, n))
    M[reg[use], np.nonzero(use)[0]] = 1.0
    cnt = M.sum(axis=1)
    has = cnt > 0
    M[has] /= cnt[has][:, None]
    return M, has, cnt


def draw_counts(draws, G):
    """counts[b, r] = how many times region r is in draw b (draws: rows = draws, columns = the G picks)."""
    Bn = draws.shape[0]
    c = np.zeros((Bn, G))
    np.add.at(c, (np.repeat(np.arange(Bn), draws.shape[1]), draws.ravel()), 1.0)
    return c


# ------------------------------------------------------------------ rank helpers (ties = exact equality)
def avg_ranks_2d(X):
    """Average ranks (1-based, ascending) along axis 1; ties are exact float equality."""
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    R, n = X.shape
    order = np.argsort(X, axis=1, kind="mergesort")
    Xs = np.take_along_axis(X, order, axis=1)
    idx = np.broadcast_to(np.arange(n), (R, n))
    newg = np.ones((R, n), bool)
    newg[:, 1:] = Xs[:, 1:] != Xs[:, :-1]
    start = np.maximum.accumulate(np.where(newg, idx, 0), axis=1)
    endg = np.ones((R, n), bool)
    endg[:, :-1] = Xs[:, :-1] != Xs[:, 1:]
    end = np.minimum.accumulate(np.where(endg, idx, n - 1)[:, ::-1], axis=1)[:, ::-1]
    rs = (start + end) / 2.0 + 1.0
    ranks = np.empty((R, n))
    np.put_along_axis(ranks, order, rs, axis=1)
    return ranks


def tie_term_2d(X):
    """Per row: sum over tie groups of (t^3 - t)."""
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    R, n = X.shape
    Xs = np.sort(X, axis=1, kind="mergesort")
    newg = np.ones((R, n), bool)
    newg[:, 1:] = Xs[:, 1:] != Xs[:, :-1]
    out = np.zeros(R)
    for r in range(R):
        st = np.flatnonzero(newg[r])
        t = np.diff(np.append(st, n)).astype(np.float64)
        out[r] = float((t ** 3 - t).sum())
    return out


def strict_order_2d(X, names):
    """Rank order per row: value descending, ties broken by name ascending (Python string order).
    Returns (order, pos): order[r, k] = column at rank k+1; pos[r, j] = 0-based rank of column j."""
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    R, n = X.shape
    perm = np.array(sorted(range(n), key=lambda j: names[j]), dtype=np.int64)
    o = np.argsort(-X[:, perm], axis=1, kind="stable")
    order = perm[o]
    pos = np.empty((R, n), dtype=np.int64)
    np.put_along_axis(pos, order, np.broadcast_to(np.arange(n), (R, n)).copy(), axis=1)
    return order, pos


def pearson_rows(A, B):
    A = np.atleast_2d(A); B = np.atleast_2d(B)
    a = A - A.mean(axis=1, keepdims=True)
    b = B - B.mean(axis=1, keepdims=True)
    num = (a * b).sum(axis=1)
    den = np.sqrt((a * a).sum(axis=1) * (b * b).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    return out


def spearman_rows(XA, XB):
    """Spearman's rho on average ranks = Pearson correlation of the average ranks (per row)."""
    return pearson_rows(avg_ranks_2d(XA), avg_ranks_2d(XB))


def spearman_1d(x, y):
    return float(spearman_rows(np.asarray(x)[None, :], np.asarray(y)[None, :])[0])


def kendall_tau_b_rows(XA, XB, chunk=100):
    """Kendall's tau-b with the tie correction: S / sqrt((n0 - n1)(n0 - n2)), per row."""
    XA = np.atleast_2d(XA); XB = np.atleast_2d(XB)
    R, n = XA.shape
    iu, ju = np.triu_indices(n, k=1)
    n0 = float(len(iu))
    out = np.empty(R)
    for s in range(0, R, chunk):
        e = min(R, s + chunk)
        a = np.sign(XA[s:e][:, iu] - XA[s:e][:, ju]).astype(np.int8)
        b = np.sign(XB[s:e][:, iu] - XB[s:e][:, ju]).astype(np.int8)
        S = (a.astype(np.int16) * b).sum(axis=1, dtype=np.int64).astype(np.float64)
        n1 = (a == 0).sum(axis=1).astype(np.float64)
        n2 = (b == 0).sum(axis=1).astype(np.float64)
        den = np.sqrt((n0 - n1) * (n0 - n2))
        with np.errstate(invalid="ignore", divide="ignore"):
            out[s:e] = np.where(den > 0, S / np.where(den > 0, den, 1.0), np.nan)
    return out


def rbo_rows(posA, posB, p):
    """RBO, eq. 32 of Webber, Moffat and Zobel (2010) for two full rankings of the same n items (equal length),
    i.e. its finite form: (1-p) sum_{d=1..n} p^(d-1) A_d + p^n A_n, A_d = |S_{:d} & T_{:d}| / d."""
    posA = np.atleast_2d(posA); posB = np.atleast_2d(posB)
    R, n = posA.shape
    m = np.maximum(posA, posB)                      # an item is in both depth-d prefixes iff m <= d-1
    flat = (m + n * np.arange(R)[:, None]).ravel()
    cnt = np.bincount(flat, minlength=R * n).reshape(R, n)
    X = np.cumsum(cnt, axis=1).astype(np.float64)   # X[:, d-1] = overlap at depth d
    d = np.arange(1, n + 1, dtype=np.float64)
    A = X / d
    w = (1.0 - p) * np.power(p, d - 1.0)
    return (A * w).sum(axis=1) + (p ** n) * A[:, -1]


def jaccard_topk_rows(posA, posB, k):
    posA = np.atleast_2d(posA); posB = np.atleast_2d(posB)
    n = posA.shape[1]
    kk = min(k, n)
    inter = ((posA < kk) & (posB < kk)).sum(axis=1).astype(np.float64)
    return inter / (2.0 * kk - inter)


def kendall_w_rows(X_list):
    """Kendall's W with the tie correction over m rankings (list of (R, n) arrays of importances):
    W = 12 S / (m^2 (n^3 - n) - m sum_i T_i), T_i = sum_g (t_g^3 - t_g), on average ranks."""
    m = len(X_list)
    R, n = np.atleast_2d(X_list[0]).shape
    ranks = [avg_ranks_2d(X) for X in X_list]
    Rs = np.sum(ranks, axis=0)
    S = ((Rs - m * (n + 1) / 2.0) ** 2).sum(axis=1)
    T = np.sum([tie_term_2d(X) for X in X_list], axis=0)
    den = m * m * (n ** 3 - n) - m * T
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, 12.0 * S / np.where(den > 0, den, 1.0), np.nan)


# ------------------------------------------------------------------ intervals and JSON helpers
def pct_ci(x):
    """Percentile 95% interval of the finite replicates (numpy's default linear interpolation)."""
    x = np.asarray(x, dtype=np.float64)
    f = np.isfinite(x)
    nf = int(f.sum())
    if nf == 0:
        return None, None, 0
    lo, hi = np.percentile(x[f], [2.5, 97.5])
    return float(lo), float(hi), nf


def fnum(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


class Out(object):
    """Builds interval objects and records their per-draw arrays under their JSON path."""

    def __init__(self):
        self.npz = {}

    def iv(self, path, value, draws, value_why=None):
        v = fnum(value)
        obj = {"value": v}
        if v is None:
            obj["value_why"] = value_why or "The number is not finite on the full sample."
        arr = np.asarray(draws, dtype=np.float64).copy()
        arr[~np.isfinite(arr)] = np.nan
        lo, hi, nf = pct_ci(arr)
        obj["ci_low"] = lo
        obj["ci_high"] = hi
        obj["n_finite"] = nf
        if lo is None:
            obj["ci_low_why"] = "No draw gives a finite value."
            obj["ci_high_why"] = "No draw gives a finite value."
        if arr.shape != (N_DRAWS,):
            raise ValueError("draw array of %s has shape %r" % ("/".join(path), arr.shape))
        self.npz["/".join(path)] = arr
        return obj

    @staticmethod
    def iv_noci(value, why, value_why=None):
        v = fnum(value)
        obj = {"value": v, "ci_low": None, "ci_high": None, "n_finite": None,
               "ci_low_why": why, "ci_high_why": why, "n_finite_why": why}
        if v is None:
            obj["value_why"] = value_why or "The number is not finite on the full sample."
        return obj

    def players(self, path, names, I_f, I_d, s_f, s_d, S_f, S_d, det, det_why=None):
        """Per-player map: I, share, signed_mean (interval objects) and sign_determined."""
        key = "/".join(path)
        n = len(names)
        out = {}
        for arr_name, arr in (("I", I_d), ("share", s_d), ("signed_mean", S_d)):
            a = np.asarray(arr, dtype=np.float64).copy()
            a[~np.isfinite(a)] = np.nan
            if a.shape != (N_DRAWS, n):
                raise ValueError("players %s/%s shape %r" % (key, arr_name, a.shape))
            self.npz[key + "/" + arr_name] = a
        self.npz[key + "/names"] = np.array(list(names))
        for j, nm in enumerate(names):
            e = {}
            for lab, full, arr in (("I", I_f, I_d), ("share", s_f, s_d), ("signed_mean", S_f, S_d)):
                v = fnum(full[j])
                col = np.asarray(arr[:, j], dtype=np.float64)
                lo, hi, nf = pct_ci(col)
                o = {"value": v, "ci_low": lo, "ci_high": hi, "n_finite": nf}
                if v is None:
                    o["value_why"] = "The number is not finite on the full sample."
                if lo is None:
                    o["ci_low_why"] = "No draw gives a finite value."
                    o["ci_high_why"] = "No draw gives a finite value."
                e[lab] = o
            d = det[j]
            e["sign_determined"] = None if d is None else bool(d)
            if d is None:
                e["sign_determined_why"] = det_why or "The signed mean has no finite interval."
            out[nm] = e
        return out


def determined(S_draws):
    """Section 8: 'determined: the bootstrap 95% interval of the signed mean excludes 0' (strictly)."""
    det = []
    for j in range(S_draws.shape[1]):
        lo, hi, nf = pct_ci(S_draws[:, j])
        det.append(None if lo is None else bool(lo > 0.0 or hi < 0.0))
    return det


def topk_list(names, order_row, shares, k):
    out = []
    for j in order_row[:k]:
        out.append([names[j], float(shares[j])])
    return out
