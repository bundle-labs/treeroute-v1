"""Unit smoke tests (synthetic data only; no run, board or export is read). Writes smoke/unit_report.json.

  S1  statistics on constructed examples with known answers: identical, reversed and tied rankings; Spearman and
      Kendall tau-b against scipy; Kendall's W on a textbook case; the mean pairwise Spearman under unequal ties
      (where (mW - 1)/(m - 1) is only an approximation); RBO_ext against the equal-length closed form; RBO on the full
      ranking against the case that overstated the nonzero-list version; the profile path equal to the direct path;
      Jaccard and TVD by hand; percentile intervals count their finite replicates.
  S2  interventional TreeSHAP against brute-force Shapley values (all 2^M coalitions) on: a scikit-learn tree with
      float32 leaves and a merged duplicate column, a oneDAL forest member, a LightGBM booster's trees, a
      HistGradientBoosting predictor, a LightGBM model TRAINED on a duplicated column (merged map; the sum of separate
      players differs), and a grouped (variable-level) game; additivity on every row; the adaptive chunk split; a
      player equal on every background row gets exactly 0 (S-ZERO), in the walk and in the per-pair linear form.
  S3  resume records; the write guard; redaction; the register (identity, background hash); the true relative
      tolerance (D8); the variable rule on real column names; the privacy scan.
Run: py -3.9 -I -B D:/treeroute/analysis/shap_v1/scripts/tests/smoke_unit.py
"""
import os
import sys
import time
import warnings

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import shapv1_common as C  # noqa: E402

C.pin_threads(1)
import numpy as np  # noqa: E402
import shapv1_rows as RW  # noqa: E402
import shapv1_stats as ST  # noqa: E402
import shapv1_treeshap as TS  # noqa: E402

warnings.filterwarnings("ignore")
REPORT = {}
FAIL = []


def check(name, ok, value):
    REPORT[name] = {"pass": bool(ok), "value": value}
    print("%-66s %s  %s" % (name, "PASS" if ok else "FAIL", value), flush=True)
    if not ok:
        FAIL.append(name)


