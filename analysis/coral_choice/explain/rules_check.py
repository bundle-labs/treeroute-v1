"""POST-HOC: would candidate engine-rule changes have fired / changed the pick on the 5 headline runs?
Read-only on runs and engine. Writes only next to this script."""
import sys, json, os
import numpy as np, pandas as pd, pyarrow.parquet as pq
ENG = r"C:\Users\<user>\Desktop\data set for reserch paper\engine"
sys.path.insert(0, ENG)
from treeroute.report.metrics import contrast_tag, group_jackknife
OUT = os.path.dirname(os.path.abspath(__file__))
RUNS = {"coral": "D:/treeroute/runs/coral/headline/20261020_f3b8e3da",
        "pm25": "D:/treeroute/runs/pm25/headline/20261007_74e67609",
        "ndvi": "D:/treeroute/runs/ndvi/headline/20261016_d1de3158",
        "fire": "D:/treeroute/runs/fire/headline/20261017_869d1f38",
        "defo": "D:/treeroute/runs/defo/headline/20261017_d71c61f4"}
ONLY = sys.argv[1:] or list(RUNS)
NDRAW = 2000
rng = np.random.default_rng(0)  # resampling draws only; no model is refit


def parse(c):
    arm, _, pt = c.partition("@")
    if not pt:
        return arm, None
    d = dict(kv.split("=") for kv in pt.split(","))
    r = d.get("ratio")
    return arm, (float(d["level"]), None if r in (None, "None") else float(r))


def linkof(arm):
    return arm.split("_plain")[0].split("_corrector")[0].split("_trees_off")[0]


def pg_mae(err, g):
    return pd.Series(np.asarray(err, dtype=np.float64)).groupby(g).mean()


