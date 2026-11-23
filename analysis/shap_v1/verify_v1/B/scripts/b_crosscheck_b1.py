# Implementer B, round 14: loop-based re-computation of a sample of my B1 numbers (full sample and single draws).
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from scipy import stats

SHAP = Path(r"D:\treeroute\analysis\shap_v1")
VB = Path(r"D:\treeroute\analysis\shap_v1\verify_v1\B")
res = json.loads((VB / "results.json").read_text(encoding="utf-8"))
bad = []


def close(name, a, b, tol=1e-12):
    ok = (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b)))
    print("%-70s %s  mine=%r  check=%r" % (name, "ok" if ok else "DIFF", a, b))
    if not ok:
        bad.append(name)


def load(p, folder, level):
    pref = "phi__" if level == "feature" else "phiv__"
    t = pq.read_table(SHAP / "out" / p / "lead_0" / folder / "rows.parquet").to_pandas().sort_values("row")
    return t, {c[len(pref):]: c for c in t.columns if c.startswith(pref)}


def imp(t, cols, names, reg_list):
    out = {}
    for j in names:
        vals = [np.mean(np.abs(t.loc[t["group"] == r, cols[j]].to_numpy())) if j in cols else 0.0 for r in reg_list]
        out[j] = float(np.mean(vals))
    return out


for p, level, draw_ids in [("fire", "variable", [11]), ("ndvi", "feature", [1500]), ("pm25", "feature", [3])]:
    regions = res["problems"][p]["draws"]["regions_in_draw_order"]
    draws = np.load(SHAP / "out" / p / "lead_0" / "compare" / "bootstrap_draws.npy")
    z = np.load(VB / "draws" / ("b1_%s.npz" % p), allow_pickle=False)
    tm, cm = load(p, "treeroute", level)
    tb, cb = load(p, "treeroute_B1", level)
    e = res["b1"][p][level]
    pb = e["pair_main_b1"]
    allp = sorted(set(cm) | set(cb))
    Im0 = imp(tm, cm, allp, regions)
    Ib0 = imp(tb, cb, allp, regions)
    Jchk = sorted(j for j in allp if Im0[j] > 1e-12 * sum(Im0.values()) or Ib0[j] > 1e-12 * sum(Ib0.values()))
    print("%s %s pair J equal: %s (%d)" % (p, level, Jchk == pb["J"], len(Jchk)))
    if Jchk != pb["J"]:
        bad.append(p + " pair J")
    J = pb["J"]
    for d in [None] + draw_ids:
        reg_list = regions if d is None else [regions[k] for k in draws[d]]
        Im = imp(tm, cm, J, reg_list)
        Ib = imp(tb, cb, J, reg_list)
        sm = {j: Im[j] / sum(Im.values()) for j in J}
        sb = {j: Ib[j] / sum(Ib.values()) for j in J}
        sp = stats.spearmanr([Im[j] for j in J], [Ib[j] for j in J]).correlation
        tau = stats.kendalltau([Im[j] for j in J], [Ib[j] for j in J], variant="b").correlation
        tv = 0.5 * sum(abs(sm[j] - sb[j]) for j in J)
        ob = sorted(J, key=lambda j: (-Ib[j], j))
        tag = "%s %s draw %s" % (p, level, "full" if d is None else d)
        if d is None:
            get = lambda k: pb[k]["value"]
            close(tag + " B1 share of its top player " + ob[0], e["importance"]["players"][ob[0]]["share"]["value"], sb[ob[0]])
            print("   B1 ranking equal:", e["importance"]["ranking"] == ob)
        else:
            get = lambda k: float(z["%s/pair_main_b1/%s" % (level, k)][d])
        close(tag + " spearman_J", get("spearman_J"), sp)
        close(tag + " kendall_tau_b", get("kendall_tau_b"), tau)
        close(tag + " tv_shares", get("tv_shares"), tv)
print("CROSSCHECK B1", "PASSED" if not bad else "FAILED: %s" % bad)
sys.exit(1 if bad else 0)
