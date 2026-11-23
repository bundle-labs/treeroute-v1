# Implementer B, round 14: checks of the statistics code on constructed examples (no project data except the
# saved draw matrices, whose generator is checked against the protocol's description).
import os
import sys
import itertools

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import stats
import b_lib as L

fails = []


def check(name, ok, detail=""):
    print("%-70s %s %s" % (name, "ok" if ok else "FAIL", detail))
    if not ok:
        fails.append(name)


# 1. Spearman with ties against scipy
X = np.array([[3, 1, 2, 2, 5, 0, 0], [1, 1, 1, 2, 2, 3, 4], [0.5, 0.5, 0.5, 0.5, 1, 2, 3]], dtype=float)
Y = np.array([[1, 2, 2, 3, 4, 0, 0], [4, 3, 3, 2, 2, 1, 0], [0.1, 0.2, 0.2, 0.3, 0.4, 0.5, 0.5]], dtype=float)
mine = L.spearman_rows(X, Y)
ref = np.array([stats.spearmanr(X[i], Y[i]).correlation for i in range(3)])
check("Spearman (average ranks, ties) equals scipy.spearmanr", np.allclose(mine, ref, atol=1e-14, rtol=0), str(mine))
check("Spearman of all-tied input is NaN", np.isnan(L.spearman_rows(np.ones((1, 4)), X[:1, :4]))[0])

# 2. Spearman on a masked subset equals the subset's own Spearman
M = np.array([[1, 1, 0, 1, 1, 0, 1], [0, 1, 1, 1, 1, 1, 0], [1, 1, 1, 0, 0, 1, 1]], dtype=bool)
mm = L.spearman_masked(X, Y, M)
rr = np.array([stats.spearmanr(X[i][M[i]], Y[i][M[i]]).correlation for i in range(3)])
check("masked Spearman equals scipy on the subset (ranks within the subset)", np.allclose(mm, rr, atol=1e-14, rtol=0), str(mm))

# 3. Kendall tau-b with ties against scipy
taus = L.kendall_tau_b_all({"a": X, "b": Y}, [("a", "b")])[("a", "b")]
ref = np.array([stats.kendalltau(X[i], Y[i], variant="b").correlation for i in range(3)])
check("Kendall tau-b (ties) equals scipy.kendalltau variant b", np.allclose(taus, ref, atol=1e-14, rtol=0), str(taus))
rng = np.random.default_rng(12345)  # constructed example only (no seed is used on project data)
A = rng.integers(0, 6, size=(5, 40)).astype(float)
Bm = rng.integers(0, 6, size=(5, 40)).astype(float)
t2 = L.kendall_tau_b_all({"a": A, "b": Bm}, [("a", "b")], chunk=2)[("a", "b")]
ref2 = np.array([stats.kendalltau(A[i], Bm[i], variant="b").correlation for i in range(5)])
check("Kendall tau-b, heavy ties, chunked", np.allclose(t2, ref2, atol=1e-13, rtol=0))


# 4. RBO
def rbo_direct(la, lb, p):
    """Eq. 32 of Webber et al. (2010) written out for lists la (length l) and lb (length s), s <= l."""
    if len(la) < len(lb):
        la, lb = lb, la
    l, s = len(la), len(lb)
    Xd = [len(set(la[:d]) & set(lb[:d])) for d in range(1, l + 1)]
    Xs = Xd[s - 1]
    Xl = Xd[l - 1]
    sum1 = sum(Xd[d - 1] / d * p ** d for d in range(1, l + 1))
    sum2 = sum(Xs * (d - s) / (s * d) * p ** d for d in range(s + 1, l + 1))
    return (1 - p) / p * (sum1 + sum2) + ((Xl - Xs) / l + Xs / s) * p ** l


n = 30
idx = np.arange(n)
order_a = idx[None, :]
for p in (0.9, 0.95):
    pa = L.positions(order_a)
    check("RBO of a ranking with itself is 1 (p=%.2f)" % p, abs(L.rbo_rows(pa, pa, p)[0] - 1.0) < 1e-14,
          repr(L.rbo_rows(pa, pa, p)[0]))
    rev = idx[::-1][None, :]
    v = L.rbo_rows(pa, L.positions(rev), p)[0]
    d = rbo_direct(list(idx), list(idx[::-1]), p)
    check("RBO reversed ranking equals the direct eq. 32 (p=%.2f)" % p, abs(v - d) < 1e-14, "%r %r" % (v, d))
    perm = rng.permutation(n)
    v = L.rbo_rows(pa, L.positions(perm[None, :]), p)[0]
    d = rbo_direct(list(idx), list(perm), p)
    check("RBO random permutation equals the direct eq. 32 (p=%.2f)" % p, abs(v - d) < 1e-14, "%r %r" % (v, d))
# ties broken by name: equal importances keep name order
I = np.array([[0.3, 0.1, 0.3, 0.0, 0.0]])
o = L.order_by_importance(I)
check("ties broken by name (stable order of name-sorted columns)", o[0].tolist() == [0, 2, 1, 3, 4], str(o))
check("negative zero ties with zero", L.order_by_importance(np.array([[0.0, -0.0, 0.1]]))[0].tolist() == [2, 0, 1])

