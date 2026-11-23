"""Exact interventional TreeSHAP with player groups, in numpy (PROTOCOL.md section 5).

For one tree f, one explained row x and its background rows B (weights w_b, summing to 1), the value of a coalition
S of players is v(S) = sum_b w_b f(x_S, b_notS): the players in S take x's values, every other player takes b's.
phi_j(x) = sum_b w_b phi_j(x; b), where phi_j(x; b) is the baseline Shapley value of the pair (x, b). It is computed
exactly by walking the hybrid points of the pair: where x and b go the same way the walk follows; where they differ
on a player not yet assigned, the walk splits (player from x, or from b); an assigned player follows its source.
At a leaf reached with a players from x and c players from b, each x player gets +v (a-1)! c! / (a+c)! and each b
player -v a! (c-1)! / (a+c)!. Additivity is exact: sum_j phi_j(x) = f(x) - sum_b w_b f(b).

A player may own several columns (an exact duplicate column, or a value column and its missing flag): the walk then
treats all of them as one player. Tree kinds:
  'le'    x <= threshold (scikit-learn and oneDAL trees, HistGradientBoosting predictors); thresholds float64,
          inputs float32 values compared as float64; NaN goes by missing_go_to_left when given (never met here:
          every model reads 0-filled inputs)
  'lgbm'  LightGBM's decision rule with its missing types (None / Zero / NaN) and default_left
Leaf values are taken exactly as the model returns them (float32-rounded where the model predicts in float32: the
treeroute bank answers and oneDAL forests).
"""
import math
from itertools import combinations

import numpy as np

MAX_PAIRS = 20000                 # pairs per chunk before the adaptive split
MAX_STATE_ELEMS = 3.0e7           # frontier states x assigned-player columns before a chunk is split
_ZERO = 1e-35                     # LightGBM's kZeroThreshold


def _wtab(d):
    wp = np.zeros((d + 1, d + 1))
    wm = np.zeros((d + 1, d + 1))
    for a in range(d + 1):
        for b in range(d + 1):
            if a:
                wp[a, b] = math.factorial(a - 1) * math.factorial(b) / math.factorial(a + b)
            if b:
                wm[a, b] = math.factorial(a) * math.factorial(b - 1) / math.factorial(a + b)
    return wp, wm


_WP, _WM = _wtab(96)


# ------------------------------------------------------------------------------------------------- tree containers
def from_sklearn(tree_, leaf_float32=False):
    """A fitted scikit-learn tree_ (DecisionTreeRegressor, or a oneDAL forest member converted by sklearnex).
    leaf_float32: round leaf values to float32 (the treeroute bank answers and oneDAL predictions are float32)."""
    val = np.asarray(tree_.value).reshape(tree_.node_count, -1)[:, 0].astype(np.float64)
    if leaf_float32:
        val = val.astype(np.float32).astype(np.float64)
    mgl = getattr(tree_, "missing_go_to_left", None)
    return {"kind": "le", "left": np.asarray(tree_.children_left, np.int64),
            "right": np.asarray(tree_.children_right, np.int64),
            "feat": np.asarray(tree_.feature, np.int64), "thr": np.asarray(tree_.threshold, np.float64),
            "val": val, "mgl": None if mgl is None else np.asarray(mgl, bool),
            "cover": np.asarray(tree_.n_node_samples, np.float64)}


def from_arrays(left, right, feat, thr, val, leaf_float32=False):
    val = np.asarray(val, np.float64)
    if leaf_float32:
        val = val.astype(np.float32).astype(np.float64)
    return {"kind": "le", "left": np.asarray(left, np.int64), "right": np.asarray(right, np.int64),
            "feat": np.asarray(feat, np.int64), "thr": np.asarray(thr, np.float64), "val": val, "mgl": None}


def from_hgb(nodes):
    """One HistGradientBoosting predictor's node array (sklearn 1.6: value, count, feature_idx, num_threshold,
    missing_go_to_left, left, right, is_leaf, ...). Numerical splits only (refused otherwise)."""
    if "is_categorical" in nodes.dtype.names and np.asarray(nodes["is_categorical"]).any():
        raise ValueError("categorical HGB split: not handled")
    leaf = np.asarray(nodes["is_leaf"], bool)
    left = np.where(leaf, -1, np.asarray(nodes["left"], np.int64))
    right = np.where(leaf, -1, np.asarray(nodes["right"], np.int64))
    return {"kind": "le", "left": left, "right": right, "feat": np.asarray(nodes["feature_idx"], np.int64),
            "thr": np.asarray(nodes["num_threshold"], np.float64), "val": np.asarray(nodes["value"], np.float64),
            "mgl": np.asarray(nodes["missing_go_to_left"], bool), "cover": np.asarray(nodes["count"], np.float64)}


