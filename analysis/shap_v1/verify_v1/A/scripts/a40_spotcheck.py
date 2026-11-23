# Round 14, implementer A: spot checks of a10/a20 outputs by a second code path (pandas groupby, scipy, loops).
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
import a_lib as L

fails = []


def check(label, ok, detail=""):
    print("%-78s %s %s" % (label, "PASS" if ok else "FAIL", detail))
    if not ok:
        fails.append(label)


def region_weighted(df, col, regs_draw=None):
    g = df.groupby("group")[col].mean()
    if regs_draw is None:
        return g.mean()
    return np.mean([g[r] for r in regs_draw])


def main():
    for p, m, lev, j in (("fire", "treeroute", "variable", "hist_mean"), ("ndvi", "rival_rf", "feature", "x__spi_03m"),
                         ("coral", "rival_lgbm", "feature", "c__ctx_doy_sin"), ("defo", "treeroute", "variable", "hist_last")):
        with open(os.path.join(L.V_A, "work", "items_%s.json" % p), "r", encoding="utf-8") as fh:
            r = json.load(fh)
        z = np.load(os.path.join(L.V_A, "draws", "%s.npz" % p), allow_pickle=False)
        rows = L.read_rows(p, m)
        key = "players" if lev == "feature" else "variables"
        mat = "phi" if lev == "feature" else "phiv"
        col = rows[mat][:, rows[key].index(j)]
        df = pd.DataFrame({"group": rows["keys"]["group"], "a": np.abs(col), "s": col})
        I_ref = region_weighted(df, "a")
        S_ref = region_weighted(df, "s")
        e = r["levels"][lev]["models"][m]["players"][j]
        check("%s %s %s %s: I by pandas groupby" % (p, m, lev, j), abs(e["I"]["value"] - I_ref) <= 1e-15 * max(1, abs(I_ref)) + 1e-18,
              "%r vs %r" % (e["I"]["value"], I_ref))
        check("%s %s %s %s: signed mean by pandas groupby" % (p, m, lev, j), abs(e["signed_mean"]["value"] - S_ref) <= 1e-15 * max(1, abs(S_ref)) + 1e-18)
        # draw 0 and draw 1999 by explicit loop over the drawn regions
        draws, sha, _ = L.load_draws(p)
        regions = r["draws"]["regions_in_draw_order"]
        names = list(z["levels/%s/models/%s/players/names" % (lev, m)])
        ci = names.index(j)
        for b in (0, 1999):
            regs = [regions[k] for k in draws[b]]
            I_b = region_weighted(df, "a", regs)
            got = z["levels/%s/models/%s/players/I" % (lev, m)][b, ci]
            check("%s %s %s: draw %d I by explicit region loop" % (p, m, j, b), abs(got - I_b) <= 1e-14 * max(1, abs(I_b)), "%r vs %r" % (got, I_b))
        # share sums to 1 over J on the full sample and on draws
        sh = np.array([v["share"]["value"] for k, v in r["levels"][lev]["models"][m]["players"].items()])
        shd = z["levels/%s/models/%s/players/share" % (lev, m)]
        check("%s %s %s: shares sum to 1 over J (full; every draw)" % (p, m, lev),
              abs(sh.sum() - 1) < 1e-12 and np.allclose(shd.sum(axis=1), 1, atol=1e-12))
    # scipy cross-check of one pair on the full sample
    for p, lev, a, b in (("pm25", "variable", "rival_lgbm", "treeroute"), ("ndvi", "feature", "rival_bardl_h1", "treeroute"),
                         ("coral", "feature", "rival_hgb_l1", "rival_lgbm")):
        with open(os.path.join(L.V_A, "work", "items_%s.json" % p), "r", encoding="utf-8") as fh:
            r = json.load(fh)
        J = r["levels"][lev]["active_set"]["J"]
        Ia = np.array([r["levels"][lev]["models"][a]["players"][j]["I"]["value"] for j in J])
        Ib = np.array([r["levels"][lev]["models"][b]["players"][j]["I"]["value"] for j in J])
        pr = r["levels"][lev]["pairs"]["%s|%s" % (a, b)]
        check("%s %s %s|%s: Spearman over J equals scipy" % (p, lev, a, b), abs(pr["spearman_J"]["value"] - stats.spearmanr(Ia, Ib).correlation) < 1e-13)
        check("%s %s %s|%s: tau-b equals scipy" % (p, lev, a, b), abs(pr["kendall_tau_b"]["value"] - stats.kendalltau(Ia, Ib, variant="b").correlation) < 1e-13)
        # top-20 union by sorting with Python keys
        ka = sorted(range(len(J)), key=lambda i: (-Ia[i], J[i]))[:20]
        kb = sorted(range(len(J)), key=lambda i: (-Ib[i], J[i]))[:20]
        U = sorted(set(ka) | set(kb))
        check("%s %s %s|%s: top-20 union names" % (p, lev, a, b), sorted(J[i] for i in U) == pr["top20_union"])
        check("%s %s %s|%s: Spearman over the top-20 union equals scipy" % (p, lev, a, b),
              abs(pr["spearman_top20_union"]["value"] - stats.spearmanr(Ia[U], Ib[U]).correlation) < 1e-13)
        j5 = len(set(ka[:5]) & set(kb[:5])) / len(set(ka[:5]) | set(kb[:5]))
        check("%s %s %s|%s: Jaccard top-5 by Python sets" % (p, lev, a, b), abs(pr["jaccard_top5"]["value"] - j5) < 1e-15)
        # RBO by Python sets on full rankings
        oa = sorted(range(len(J)), key=lambda i: (-Ia[i], J[i]))
        ob = sorted(range(len(J)), key=lambda i: (-Ib[i], J[i]))
        pp = 0.9
        tot, sa, sb = 0.0, set(), set()
        for d in range(1, len(J) + 1):
            sa.add(oa[d - 1]); sb.add(ob[d - 1])
            tot += (1 - pp) * pp ** (d - 1) * len(sa & sb) / d
        tot += pp ** len(J) * len(sa & sb) / len(J)
        check("%s %s %s|%s: RBO p=0.9 by Python sets" % (p, lev, a, b), abs(pr["rbo_p090"]["value"] - tot) < 1e-12, "%r vs %r" % (pr["rbo_p090"]["value"], tot))
        sha = np.array([r["levels"][lev]["models"][a]["players"][j]["share"]["value"] for j in J])
        shb = np.array([r["levels"][lev]["models"][b]["players"][j]["share"]["value"] for j in J])
        check("%s %s %s|%s: TV of shares" % (p, lev, a, b), abs(pr["tv_shares"]["value"] - 0.5 * np.abs(sha - shb).sum()) < 1e-14)
    # Kendall's W by a direct loop (ndvi variable level)
    with open(os.path.join(L.V_A, "work", "items_ndvi.json"), "r", encoding="utf-8") as fh:
        r = json.load(fh)
    lv = r["levels"]["variable"]
    J = lv["active_set"]["J"]
    mains = r["main_set"]
    ranks = [stats.rankdata([lv["models"][m]["players"][j]["I"]["value"] for j in J]) for m in mains]
    mm, n = len(mains), len(J)
    Rj = np.sum(ranks, axis=0)
    S = ((Rj - mm * (n + 1) / 2) ** 2).sum()
    T = 0.0
    for rk in ranks:
        _, c = np.unique(rk, return_counts=True)
        T += ((c ** 3) - c).sum()
    Wref = 12 * S / (mm ** 2 * (n ** 3 - n) - mm * T)
    check("ndvi variable: Kendall's W by a direct loop", abs(lv["per_problem"]["kendall_w"]["value"] - Wref) < 1e-13, "%r vs %r" % (lv["per_problem"]["kendall_w"]["value"], Wref))
    # family share by pandas (fire treeroute own history)
    with open(os.path.join(L.V_A, "work", "items_fire.json"), "r", encoding="utf-8") as fh:
        r = json.load(fh)
    rows = L.read_rows("fire", "treeroute")
    fam = r["levels"]["variable"]["families"]["variable_family"]
    F = {f: np.zeros(1000) for f in L.FAMILIES}
    for c, v in enumerate(rows["variables"]):
        F[fam[v]] += rows["phiv"][:, c]
    df = pd.DataFrame({"group": rows["keys"]["group"], **{f: np.abs(F[f]) for f in L.FAMILIES}})
    Ifam = {f: df.groupby("group")[f].mean().mean() for f in L.FAMILIES}
    tot = sum(Ifam.values())
    got = r["levels"]["variable"]["models"]["treeroute"]["family_shares"]["own_history"]["value"]
    check("fire treeroute own-history family share by pandas", abs(got - Ifam["own_history"] / tot) < 1e-14, "%r vs %r" % (got, Ifam["own_history"] / tot))
    check("fire main row own-history share of treeroute equals the family share",
          r["main_row"]["own_history_share_treeroute"]["value"] == got)
    print("SPOTCHECK", "PASSED" if not fails else "FAILED: %s" % fails)


if __name__ == "__main__":
    main()