# 5. Jaccard
pa = L.positions(np.array([[0, 1, 2, 3, 4, 5]]))
pb = L.positions(np.array([[1, 0, 5, 4, 2, 3]]))
check("Jaccard top-2 of identical sets is 1", L.jaccard_topk(pa, pb, 2)[0] == 1.0)
check("Jaccard top-3 = 2/4", L.jaccard_topk(pa, pb, 3)[0] == 0.5)
check("Jaccard top-k with k > n is 1", L.jaccard_topk(pa, pb, 10)[0] == 1.0)

# 6. Kendall's W: closed form equals the textbook tie-corrected formula; without ties, mean Spearman = (mW-1)/(m-1)
R1 = np.array([[1, 2, 3, 4, 5, 6.0]])
R2 = np.array([[2, 1, 3, 3, 6, 5.0]])
R3 = np.array([[1, 1, 2, 4, 4, 4.0]])
w = L.kendall_w_rows([R1, R2, R3])[0]
we = L.kendall_w_explicit([R1[0], R2[0], R3[0]])
check("W closed form equals 12S/(m^2(n^3-n) - m sum T) with ties", abs(w - we) < 1e-14, "%r %r" % (w, we))
P = [rng.permutation(8).astype(float)[None, :] for _ in range(4)]
w = L.kendall_w_rows(P)[0]
ms = np.mean([L.spearman_rows(P[i], P[j])[0] for i, j in itertools.combinations(range(4), 2)])
check("no ties: mean pairwise Spearman equals (mW-1)/(m-1)", abs(ms - (4 * w - 1) / 3) < 1e-14, "%r %r" % (ms, (4 * w - 1) / 3))
Pt = [R1, R2, R3]
w = L.kendall_w_rows(Pt)[0]
ms = np.mean([L.spearman_rows(Pt[i], Pt[j])[0] for i, j in itertools.combinations(range(3), 2)])
check("unequal ties: mean pairwise Spearman differs from (mW-1)/(m-1)", abs(ms - (3 * w - 1) / 2) > 1e-6,
      "%r vs %r" % (ms, (3 * w - 1) / 2))
# textbook: identical rankings give W = 1; W of two reversed rankings is 0
check("W of identical rankings is 1", abs(L.kendall_w_rows([R1, R1, R1])[0] - 1) < 1e-14)
check("W of a ranking and its reverse is 0", abs(L.kendall_w_rows([R1, R1[:, ::-1]])[0]) < 1e-14)

# 7. Region weighting: each region weighs 1; a region drawn twice weighs 2
phi = np.array([[1.0], [-3.0], [5.0], [2.0], [2.0], [8.0]])
reg = np.array([0, 1, 1, 2, 2, 2])
Mabs, nr = L.region_means(np.abs(phi), reg, 3)
full = L.weighted_over_regions(np.ones((1, 3)), Mabs)[0, 0]
check("I = mean of the region means (each region weighs 1)", abs(full - (1 + 4 + 4) / 3) < 1e-15, repr(full))
dr = L.draw_counts(np.array([[0, 0, 2]]), 3)
v = L.weighted_over_regions(dr, Mabs)[0, 0]
check("a region drawn twice weighs 2", abs(v - (2 * 1 + 4) / 3) < 1e-15 and dr.sum() == 3, repr(v))
pres = np.array([True, False, True])
v = L.weighted_over_regions(np.ones((1, 3)), Mabs, present=pres)[0, 0]
check("item 8 weighting over the regions that have rows", abs(v - (1 + 4) / 2) < 1e-15)
v = L.weighted_over_regions(L.draw_counts(np.array([[1, 1, 1]]), 3), Mabs, present=pres)[0, 0]
check("item 8: a draw without such regions is NaN", np.isnan(v))

# 8. Shares sum to 1 over J
Iv = np.array([[0.2, 0.5, 0.3, 1e-20]])
s = Iv / Iv.sum(axis=1, keepdims=True)
check("shares sum to 1", abs(s.sum() - 1) < 1e-15)

# 9. Intervals and determined signs
d = np.concatenate([np.full(1000, 1.0), np.full(1000, 2.0)])
iv = L.interval(1.5, d)
check("percentile interval (numpy linear)", iv["ci_low"] == np.percentile(d, 2.5) and iv["n_finite"] == 2000)
d2 = d.copy()
d2[:10] = np.nan
check("non-finite draws left out and counted", L.interval(1.5, d2)["n_finite"] == 1990)
D = np.column_stack([np.linspace(-1, 1, 2000), np.linspace(0.1, 1, 2000), np.zeros(2000),
                     np.concatenate([np.linspace(-2, -1, 1900), np.zeros(100)]), np.linspace(-2, -0.01, 2000)])
check("determined: excludes 0 strictly (an end exactly 0 is not determined)",
      L.determined(D) == [False, True, False, False, True], str(L.determined(D)))

# 10. The saved draw matrices follow the protocol's SHA-256 generator, every row and column; each draw has G regions
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    dr = np.load(L.SHAP / "out" / p / "lead_0" / "compare" / "bootstrap_draws.npy")
    G = dr.shape[1]
    gen = np.array([L.generator_row(p, 0, b, G) for b in range(dr.shape[0])])
    C = L.draw_counts(dr, G)
    check("draw matrix of %s reproduced by the salt shap_v1|AW4|%s|0 (all %d rows)" % (p, p, dr.shape[0]),
          np.array_equal(gen, dr) and np.all(C.sum(axis=1) == G))

print("SELFTEST", "PASSED" if not fails else "FAILED: " + ", ".join(fails))
sys.exit(1 if fails else 0)