res = {}
for pkg in ONLY:
    run = RUNS[pkg]
    adopt = json.load(open(run + "/adoption.json"))
    verdict = json.load(open(run + "/verdict.json"))
    a = adopt["adopted"]
    A = "%s_%s_%s" % (a["link"], a["tool"], a["weighting"])
    bp = adopt["best_tree_penalty"]
    band_test = verdict["band"]
    cols = pq.read_schema(run + "/inner_preds.parquet").names
    pcols = [c for c in cols[4:] if not c.startswith("pre__")]
    S = pq.read_table(run + "/inner_preds.parquet", columns=["group", "y"] + pcols).to_pandas()
    y = S["y"].to_numpy(np.float64)
    g = S["group"].astype(str).to_numpy()
    arms = {}
    for c in pcols:
        arm, pt = parse(c)
        arms.setdefault(arm, []).append((pt, c))
    picks = {}
    for arm, lst in arms.items():
        if arm.startswith("base__"):
            continue
        maes = [float(np.mean(np.abs(y - S[c].to_numpy(np.float64)))) for _, c in lst]
        k = int(np.argmin(maes))
        pt = lst[k][0]
        edge = None
        if pt is not None:
            lv = sorted({p[0] for p, _ in lst})
            rt = sorted({p[1] for p, _ in lst if p[1] is not None})
            e = []
            if len(lv) > 1 and pt[0] in (lv[0], lv[-1]):
                e.append("level-" + ("top" if pt[0] == lv[-1] else "bottom"))
            if len(rt) > 1 and pt[1] is not None and pt[1] in (rt[0], rt[-1]):
                e.append("ratio-" + ("top" if pt[1] == rt[-1] else "bottom"))
            edge = e
        picks[arm] = dict(col=lst[k][1], mae=maes[k], point=pt, edge=edge)
    # decision-time analogue of the R35 band: median jackknife SE of arm-vs-own-trees-off on the SURFACE
    ses = []
    for arm, p in picks.items():
        if "trees_off" in arm:
            continue
        off = picks[linkof(arm) + "_trees_off_unweighted"]["col"]
        dv = (pg_mae(np.abs(y - S[off]), g) - pg_mae(np.abs(y - S[p["col"]]), g)).to_numpy()
        ses.append(group_jackknife(dv).se)
    band_surf = float(np.median(ses))
    link, tool, wt = a["link"], a["tool"], a["weighting"]
    variants = []
    for t2 in [tool] + (["plain"] if tool == "corrector" else []):
        for w2 in [wt] + (["unweighted"] if wt == "gls" else []):
            v = "%s_%s_%s" % (link, t2, w2)
            if v != A and v in picks:
                variants.append(v)
    # the weighting twin (for the label-free drift check), even if it is not simpler
    twin = "%s_%s_%s" % (link, tool, "unweighted" if wt == "gls" else "gls")
    T = pd.read_parquet(run + "/test_preds.parquet")
    T = T[np.isfinite(T["y"].to_numpy(np.float64))].reset_index(drop=True)  # unlabelled rows are not scored
    yt = T["y"].to_numpy(np.float64)

    def tmae(arm):
        c = "arm__" + arm
        return float(np.mean(np.abs(yt - T[c].to_numpy(np.float64)))) if c in T else None

    hi = np.zeros(y.size, bool); hi[np.argsort(-y, kind="stable")[: max(1, y.size // 10)]] = True  # top 10% rows by y
    yt_hi = np.zeros(yt.size, bool); yt_hi[np.argsort(-yt, kind="stable")[: max(1, yt.size // 10)]] = True
    vrec = {}
    for v in sorted(set(variants + ([twin] if twin in picks else []))):
        dv = (pg_mae(np.abs(y - S[picks[v]["col"]]), g) - pg_mae(np.abs(y - S[picks[A]["col"]]), g))
        rec = {"own_point": picks[v]["point"], "surface_mae": picks[v]["mae"],
               "pooled_gap_adopted_better": picks[v]["mae"] - picks[A]["mae"], "pg_mean": float(dv.mean())}
        for nm, b in (("test_band", band_test), ("surface_band", band_surf)):
            tag, jk = contrast_tag(dv.to_numpy(), b)
            rec["tag_" + nm] = tag.name
            rec["jk_low"], rec["jk_high"], rec["jk_se"] = jk.low, jk.high, jk.se
        rec["top10_mae_adopted"] = float(np.mean(np.abs(y - S[picks[A]["col"]])[hi]))
        rec["top10_mae_variant"] = float(np.mean(np.abs(y - S[picks[v]["col"]])[hi]))
        same = [c for pt, c in arms[v] if pt == picks[A]["point"]]
        if same:
            rec["disagree_surface"] = float(np.mean(np.abs(S[picks[A]["col"]] - S[same[0]])))
        if "arm__" + v in T:
            rec["disagree_test"] = float(np.mean(np.abs(T["arm__" + A] - T["arm__" + v])))
        rec["test_mae_at_adopted_point"] = tmae(v)
        if "arm__" + v in T:
            rec["test_top10_mae_adopted"] = float(np.mean(np.abs(yt - T["arm__" + A])[yt_hi]))
            rec["test_top10_mae_variant"] = float(np.mean(np.abs(yt - T["arm__" + v])[yt_hi]))
        vrec[v] = rec

    def rank(v):
        return int(v.endswith("_gls")) + int("_corrector_" in v)

    ruleA = {}
    for nm in ("test_band", "surface_band"):
        ok = [v for v in variants if vrec[v]["tag_" + nm] != "HELPS"]
        ruleA[nm] = sorted(ok, key=lambda v: (rank(v), vrec[v]["surface_mae"]))[0] if ok else A
    # whole-rule group bootstrap from group sums
    G, gi = np.unique(g, return_inverse=True)
    N = np.bincount(gi, minlength=len(G)).astype(float)
    cand = [(arm, c) for arm, lst in arms.items() for _, c in lst]
    Ssum = np.stack([np.bincount(gi, weights=np.abs(y - S[c].to_numpy(np.float64)), minlength=len(G))
                     for _, c in cand], 1)
    armnames = sorted({arm for arm, _ in cand if not arm.startswith("base__")})
    idx = {arm: [i for i, (a2, _) in enumerate(cand) if a2 == arm] for arm in armnames}
    use_donor = "decline_baseline" in adopt["decision"]
    base_i = [i for i, (a2, _) in enumerate(cand) if a2 == "base__donor_median"]
    wins = {}
    for _ in range(NDRAW):
        cnt = np.bincount(rng.integers(0, len(G), len(G)), minlength=len(G)).astype(float)
        m = (cnt @ Ssum) / (cnt @ N)
        best = {arm: m[idx[arm]].min() for arm in armnames}
        if use_donor:
            el = [k for k in armnames if "trees_off" not in k and best[k] < m[base_i[0]]]
        else:
            el = [k for k in armnames if "trees_off" not in k and best[k] < best[linkof(k) + "_trees_off_unweighted"]]
        w = min(el, key=lambda k: best[k]) if el else "decline"
        wins[w] = wins.get(w, 0) + 1
    wins = {k: v / NDRAW for k, v in sorted(wins.items(), key=lambda kv: -kv[1])}
    res[pkg] = dict(adopted=A, adopted_point=bp, adopted_surface_mae=picks[A]["mae"],
                    adopted_edge=picks[A]["edge"],
                    arms_on_edge=sum(1 for p in picks.values() if p["edge"]),
                    arms_with_grid=sum(1 for p in picks.values() if p["edge"] is not None),
                    band_test=band_test, band_surface=band_surf, n_groups=len(G), n_surface=len(y),
                    test_mae_adopted=tmae(A), variants=vrec, ruleA=ruleA,
                    ruleA_test_mae={k: tmae(v) for k, v in ruleA.items()},
                    bootstrap_adopt_share=wins, bootstrap_share_of_actual=wins.get(A, 0.0),
                    eligibility="donor_median (V1)" if use_donor else "own trees-off (N2)")
    print(pkg, json.dumps(res[pkg], indent=1, default=str), flush=True)
    json.dump(res[pkg], open(os.path.join(OUT, "rules_check_%s.json" % pkg), "w"), indent=1, default=str)
    del S, T