def s1_stats():
    from scipy import stats as SS
    a = np.array([5.0, 4, 3, 2, 1, 0.5])
    order = np.arange(a.size)
    check("S1 identical: spearman=1", ST.spearman(a, a) == 1.0, ST.spearman(a, a))
    check("S1 identical: kendall tau_b=1", abs(ST.kendall_tau_b(a, a) - 1) < 1e-15, ST.kendall_tau_b(a, a))
    check("S1 identical: jaccard@3=1, tvd=0", ST.jaccard_topk(a, a, order, 3) == 1.0 and ST.tvd(a, a) == 0.0,
          [ST.jaccard_topk(a, a, order, 3), ST.tvd(a, a)])
    check("S1 identical: RBO_ext=1, RBO full=1", abs(ST.rbo_ext(list(range(10)), list(range(10)), 0.9) - 1) < 1e-12
          and abs(ST.rbo_full(a, a, order, 0.9) - 1) < 1e-12, ST.rbo_full(a, a, order, 0.9))
    b = a[::-1].copy()
    check("S1 reversed: spearman=-1", abs(ST.spearman(a, b) + 1) < 1e-15, ST.spearman(a, b))
    check("S1 reversed: kendall=-1", abs(ST.kendall_tau_b(a, b) + 1) < 1e-15, ST.kendall_tau_b(a, b))
    check("S1 disjoint lists: RBO_ext=0", ST.rbo_ext([0, 1, 2], [3, 4, 5], 0.9) == 0.0, 0.0)
    rng = np.random.default_rng(1)
    worst_s = worst_k = worst_r = 0.0
    for _ in range(200):
        x = rng.integers(0, 6, 25).astype(float)
        y = rng.integers(0, 6, 25).astype(float)
        worst_s = max(worst_s, abs(ST.spearman(x, y) - SS.spearmanr(x, y)[0]))
        worst_k = max(worst_k, abs(ST.kendall_tau_b(x, y) - SS.kendalltau(x, y, variant="b")[0]))
        worst_r = max(worst_r, float(np.abs(ST.rankdata(x) - SS.rankdata(x)).max()))
    check("S1 ties: spearman vs scipy (200 tied cases)", worst_s < 1e-12, worst_s)
    check("S1 ties: kendall tau_b vs scipy (200 tied cases)", worst_k < 1e-12, worst_k)
    check("S1 ties: vectorised average ranks vs scipy", worst_r == 0.0, worst_r)
    M = np.array([[4, 3, 2, 1], [3, 4, 2, 1], [4, 2, 3, 1]], float)
    W = ST.kendall_w(M)
    check("S1 Kendall W textbook (rank sums 4,6,8,12 -> 0.7778)", abs(W - 420.0 / 540.0) < 1e-12, W)
    m = M.shape[0]
    check("S1 mean rho = (mW-1)/(m-1) holds WITHOUT ties", abs(ST.mean_pairwise_spearman(M) - (m * W - 1) / (m - 1))
          < 1e-12, [ST.mean_pairwise_spearman(M), (m * W - 1) / (m - 1)])
    Mt2 = np.array([[5, 4, 3, 2, 1, 0, 0, 0], [5, 3, 4, 2, 0, 0, 0, 0], [4, 5, 3, 1, 2, 1, 0, 0]], float)
    W2 = ST.kendall_w(Mt2)
    gap = abs(ST.mean_pairwise_spearman(Mt2) - (3 * W2 - 1) / 2.0)
    check("S1 unequal ties: (mW-1)/(m-1) is NOT the mean rho (reported directly)", gap > 1e-6,
          [ST.mean_pairwise_spearman(Mt2), (3 * W2 - 1) / 2.0])
    check("S1 Kendall W identical rankings = 1", abs(ST.kendall_w(np.vstack([a, a, a])) - 1) < 1e-12, 1.0)
    Mt = np.array([[3, 3, 1, 1], [3, 1, 3, 1]], float)
    check("S1 Kendall W with ties (12*8/192 = 0.5)", abs(ST.kendall_w(Mt) - 0.5) < 1e-12, ST.kendall_w(Mt))
    l1, l2, p = [0, 1, 2, 3, 4, 5], [1, 0, 2, 5, 6, 7], 0.9
    k = 6
    Xd = [len(set(l1[:d]) & set(l2[:d])) for d in range(1, k + 1)]
    closed = Xd[-1] / k * p ** k + (1 - p) / p * sum(Xd[d - 1] / d * p ** d for d in range(1, k + 1))
    check("S1 RBO_ext equal length vs closed form", abs(ST.rbo_ext(l1, l2, p) - closed) < 1e-12,
          [ST.rbo_ext(l1, l2, p), closed])
    # RBO on the full ranking equals RBO_ext of the two (tie-broken) full lists
    va, vb = rng.random(40), rng.random(40)
    o40 = np.arange(40)
    ref = ST.rbo_ext(ST.ranked(va, o40), ST.ranked(vb, o40), 0.9)
    check("S1 RBO full == RBO_ext of the full tie-broken lists", abs(ST.rbo_full(va, vb, o40, 0.9) - ref) < 1e-12,
          [ST.rbo_full(va, vb, o40, 0.9), ref])
    one = np.zeros(51)
    one[0] = 1.0
    spread = np.r_[1.0, np.linspace(0.01, 0.03, 50)]       # same top-1, the tail in the other order
    old = ST.rbo_ext([i for i in ST.ranked(one, np.arange(51)) if one[i] > 0],
                     [i for i in ST.ranked(spread, np.arange(51)) if spread[i] > 0], 0.9)
    new = ST.rbo_full(one, spread, np.arange(51), 0.9)
    check("S1 RBO: nonzero-list version overstated (1.0); full ranking does not", old > 0.999 and new < 0.5,
          [round(old, 3), round(new, 3), round(ST.tvd(one, spread), 3)])
    x = np.array([0.5, 0.3, 0.2, 0.0])
    y = np.array([0.2, 0.3, 0.5, 0.0])
    check("S1 TVD by hand (0.3)", abs(ST.tvd(x, y) - 0.3) < 1e-15, ST.tvd(x, y))
    check("S1 Jaccard@2 by hand ({0,1} vs {2,1} = 1/3)", abs(ST.jaccard_topk(x, y, np.arange(4), 2) - 1 / 3.) < 1e-15,
          ST.jaccard_topk(x, y, np.arange(4), 2))
    worst = 0.0
    for _ in range(50):
        va = np.round(rng.random(60), 1)
        vb = np.round(rng.random(60), 1)
        o = np.arange(60)
        d1 = ST.pair_stats(va, vb, o)
        d2 = ST.pair_from_profiles(ST.profile(va, o), ST.profile(vb, o))
        for kk in d1:
            if np.isfinite(d1[kk]) or np.isfinite(d2[kk]):
                worst = max(worst, abs(d1[kk] - d2[kk]))
        Mx = np.vstack([va, vb, np.round(rng.random(60), 1)])
        worst = max(worst, abs(ST.kendall_w(Mx) - ST.kendall_w_profiles([ST.profile(r, o) for r in Mx])))
    check("S1 profile path == direct path (pairs and W, 50 tied cases)", worst < 1e-12, worst)
    lo, hi, nf = ST.percentile_ci([0.1, float("nan"), 0.3, 0.2])
    check("S1 percentile interval reports its finite replicates", nf == 3 and lo <= hi, [lo, hi, nf])
    D = C.draw_matrix("unit-test", 7, 5)
    D2 = C.draw_matrix("unit-test", 7, 5)
    check("S1 bootstrap draws deterministic and in range", bool((D == D2).all() and D.min() >= 0 and D.max() < 7),
          D[0].tolist())


