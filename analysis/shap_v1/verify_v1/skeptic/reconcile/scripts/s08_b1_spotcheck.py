"""Skeptic: a small independent recomputation of B1 full-sample numbers (no official output exists for B1, so A = B
could hide a shared misreading). For fire, pm25 and ndvi at both levels: I(j) of both runs (region-weighted mean
|phi|, each region weighs 1), the pair J (either run gives more than 1e-12 of its total), B1 shares over that J,
Spearman over the pair J, n_nonzero of B1, the top-10; compared with A's and B's results. Also prints the B1 run
facts that the reconciler only lists side by side (duplicates_merged_*, context_columns_summed), and whether A's and
B's B1 counts carry intervals (C08). Read-only; stdout only."""
import json
import os

import numpy as np
import pyarrow.parquet as pq

SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
RES = {X: json.load(open(os.path.join(V, X, "results.json"), encoding="utf-8")) for X in ("A", "B")}


def avg_ranks(x):
    x = np.asarray(x, float)
    o = np.argsort(x, kind="mergesort")
    s = x[o]
    r = np.empty(len(x))
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and s[j + 1] == s[i]:
            j += 1
        r[o[i:j + 1]] = 0.5 * (i + j) + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = avg_ranks(a), avg_ranks(b)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


def imp(path, pref):
    t = pq.read_table(path).to_pandas().sort_values("row")
    cols = [c for c in t.columns if c.startswith(pref)]
    g = t["group"].astype(str).to_numpy()
    regs = sorted(set(g))
    P = np.abs(t[cols].to_numpy(float))
    S = t[cols].to_numpy(float)
    Ir = np.vstack([P[g == r].mean(0) for r in regs])
    Sr = np.vstack([S[g == r].mean(0) for r in regs])
    return {c[len(pref):]: (Ir[:, k].mean(), Sr[:, k].mean()) for k, c in enumerate(cols)}


for p in ("fire", "pm25", "ndvi"):
    for L, pref in (("feature", "phi__"), ("variable", "phiv__")):
        M = imp(os.path.join(SHAP, "out", p, "lead_0", "treeroute", "rows.parquet"), pref)
        B = imp(os.path.join(SHAP, "out", p, "lead_0", "treeroute_B1", "rows.parquet"), pref)
        names = sorted(set(M) | set(B))
        im = np.array([M.get(n, (0.0, 0.0))[0] for n in names])
        ib = np.array([B.get(n, (0.0, 0.0))[0] for n in names])
        act = (im > 1e-12 * im.sum()) | (ib > 1e-12 * ib.sum())
        J = [n for n, a in zip(names, act) if a]
        imJ, ibJ = im[act], ib[act]
        shB = ibJ / ibJ.sum()
        rho = spearman(imJ, ibJ)
        order = sorted(range(len(J)), key=lambda k: (-ibJ[k], J[k]))
        top10 = [J[k] for k in order[:10]]
        nnz = int((ib > 0).sum())
        for X, R in RES.items():
            b = R["b1"][p][L]
            Jx = b["pair_main_b1"]["J"]
            pl = b["importance"]["players"]
            dI = max(abs(pl[j]["I"]["value"] - B.get(j, (0.0, 0.0))[0]) for j in J)
            dS = max(abs(pl[j]["share"]["value"] - s) for j, s in zip(J, shB))
            dSg = max(abs(pl[j]["signed_mean"]["value"] - B.get(j, (0.0, 0.0))[1]) for j in J)
            rx = b["pair_main_b1"]["spearman_J"]["value"]
            t10 = [x[0] for x in b["top10"]]
            print("%-5s %-8s %s  J equal %s (%d vs %d)  max|dI| %.2e  max|dshare| %.2e  max|dS| %.2e  rho %.15f vs %.15f "
                  "(d %.1e)  top10 equal %s  n_nonzero %d vs %s  n_J ci %s" % (
                      p, L, X, Jx == J, len(J), len(Jx), dI, dS, dSg, rho, rx, abs(rho - rx), t10 == top10, nnz,
                      b["importance"]["n_nonzero"]["value"],
                      (b["pair_main_b1"]["n_J"]["ci_low"], b["pair_main_b1"]["n_J"]["n_finite"])))
    for X, R in RES.items():
        run = R["b1"][p]["run"]
        print("   %s run: dup_main %s dup_b1 %s summed %s draws_sha_match %s; n_nonzero ci (%s, %s, %s)" % (
            X, run.get("duplicates_merged_main"), run.get("duplicates_merged_b1"), run.get("context_columns_summed"),
            run.get("draws_sha256_match"), R["b1"][p]["feature"]["importance"]["n_nonzero"]["ci_low"],
            R["b1"][p]["feature"]["importance"]["n_nonzero"]["ci_high"],
            R["b1"][p]["feature"]["importance"]["n_nonzero"]["n_finite"]))
    for X, R in RES.items():
        fams = R["b1"][p]["variable"]["families"]
        print("   %s B1 families:" % X, {f: (None if v is None else v.get("value")) for f, v in fams.items()})
