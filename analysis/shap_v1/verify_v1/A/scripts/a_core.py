# Round 14, implementer A: importances and pair statistics (one code path for the main pairs and for B1).
# Choices (V\A\choices.md): J fixed at the full sample (C07); top-k sets and their unions found again on each
# draw; determined signs from the full bootstrap (fixed); ranks on I_m, ties = exact equality; names compared
# as written in the results (C10); Spearman over the top-20 union ranks within the union (C11); RBO's finite
# form (C13); TV = half the L1 distance (C14); family shares from variable-level phi (C15).
import numpy as np

import a_lib as L


class ModelLevel(object):
    pass


def union_matrix(rows, key, mat, names):
    """(n_rows x N) matrix over the union of names; a name the piece does not have is 0 on every row (C06)."""
    idx = {n: i for i, n in enumerate(names)}
    X = np.zeros((rows[mat].shape[0], len(names)))
    cols = [idx[n] for n in rows[key]]
    X[:, cols] = rows[mat]
    own = np.zeros(len(names), bool)
    own[cols] = True
    return X, own


def region_stats(X, M, Wd):
    """Region means of |phi| and phi, the full-sample importances (each region weighs 1) and per draw."""
    A = M @ np.abs(X)
    Bm = M @ X
    return A.mean(axis=0), Wd @ A, Bm.mean(axis=0), Wd @ Bm


def family_matrix(rows, var_family):
    """Row attribution of each family = sum of its variables' (variable-level) phi on that row (C15)."""
    F = np.zeros((rows["phiv"].shape[0], len(L.FAMILIES)))
    for c, v in enumerate(rows["variables"]):
        F[:, L.FAMILIES.index(var_family[v])] += rows["phiv"][:, c]
    return F


