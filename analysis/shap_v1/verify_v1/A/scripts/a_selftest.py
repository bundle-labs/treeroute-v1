# Round 14, implementer A: checks of the statistic code on constructed examples (no real data).
# scipy is used here only as an outside reference for the checks.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
import a_lib as L

fails = []


def check(label, ok, detail=""):
    print("%-70s %s %s" % (label, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(label)


def main():
    rng = np.random.default_rng(12345)  # toy data only
    # 1. average ranks vs scipy.rankdata, with ties
    X = rng.integers(0, 5, size=(50, 17)).astype(float)
    r = L.avg_ranks_2d(X)
    ref = np.vstack([stats.rankdata(x, method="average") for x in X])
    check("average ranks equal scipy.rankdata (ties)", np.array_equal(r, ref))
    # 2. Spearman vs scipy on tied toy data
    x = np.array([0.0, 0.0, 0.0, 1.0, 2.0, 2.0, 3.0, 5.0, 5.0, 7.0])
    y = np.array([0.0, 1.0, 0.0, 0.0, 2.0, 3.0, 3.0, 4.0, 6.0, 6.0])
    rho = L.spearman_1d(x, y)
    check("Spearman equals scipy.spearmanr on a tied toy case", abs(rho - stats.spearmanr(x, y).correlation) < 1e-14,
          "%r vs %r" % (rho, stats.spearmanr(x, y).correlation))
    A = rng.integers(0, 4, size=(30, 12)).astype(float)
    Bm = rng.integers(0, 4, size=(30, 12)).astype(float)
    sp = L.spearman_rows(A, Bm)
    ref = np.array([stats.spearmanr(a, b).correlation for a, b in zip(A, Bm)])
    check("Spearman rows equal scipy (30 random tied cases)", np.allclose(sp, ref, atol=1e-14, rtol=0, equal_nan=True))
    # 3. Kendall tau-b vs scipy
    tb = L.kendall_tau_b_rows(x[None, :], y[None, :])[0]
    check("Kendall tau-b equals scipy.kendalltau (variant b) on the tied toy case",
          abs(tb - stats.kendalltau(x, y, variant="b").correlation) < 1e-14,
          "%r vs %r" % (tb, stats.kendalltau(x, y, variant="b").correlation))
    tbr = L.kendall_tau_b_rows(A, Bm, chunk=7)
    ref = np.array([stats.kendalltau(a, b, variant="b").correlation for a, b in zip(A, Bm)])
    check("Kendall tau-b rows equal scipy (30 random tied cases, chunked)", np.allclose(tbr, ref, atol=1e-14, rtol=0, equal_nan=True))
    # constant vector: undefined
    check("Spearman of a constant vector is undefined (NaN)", np.isnan(L.spearman_1d(np.zeros(5), np.arange(5.0))))
    # 4. RBO: a ranking with itself is 1; reversed and a direct prefix computation
    for n in (5, 37, 120, 503):
        names = ["p%03d" % i for i in range(n)]
        v = rng.random(n)
        o, pos = L.strict_order_2d(v[None, :], names)
        for p in (0.9, 0.95):
            r1 = L.rbo_rows(pos, pos, p)[0]
            check("RBO(p=%.2f) of a ranking of %d with itself is 1" % (p, n), abs(r1 - 1.0) < 1e-12, repr(r1))
    n = 12
    names = ["n%02d" % i for i in range(n)]
    v1 = rng.random(n); v2 = rng.random(n)
    o1, p1 = L.strict_order_2d(v1[None, :], names)
    o2, p2 = L.strict_order_2d(v2[None, :], names)
    for p in (0.9, 0.95):
        direct = 0.0
        for d in range(1, n + 1):
            Ad = len(set(o1[0, :d]) & set(o2[0, :d])) / d
            direct += (1 - p) * p ** (d - 1) * Ad
        direct += p ** n * (len(set(o1[0]) & set(o2[0])) / n)
        got = L.rbo_rows(p1, p2, p)[0]
        check("RBO(p=%.2f) equals the direct prefix sum (n=12)" % p, abs(got - direct) < 1e-14, "%r vs %r" % (got, direct))
    # reversed list of 2 items: A1 = 0, A2 = 1 -> (1-p)*p*1 + p^2
    o, pa = L.strict_order_2d(np.array([[2.0, 1.0]]), ["a", "b"])
    o, pb = L.strict_order_2d(np.array([[1.0, 2.0]]), ["a", "b"])
    check("RBO of a reversed pair is (1-p)p + p^2", abs(L.rbo_rows(pa, pb, 0.9)[0] - (0.1 * 0.9 + 0.81)) < 1e-15)
    # 5. strict order: ties broken by name ascending
    o, pos = L.strict_order_2d(np.array([[1.0, 3.0, 1.0, 3.0, 0.0]]), ["e", "d", "c", "b", "a"])
    names = ["e", "d", "c", "b", "a"]
    check("strict order: value descending, ties by name ascending",
          [names[j] for j in o[0]] == ["b", "d", "c", "e", "a"], str([names[j] for j in o[0]]))
    # 6. Kendall's W: textbook identity without ties, (mW-1)/(m-1) = mean pairwise Spearman
    m, n = 4, 9
    Xs = [rng.permutation(n).astype(float)[None, :] for _ in range(m)]
    W = L.kendall_w_rows(Xs)[0]
    pairs = [L.spearman_1d(Xs[i][0], Xs[j][0]) for i in range(m) for j in range(i + 1, m)]
    check("W without ties satisfies (mW-1)/(m-1) = mean pairwise Spearman",
          abs((m * W - 1) / (m - 1) - np.mean(pairs)) < 1e-12, "%r vs %r" % ((m * W - 1) / (m - 1), np.mean(pairs)))
    # textbook: 3 judges, identical rankings -> W = 1; with ties identical -> W = 1
    Xi = [np.array([[1.0, 2, 3, 4, 5]])] * 3
    check("W of identical rankings is 1", abs(L.kendall_w_rows(Xi)[0] - 1.0) < 1e-12)
    Xt = [np.array([[1.0, 1, 3, 4, 4]])] * 3
    check("W of identical tied rankings is 1 (tie correction)", abs(L.kendall_w_rows(Xt)[0] - 1.0) < 1e-12,
          repr(L.kendall_w_rows(Xt)[0]))
    # textbook example (Siegel & Castellan style): 3 judges, 6 objects
    Xtb = [np.array([[1.0, 6, 3, 2, 5, 4]]), np.array([[1.0, 5, 6, 4, 2, 3]]), np.array([[6.0, 3, 2, 5, 4, 1]])]
    Rj = np.sum([x[0] for x in Xtb], axis=0)
    Sref = ((Rj - Rj.mean()) ** 2).sum()
    Wref = 12 * Sref / (9 * (216 - 6))
    check("W equals 12S/(m^2(n^3-n)) on a 3x6 textbook case", abs(L.kendall_w_rows(Xtb)[0] - Wref) < 1e-14,
          "%r vs %r" % (L.kendall_w_rows(Xtb)[0], Wref))
    # 7. region weighting: each region weighs 1; shares sum to 1
    reg = np.array([0, 0, 0, 1, 2, 2])
    phi = np.array([[1.0], [1.0], [1.0], [4.0], [0.0], [2.0]])
    M, has, cnt = L.region_mean_matrix(reg, 3)
    I = (M @ np.abs(phi)).mean(axis=0)
    check("I_m(j) weighs each region 1 (mean of region means)", abs(I[0] - (1.0 + 4.0 + 1.0) / 3.0) < 1e-15, repr(I))
    c = L.draw_counts(np.array([[0, 0, 1], [2, 2, 2]]), 3)
    Istar = (c / 3.0) @ (M @ np.abs(phi))
    check("a region drawn twice weighs 2 in a draw", abs(Istar[0, 0] - (1 + 1 + 4) / 3.0) < 1e-15 and abs(Istar[1, 0] - 1.0) < 1e-15,
          repr(Istar))
    sh = rng.random(40); sh = sh / sh.sum()
    check("shares sum to 1", abs(sh.sum() - 1.0) < 1e-12)
    # 8. percentile interval of finite replicates
    x = np.array([np.nan] + list(range(1, 101)), dtype=float)
    lo, hi, nf = L.pct_ci(x)
    check("percentile interval drops non-finite replicates and counts them", nf == 100 and abs(lo - np.percentile(np.arange(1, 101), 2.5)) < 1e-12)
    # 9. Jaccard top-k from positions
    o, pa = L.strict_order_2d(np.array([[5.0, 4, 3, 2, 1, 0]]), list("abcdef"))
    o, pb = L.strict_order_2d(np.array([[0.0, 4, 3, 2, 1, 5]]), list("abcdef"))
    check("Jaccard top-2 of {a,b} and {f,b} is 1/3", abs(L.jaccard_topk_rows(pa, pb, 2)[0] - 1.0 / 3.0) < 1e-15)
    # 10. tie term
    check("tie term of [1,1,2,3,3,3] is (8-2)+(27-3)=30", L.tie_term_2d(np.array([[1.0, 1, 2, 3, 3, 3]]))[0] == 30.0)
    print("SELFTEST", "PASSED" if not fails else "FAILED: %s" % fails)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