def from_lgbm(tree_info):
    """One tree of lightgbm.Booster.dump_model()['tree_info'] (pre-order node ids; leaves have left = -1)."""
    L, R, F, T, V, DL, MT, CV = [], [], [], [], [], [], [], []

    def walk(nd):
        i = len(L)
        for a in (L, R, F, T, V, DL, MT, CV):
            a.append(None)
        if "leaf_value" in nd:
            L[i] = R[i] = -1
            F[i], T[i], V[i], DL[i], MT[i] = 0, 0.0, float(nd["leaf_value"]), True, 0
            CV[i] = float(nd.get("leaf_count", 0))
            return i
        if nd.get("decision_type", "<=") != "<=":
            raise ValueError("categorical LightGBM split: not handled")
        F[i], T[i], V[i] = int(nd["split_feature"]), float(nd["threshold"]), 0.0
        DL[i] = bool(nd["default_left"])
        MT[i] = {"None": 0, "Zero": 1, "NaN": 2}[nd["missing_type"]]
        CV[i] = float(nd.get("internal_count", 0))
        L[i] = walk(nd["left_child"])
        R[i] = walk(nd["right_child"])
        return i
    walk(tree_info["tree_structure"])
    return {"kind": "lgbm", "left": np.array(L, np.int64), "right": np.array(R, np.int64),
            "feat": np.array(F, np.int64), "thr": np.array(T, np.float64), "val": np.array(V, np.float64),
            "dl": np.array(DL, bool), "mt": np.array(MT, np.int8), "cover": np.array(CV, np.float64)}


def goes_left(T, node, v):
    if T["kind"] == "le":
        r = v <= T["thr"][node]
        mgl = T.get("mgl")
        if mgl is not None:
            nan = np.isnan(v)
            if nan.any():
                r = np.where(nan, mgl[node], r)
        return r
    mt = T["mt"][node]
    isnan = np.isnan(v)
    vv = np.where(isnan & (mt != 2), 0.0, v)
    miss = ((mt == 1) & (np.abs(vv) <= _ZERO)) | ((mt == 2) & isnan)
    return np.where(miss, T["dl"][node], vv <= T["thr"][node])


def predict(T, X):
    """The tree's value on every row of X (float64 rows)."""
    node = np.zeros(X.shape[0], np.int64)
    act = np.arange(X.shape[0])
    while act.size:
        nd = node[act]
        inner = T["left"][nd] >= 0
        act, nd = act[inner], nd[inner]
        if not act.size:
            break
        go = goes_left(T, nd, X[act, T["feat"][nd]])
        node[act] = np.where(go, T["left"][nd], T["right"][nd])
    return T["val"][node]


def depth(T):
    d = np.zeros(T["left"].size, np.int64)
    out = 0
    stack = [0]
    while stack:
        i = stack.pop()
        if T["left"][i] >= 0:
            for c in (T["left"][i], T["right"][i]):
                d[c] = d[i] + 1
                stack.append(c)
        else:
            out = max(out, int(d[i]))
    return out


# ------------------------------------------------------------------------------------------------- the walk
class _TooBig(Exception):
    pass