def s2_treeshap():
    from sklearn.tree import DecisionTreeRegressor
    rng = np.random.default_rng(20261112)
    n, Cn = 3000, 7
    X = rng.normal(size=(n, Cn)).astype(np.float32)
    X[:, 6] = X[:, 5]
    y = X[:, 0] * X[:, 1] + np.sin(X[:, 2]) + 0.5 * X[:, 5] + rng.normal(scale=0.1, size=n)
    poc = np.array([0, 1, 2, 3, 4, 5, 5])
    npl = 6
    Xe = rng.normal(size=(4, Cn)).astype(np.float32)
    Xe[:, 6] = Xe[:, 5]
    BG = rng.normal(size=(9, Cn)).astype(np.float32)
    BG[:, 6] = BG[:, 5]
    Xe64, BG64 = Xe.astype(np.float64), BG.astype(np.float64)
    bgl = [np.arange(9)] * 4
    px, pb, pw = TS.pairs_for(bgl)

    def run(T, name, fpred):
        phi = TS.itreeshap(T, Xe64, BG64, px, pb, pw, poc, npl)
        worst = 0.0
        for i in range(4):
            bf = TS.brute_force(lambda Z: TS.predict(T, Z), Xe64[i], BG64, np.full(9, 1 / 9.), poc, npl)
            worst = max(worst, float(np.abs(bf - phi[i]).max()))
        add = phi.sum(1) - (TS.predict(T, Xe64) - TS.predict(T, BG64).mean())
        same = bool(np.array_equal(TS.predict(T, Xe64), fpred(Xe)))
        check("S2 %s: brute force, additivity, evaluator == model" % name, worst < 1e-12 and
              np.abs(add).max() < 1e-12 and same, [worst, float(np.abs(add).max()), same])

    est = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.5, random_state=3).fit(X, y)
    T = TS.from_sklearn(est.tree_, leaf_float32=True)
    run(T, "sklearn tree, float32 leaves, merged duplicate", lambda Z: est.predict(Z).astype(np.float32).astype(np.float64))
    from sklearnex.ensemble import RandomForestRegressor
    rf = RandomForestRegressor(n_estimators=1, bootstrap=False, max_features=0.5, min_samples_leaf=20,
                               random_state=9, n_jobs=1).fit(X, y)
    T = TS.from_sklearn(rf.estimators_[0].tree_, leaf_float32=True)
    run(T, "oneDAL forest member", lambda Z: np.asarray(rf.predict(Z), np.float64))
    import lightgbm as lgb
    bst = lgb.train({"objective": "regression", "num_leaves": 15, "verbose": -1, "seed": 0, "num_threads": 1,
                     "deterministic": True}, lgb.Dataset(X, y), num_boost_round=3)
    trees = [TS.from_lgbm(t) for t in bst.dump_model()["tree_info"]]
    phi = np.zeros((4, npl))
    for T in trees:
        TS.itreeshap(T, Xe64, BG64, px, pb, pw, poc, npl, phi)
    raw = lambda Z: sum(TS.predict(T, Z) for T in trees)  # noqa: E731
    worst = max(float(np.abs(TS.brute_force(raw, Xe64[i], BG64, np.full(9, 1 / 9.), poc, npl) - phi[i]).max())
                for i in range(4))
    same = float(np.abs(raw(Xe64) - bst.predict(Xe64, raw_score=True)).max())
    check("S2 LightGBM booster (3 trees): brute force, evaluator vs booster", worst < 1e-12 and same < 1e-12,
          [worst, same])
    # a LightGBM model trained WITH a duplicated column (feature_fraction < 1, an interaction): the merged map equals
    # the brute-force merged player; the sum of two separate players does not
    Xd = rng.normal(size=(4000, 5)).astype(np.float32)
    Xd[:, 4] = Xd[:, 1]
    yd = Xd[:, 0] * Xd[:, 1] + Xd[:, 2] + 0.3 * Xd[:, 3] * Xd[:, 1] + rng.normal(scale=0.05, size=4000)
    bd = lgb.train({"objective": "regression", "num_leaves": 31, "verbose": -1, "seed": 0, "num_threads": 1,
                    "deterministic": True, "feature_fraction": 0.6, "min_data_in_leaf": 20}, lgb.Dataset(Xd, yd),
                   num_boost_round=20)
    td = [TS.from_lgbm(t) for t in bd.dump_model()["tree_info"]]
    used = sorted(set(int(f) for T in td for f, l in zip(T["feat"], T["left"]) if l >= 0))
    Xe5 = rng.normal(size=(5, 5)).astype(np.float32)
    Xe5[:, 4] = Xe5[:, 1]
    BG5 = rng.normal(size=(7, 5)).astype(np.float32)
    BG5[:, 4] = BG5[:, 1]
    e5, b5 = Xe5.astype(np.float64), BG5.astype(np.float64)
    px5, pb5, pw5 = TS.pairs_for([np.arange(7)] * 5)
    pm = np.array([0, 1, 2, 3, 1])
    phim, phis = np.zeros((5, 4)), np.zeros((5, 5))
    for T in td:
        TS.itreeshap(T, e5, b5, px5, pb5, pw5, pm, 4, phim)
        TS.itreeshap(T, e5, b5, px5, pb5, pw5, np.arange(5), 5, phis)
    rawd = lambda Z: sum(TS.predict(T, Z) for T in td)  # noqa: E731
    worst = max(float(np.abs(TS.brute_force(rawd, e5[i], b5, np.full(7, 1 / 7.), pm, 4) - phim[i]).max())
                for i in range(5))
    check("S2 LightGBM trained on a duplicated column: merged map == brute force", worst < 1e-12 and
          1 in used and 4 in used, [worst, "columns split on: %s" % used])
    # a per-NODE feature draw (scikit-learn / oneDAL max_features, as the RF) puts both copies in one tree: there the
    # sum of two separate players is not the merged player's value (LightGBM's per-tree draw never mixes them)
    ts = DecisionTreeRegressor(max_depth=8, min_samples_leaf=5, max_features=0.5, random_state=11).fit(Xd, yd)
    Ts = TS.from_sklearn(ts.tree_, leaf_float32=True)
    phim2 = TS.itreeshap(Ts, e5, b5, px5, pb5, pw5, pm, 4)
    phis2 = TS.itreeshap(Ts, e5, b5, px5, pb5, pw5, np.arange(5), 5)
    worst2 = max(float(np.abs(TS.brute_force(lambda Z: TS.predict(Ts, Z), e5[i], b5, np.full(7, 1 / 7.), pm, 4)
                              - phim2[i]).max()) for i in range(5))
    gap = float(np.abs(phis2[:, 1] + phis2[:, 4] - phim2[:, 1]).max())
    check("S2 per-node draw on a duplicated column: merged == brute force; separate sum differs",
          worst2 < 1e-12 and gap > 1e-6, [worst2, gap, "LightGBM separate-sum gap %.1e" %
                                          float(np.abs(phis[:, 1] + phis[:, 4] - phim[:, 1]).max())])
    # grouped (variable-level) game: several distinct columns per player, against brute force
    pg = np.array([0, 0, 1, 2, 2, 3, 3])
    est3 = DecisionTreeRegressor(max_depth=7, min_samples_leaf=5, random_state=4).fit(X, y)
    T3 = TS.from_sklearn(est3.tree_, leaf_float32=True)
    phig = TS.itreeshap(T3, Xe64, BG64, px, pb, pw, pg, 4)
    worst = max(float(np.abs(TS.brute_force(lambda Z: TS.predict(T3, Z), Xe64[i], BG64, np.full(9, 1 / 9.), pg, 4)
                             - phig[i]).max()) for i in range(4))
    check("S2 grouped game (variable level, 7 columns in 4 groups) == brute force", worst < 1e-12, worst)
    from sklearn.ensemble import HistGradientBoostingRegressor
    h = HistGradientBoostingRegressor(max_iter=3, max_leaf_nodes=15, random_state=0).fit(X, y)
    trees = [TS.from_hgb(pr[0].nodes) for pr in h._predictors]
    base = float(np.ravel(h._baseline_prediction)[0])
    hraw = lambda Z: base + sum(TS.predict(T, Z) for T in trees)  # noqa: E731
    phi = np.zeros((4, npl))
    for T in trees:
        TS.itreeshap(T, Xe64, BG64, px, pb, pw, poc, npl, phi)
    worst = max(float(np.abs(TS.brute_force(hraw, Xe64[i], BG64, np.full(9, 1 / 9.), poc, npl) - phi[i]).max())
                for i in range(4))
    same = float(np.abs(hraw(Xe64) - h.predict(Xe64)).max())
    check("S2 HistGradientBoosting (3 trees): brute force, evaluator vs model", worst < 1e-12 and same < 1e-12,
          [worst, same])
    # S-ZERO: a column equal on every background row of an explained row gets exactly 0, in the walk ...
    BGz = BG64.copy()
    BGz[:, 2] = Xe64[0, 2]                       # player 2 constant for row 0 only
    phz = TS.itreeshap(TS.from_sklearn(est.tree_, leaf_float32=True), Xe64, BGz, px, pb, pw, poc, npl)
    cm = RW.constant_mask(Xe64, BGz, px, pb, poc, npl)
    check("S2 S-ZERO walk: a player equal on every background row has phi exactly 0", phz[0, 2] == 0.0 and cm[0, 2]
          and not cm[1, 2], [float(phz[0, 2]), bool(cm[0, 2]), bool(cm[1, 2])])
    # ... and in the per-pair linear form, where the old mean-then-subtract form leaves 1-ulp noise
    noisy = exact0 = 0
    for _ in range(2000):
        v = rng.normal() * 10.0 ** int(rng.integers(-3, 4))
        k = int(rng.integers(5, 60))
        lin_b = np.full(k, v)
        old_form = 0.7 * (v - np.bincount(np.zeros(k, np.int64), weights=lin_b * (1.0 / k), minlength=1)[0])
        new_form = 0.7 * np.bincount(np.zeros(k, np.int64), weights=(v - lin_b) * (1.0 / k), minlength=1)[0]
        noisy += old_form != 0
        exact0 += new_form == 0
    check("S2 S-ZERO linear: per-pair differences give exactly 0 (old form noisy)", exact0 == 2000 and noisy > 100,
          {"new_form_exact_zero": exact0, "old_form_nonzero": noisy})
    # adaptive split: force tiny chunk limits and compare with the unsplit result
    est2 = DecisionTreeRegressor(max_depth=14, min_samples_leaf=2, random_state=1).fit(X, y)
    T2 = TS.from_sklearn(est2.tree_)
    Xe2 = rng.normal(size=(50, Cn))
    BG2 = rng.normal(size=(30, Cn))
    px2, pb2, pw2 = TS.pairs_for([np.arange(30)] * 50)
    ref = TS.itreeshap(T2, Xe2, BG2, px2, pb2, pw2, np.arange(Cn), Cn)
    keep = (TS.MAX_PAIRS, TS.MAX_STATE_ELEMS)
    TS.MAX_PAIRS, TS.MAX_STATE_ELEMS = 97, 500.0
    t0 = time.time()
    got = TS.itreeshap(T2, Xe2, BG2, px2, pb2, pw2, np.arange(Cn), Cn)
    TS.MAX_PAIRS, TS.MAX_STATE_ELEMS = keep
    add = got.sum(1) - (TS.predict(T2, Xe2) - TS.predict(T2, BG2).mean())
    check("S2 adaptive chunk split equals the unsplit walk (depth-14 tree)", float(np.abs(got - ref).max()) < 1e-12
          and float(np.abs(add).max()) < 1e-11, [float(np.abs(got - ref).max()), float(np.abs(add).max()),
                                                 round(time.time() - t0, 2)])