def prepare(I_f, I_d, S_f, S_d, own, jj, Jnames, fam=None):
    """Everything a model needs at one level, over the index set jj (J) of the union."""
    m = ModelLevel()
    m.I_full_all, m.I_d_all, m.own = I_f, I_d, own
    m.IJ_f = I_f[jj]
    m.IJ_d = I_d[:, jj]
    tot_f = m.IJ_f.sum()
    tot_d = m.IJ_d.sum(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        m.sh_f = m.IJ_f / tot_f if tot_f > 0 else np.full(len(jj), np.nan)
        m.sh_d = np.where(tot_d > 0, m.IJ_d / np.where(tot_d > 0, tot_d, 1.0), np.nan)
    m.SJ_f = S_f[jj]
    m.SJ_d = S_d[:, jj]
    m.det = L.determined(m.SJ_d)
    m.detb = np.array([bool(x) for x in m.det])
    m.nz_f = int((I_f[own] > 0).sum())
    m.nz_d = (I_d[:, own] > 0).sum(axis=1).astype(np.float64)
    m.order_f, m.pos_f = L.strict_order_2d(m.IJ_f[None, :], Jnames)
    m.order_d, m.pos_d = L.strict_order_2d(m.IJ_d, Jnames)
    m.rk_f = L.avg_ranks_2d(m.IJ_f[None, :])
    m.rk_d = L.avg_ranks_2d(m.IJ_d)
    m.ranking = [Jnames[j] for j in m.order_f[0]]
    m.top10 = L.topk_list(Jnames, m.order_f[0], m.sh_f, 10)
    m.top3 = L.topk_list(Jnames, m.order_f[0], m.sh_f, 3)
    if fam is not None:
        F_f, F_d = fam
        with np.errstate(invalid="ignore", divide="ignore"):
            m.fs_f = F_f / F_f.sum()
            tot = F_d.sum(axis=1, keepdims=True)
            m.fs_d = np.where(tot > 0, F_d / np.where(tot > 0, tot, 1.0), np.nan)
    else:
        m.fs_f = m.fs_d = None
    return m


def tau_b_pairs(models, pairs, chunk=50):
    """Kendall's tau-b per draw for many pairs, computing each model's pair signs once per chunk."""
    any_m = next(iter(models.values()))
    R, n = any_m.IJ_d.shape
    iu, ju = np.triu_indices(n, k=1)
    n0 = float(len(iu))
    out = {pr: np.empty(R) for pr in pairs}
    used = sorted(set([a for a, b in pairs] + [b for a, b in pairs]))
    for s in range(0, R, chunk):
        e = min(R, s + chunk)
        sg = {}
        for mname in used:
            X = models[mname].IJ_d[s:e]
            sg[mname] = np.sign(X[:, iu] - X[:, ju]).astype(np.int8)
        ties = {mname: (sg[mname] == 0).sum(axis=1).astype(np.float64) for mname in used}
        for (a, b) in pairs:
            S = (sg[a].astype(np.int16) * sg[b]).sum(axis=1, dtype=np.int64).astype(np.float64)
            den = np.sqrt((n0 - ties[a]) * (n0 - ties[b]))
            with np.errstate(invalid="ignore", divide="ignore"):
                out[(a, b)][s:e] = np.where(den > 0, S / np.where(den > 0, den, 1.0), np.nan)
    return out


def spearman_union_draws(A, B, k=20):
    R = A.IJ_d.shape[0]
    out = np.empty(R)
    for r in range(R):
        U = (A.pos_d[r] < k) | (B.pos_d[r] < k)
        out[r] = L.spearman_1d(A.IJ_d[r, U], B.IJ_d[r, U])
    return out


def pair_stats(out, path, A, B, Jnames, level, tau_d, fam_exists):
    """Section 8's pair statistics for runs A and B over J (A, B: ModelLevel; path: JSON path of the pair)."""
    d = {}
    nJ = len(Jnames)
    P = lambda k: path + [k]
    # Spearman over J
    d["spearman_J"] = out.iv(P("spearman_J"), L.pearson_rows(A.rk_f, B.rk_f)[0], L.pearson_rows(A.rk_d, B.rk_d),
                             "Spearman's rho is undefined when one ranking is all ties.")
    # Spearman over the union of the two top-20 sets (ranks within the union)
    U = (A.pos_f[0] < 20) | (B.pos_f[0] < 20)
    full_u = L.spearman_1d(A.IJ_f[U], B.IJ_f[U])
    d["spearman_top20_union"] = out.iv(P("spearman_top20_union"), full_u, spearman_union_draws(A, B, 20),
                                       "Spearman's rho is undefined when one ranking is all ties on the union.")
    d["top20_union"] = sorted(Jnames[j] for j in np.flatnonzero(U))
    # Kendall's tau-b
    full_tau = L.kendall_tau_b_rows(A.IJ_f[None, :], B.IJ_f[None, :])[0]
    d["kendall_tau_b"] = out.iv(P("kendall_tau_b"), full_tau, tau_d,
                                "Kendall's tau-b is undefined when one ranking is all ties.")
    # Jaccard
    d["jaccard_top5"] = out.iv(P("jaccard_top5"), L.jaccard_topk_rows(A.pos_f, B.pos_f, 5)[0],
                               L.jaccard_topk_rows(A.pos_d, B.pos_d, 5))
    d["jaccard_top10"] = out.iv(P("jaccard_top10"), L.jaccard_topk_rows(A.pos_f, B.pos_f, 10)[0],
                                L.jaccard_topk_rows(A.pos_d, B.pos_d, 10))
    if nJ >= 200:
        d["jaccard_top20"] = out.iv(P("jaccard_top20"), L.jaccard_topk_rows(A.pos_f, B.pos_f, 20)[0],
                                    L.jaccard_topk_rows(A.pos_d, B.pos_d, 20))
    else:
        d["jaccard_top20"] = None
        d["jaccard_top20_why"] = ("Section 8 gives the top-20 Jaccard only when J has 200 or more players; "
                                  "this J has %d." % nJ)
    # RBO
    for p, key in ((0.9, "rbo_p090"), (0.95, "rbo_p095")):
        d[key] = out.iv(P(key), L.rbo_rows(A.pos_f, B.pos_f, p)[0], L.rbo_rows(A.pos_d, B.pos_d, p))
    # total-variation distances
    d["tv_shares"] = out.iv(P("tv_shares"), 0.5 * np.abs(A.sh_f - B.sh_f).sum(),
                            0.5 * np.abs(A.sh_d - B.sh_d).sum(axis=1))
    if level == "variable":
        ex = np.array(fam_exists, bool)
        d["tv_family_shares"] = out.iv(P("tv_family_shares"), 0.5 * np.abs(A.fs_f - B.fs_f)[ex].sum(),
                                       0.5 * np.abs(A.fs_d - B.fs_d)[:, ex].sum(axis=1))
    else:
        d["tv_family_shares"] = None
        d["tv_family_shares_why"] = ("Family shares are formed from variable-level phi (section 8: 'the sum of its "
                                     "variables' (variable-level) phi'), so they have no feature-level version; "
                                     "their distance is reported at the variable level.")
    # sign agreement on the union of the two top-10 sets, among players determined in both
    U10 = (A.pos_f[0] < 10) | (B.pos_f[0] < 10)
    D = U10 & A.detb & B.detb
    agree = D & (np.sign(A.SJ_f) == np.sign(B.SJ_f))
    n_det, n_agr = int(D.sum()), int(agree.sum())
    U10d = (A.pos_d < 10) | (B.pos_d < 10)
    Dd = U10d & A.detb[None, :] & B.detb[None, :]
    agd = Dd & (np.sign(A.SJ_d) == np.sign(B.SJ_d))
    nd = Dd.sum(axis=1).astype(np.float64)
    na = agd.sum(axis=1).astype(np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        frac_d = np.where(nd > 0, na / np.where(nd > 0, nd, 1.0), np.nan)
    d["sign_agreement"] = out.iv(P("sign_agreement"), (n_agr / n_det) if n_det > 0 else None, frac_d,
                                 "No player of the union of the two top-10 sets has its sign determined in both models.")
    d["sign_n_determined"] = out.iv(P("sign_n_determined"), n_det, nd)
    d["sign_n_agree"] = out.iv(P("sign_n_agree"), n_agr, na)
    d["sign_union_top10"] = sorted(Jnames[j] for j in np.flatnonzero(U10))
    d["sign_determined_both"] = sorted(Jnames[j] for j in np.flatnonzero(D))
    # diagnostics for the reconciler (not matched): alternative readings on the full sample
    rkA = A.rk_f[0][U]; rkB = B.rk_f[0][U]
    d["extra"] = {"spearman_top20_union_ranks_carried_from_J": L.fnum(L.pearson_rows(rkA[None], rkB[None])[0]),
                  "top20_union_size": int(U.sum()), "sign_union_top10_size": int(U10.sum())}
    return d