def _chunk(T, X, BG, px, pb, pw, poc, phi):
    nplay = phi.shape[1]
    left, right, val = T["left"], T["right"], T["val"]
    n = px.size
    sp = np.arange(n)
    node = np.zeros(n, np.int64)
    na = np.zeros(n, np.int64)
    nb = np.zeros(n, np.int64)
    ap = np.full((n, 0), -1, np.int32)
    asrc = np.zeros((n, 0), np.int8)
    flat = phi.reshape(-1)
    while sp.size:
        leaf = left[node] < 0
        if leaf.any():
            li = np.flatnonzero(leaf & ((na + nb) > 0))
            if li.size:
                v = val[node[li]] * pw[sp[li]]
                a, b = na[li], nb[li]
                cp, cm = v * _WP[a, b], -v * _WM[a, b]
                rows = px[sp[li]]
                for k in range(ap.shape[1]):
                    pk = ap[li, k]
                    m = pk >= 0
                    if m.any():
                        idx = rows[m] * nplay + pk[m]
                        w = np.where(asrc[li, k] == 0, cp, cm)[m]
                        flat += np.bincount(idx, weights=w, minlength=flat.size)
            keep = ~leaf
            sp, node, na, nb, ap, asrc = sp[keep], node[keep], na[keep], nb[keep], ap[keep], asrc[keep]
            if not sp.size:
                break
        f = T["feat"][node]
        pl = poc[f]
        gx = goes_left(T, node, X[px[sp], f])
        gb = goes_left(T, node, BG[pb[sp], f])
        if ap.shape[1]:
            hit = ap == pl[:, None]
            has = hit.any(1)
            src = np.where(has, asrc[np.arange(sp.size), hit.argmax(1)], -1)
        else:
            has = np.zeros(sp.size, bool)
            src = np.full(sp.size, -1)
        go = np.where(src == 1, gb, gx)
        nxt = np.where(go, left[node], right[node])
        split = (~has) & (gx != gb)
        if split.any():
            si = np.flatnonzero(split)
            ap = np.concatenate([ap, np.full((ap.shape[0], 1), -1, np.int32)], 1)
            asrc = np.concatenate([asrc, np.zeros((asrc.shape[0], 1), np.int8)], 1)
            c = ap.shape[1] - 1
            ap[si, c] = pl[si]
            asrc[si, c] = 0
            na2 = na.copy()
            na2[si] += 1
            nx = nxt.copy()
            nx[si] = np.where(gx[si], left[node[si]], right[node[si]])
            apb = ap[si].copy()
            asb = asrc[si].copy()
            asb[:, c] = 1
            nxb = np.where(gb[si], left[node[si]], right[node[si]])
            sp = np.concatenate([sp, sp[si]])
            node = np.concatenate([nx, nxb])
            na = np.concatenate([na2, na[si]])
            nb = np.concatenate([nb, nb[si] + 1])
            ap = np.concatenate([ap, apb])
            asrc = np.concatenate([asrc, asb])
            if float(ap.shape[0]) * ap.shape[1] > MAX_STATE_ELEMS and px.size > 1:
                raise _TooBig()
        else:
            node = nxt


def itreeshap(T, X, BG, px, pb, pw, poc, nplay, phi=None):
    """Exact interventional SHAP of one tree.
    X (n_x, C) and BG (n_b, C): float64 rows as the tree compares them. px, pb: the explained-row and background-row
    index of every pair; pw: the pair weight (1/|B_i|). poc (C,): the player of every column. Adds into phi
    (n_x, nplay) and returns it."""
    if phi is None:
        phi = np.zeros((X.shape[0], nplay))
    px = np.asarray(px, np.int64)
    pb = np.asarray(pb, np.int64)
    pw = np.asarray(pw, np.float64)
    poc = np.asarray(poc, np.int32)
    todo = [(a, min(a + MAX_PAIRS, px.size)) for a in range(0, px.size, MAX_PAIRS)]
    while todo:
        a, b = todo.pop(0)
        part = np.zeros_like(phi)
        try:
            _chunk(T, X, BG, px[a:b], pb[a:b], pw[a:b], poc, part)
        except _TooBig:
            mid = (a + b) // 2
            todo[:0] = [(a, mid), (mid, b)]
            continue
        phi += part
    return phi


# ------------------------------------------------------------------------------------------------- references for tests
def brute_force(f, x, BG, w, poc, nplay):
    """Exact Shapley values of v(S) = sum_b w_b f(x_S, b_notS) by enumeration over the players (tests only).
    f: rows (k, C) -> values (k,)."""
    cols = [np.flatnonzero(np.asarray(poc) == p) for p in range(nplay)]
    vals = {}
    for r in range(nplay + 1):
        for S in combinations(range(nplay), r):
            Z = BG.copy()
            for p in S:
                Z[:, cols[p]] = x[cols[p]]
            vals[S] = float(np.dot(w, f(Z)))
    phi = np.zeros(nplay)
    for j in range(nplay):
        others = [p for p in range(nplay) if p != j]
        for r in range(nplay):
            for S in combinations(others, r):
                wt = math.factorial(r) * math.factorial(nplay - r - 1) / math.factorial(nplay)
                phi[j] += wt * (vals[tuple(sorted(S + (j,)))] - vals[S])
    return phi


def pairs_for(bg_lists):
    """px, pb, pw for explained rows whose background rows are given as index lists into BG."""
    px, pb, pw = [], [], []
    for i, lst in enumerate(bg_lists):
        lst = np.asarray(lst, np.int64)
        if lst.size == 0:
            raise ValueError("explained row %d has no background row" % i)
        px.append(np.full(lst.size, i, np.int64))
        pb.append(lst)
        pw.append(np.full(lst.size, 1.0 / lst.size))
    return np.concatenate(px), np.concatenate(pb), np.concatenate(pw)