def s3_resume():
    d = os.path.join(C.ROOT, "smoke", "unit_resume")
    C.makedirs(d)
    p = os.path.join(d, "piece.json")
    inputs = {"a": 1}
    C.write_json(p, {"x": 1})
    C.mark_done(p, inputs)
    ok1 = C.piece_done(p, inputs)
    ok2 = not C.piece_done(p, {"a": 2})
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(" ")
    ok3 = not C.piece_done(p, inputs)
    check("S3 resume: finished piece skipped; changed inputs / edited file redone", ok1 and ok2 and ok3,
          [ok1, ok2, ok3])
    refused = []
    for bad in ("D:/treeroute/runs/x.json", "D:/treeroute/rivals/x.json", "C:/Windows/x.json",
                os.path.join(C.ROOT, "..", "ablation_perlocation", "x.json")):
        try:
            C.assert_writable(bad)
            refused.append(False)
        except SystemExit:
            refused.append(True)
    check("S3 write guard refuses outside/protected targets", all(refused), refused)
    red = C.redact(r"C:\Users\someone else\Downloads\x and C:/Users/abc/y")
    check("S3 redaction removes account names", "someone" not in red and "abc" not in red, red)
    # the register: identity, background hash, refusal of an unregistered or altered file
    reg = os.path.join(d, "REG.txt")
    sf = os.path.join(d, "sample.parquet")
    bf = os.path.join(d, "background_lead_0.parquet")
    for f, txt in ((sf, "sample-bytes"), (bf, "bg-bytes")):
        with open(C.assert_writable(f), "w", encoding="utf-8") as fh:
            fh.write(txt)
    with open(C.assert_writable(reg), "w", encoding="utf-8") as fh:
        fh.write("2026-11-12T00:00:00 problem=coral tag=v1 leads=0 n=2 defo_regions=0 sample=%s "
                 "background_lead_0.parquet=%s\n" % (C.sha256_file(sf), C.sha256_file(bf)))
    idn = C.sample_identity("coral", d, reg, lead=0)
    with open(bf, "a", encoding="utf-8") as fh:
        fh.write("x")
    try:
        C.sample_identity("coral", d, reg, lead=0)
        altered = False
    except SystemExit:
        altered = True
    check("S3 register: identity read; an altered background file is refused", idn["sample_sha256"] ==
          C.sha256_file(sf) and altered, [idn["sample_sha256"][:12], altered])
    # D8: a TRUE relative tolerance (|d| <= tol |saved|), exact where saved is 0
    s = np.array([1e-3, 2.0, 0.0, 5e-7])
    ok_a = C.relative_check(s, s * (1 + 5e-13), 1e-12)[0]
    ok_b = not C.relative_check(s, s + 1e-13, 1e-12)[0]          # absolute 1e-13 on 5e-7 is 2e-7 relative
    ok_c = not C.relative_check(s, np.array([1e-3, 2.0, 1e-300, 5e-7]), 1e-12)[0]
    check("S3 D8 tolerance is relative below |y|=1 and exact at 0", ok_a and ok_b and ok_c, [ok_a, ok_b, ok_c])
    # the variable rule on real column names (PROTOCOL.md 8)
    cases = {"x__dhw_84": "dhw", "x__dhw_90": "dhw", "x__n_above_mmm1_30": "n_above_mmm1",
             "x__cyc_maxw_200_30": "cyc_maxw", "x__frost_days_mean": "frost_days", "x__frost_days_max": "frost_days",
             "x__V06_spei_12m_lag12": "spei", "x__spei_01m_lag12": "spei", "x__V06_spei_12m_mean_lag1": "spei",
             "x__V01_mean_temp_C_lag3": "mean_temp_C", "x__V01_mean_temp_C_mean": "mean_temp_C",
             "x__wbal_roll12": "wbal", "x__hist_mean_all": "hist_mean", "x__hist_mean_12": "hist_mean",
             "x__hist_last_2": "hist_last", "x__n_burns_12mo": "n_burns", "x__nbr25km_12mo_lag3": "nbr25km",
             "x__nino34": "nino34", "x__era5l_stl1": "era5l_stl1", "c__ctx:month": "calendar",
             "c__ctx_doy_sin": "calendar", "c__ctx:sin2": "calendar", "c__ctx:lat": "ctx:lat",
             "c__ctx:top5:sph_kgkg_lag6": "sph_kgkg", "normal": "normal", "x__aglw_cattle_hold2021":
             "aglw_cattle_hold2021", "x__vpd_warm_season_mean_max": "vpd_warm_season"}
    bad = {k: C.variable_of(k) for k, v in cases.items() if C.variable_of(k) != v}
    check("S3 variable rule on %d real column names" % len(cases), not bad, bad or "all as expected")
    # the privacy scan finds an account path outside the engine-written folders and counts the ones inside them
    pdir = os.path.join(d, "privacy")
    C.makedirs(os.path.join(pdir, "engine_runs"))
    acct = "C:/Users/" + "zz" + "unit/Desktop/x"          # a made-up account name
    for f in (os.path.join(pdir, "a.txt"), os.path.join(pdir, "engine_runs", "key.json")):
        with open(C.assert_writable(f), "w", encoding="utf-8") as fh:
            fh.write(acct)
    badf, inside = C.privacy_scan(pdir, names=["zz" + "unit"])
    for f in (os.path.join(pdir, "a.txt"), os.path.join(pdir, "engine_runs", "key.json")):
        os.remove(f)
    check("S3 privacy scan: 1 file outside, 1 inside the engine-written folders", badf == ["a.txt"] and inside == 1,
          [badf, inside])


if __name__ == "__main__":
    t0 = time.time()
    s1_stats()
    s2_treeshap()
    s3_resume()
    REPORT["_seconds"] = round(time.time() - t0, 1)
    REPORT["_failed"] = FAIL
    C.write_json(os.path.join(C.ROOT, "smoke", "unit_report.json"), REPORT)
    print("unit smoke: %d checks, %d failed, %.1f s" % (len(REPORT) - 2, len(FAIL), time.time() - t0))
    sys.exit(1 if FAIL else 0)
