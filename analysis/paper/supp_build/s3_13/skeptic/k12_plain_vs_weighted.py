# Skeptic (version 2 check, item 4): the captions call the importances "mean absolute SHAP value(s)"; PROTOCOL 8 defines
# I_m(j) as the REGION-WEIGHTED mean |phi| (each region weighs 1), and k08 shows that the stored values are that.
# How far would a plain mean over the 1,000 rows move the printed shares? Read-only; prints only.
import json, sys
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
FAMS = ["own history", "global indices", "local drivers", "context and calendar", "seasonal normal"]


def pct1(x):
    return "0.0%" if x == 0.0 else ("<0.1%" if 100 * x < 0.05 else format(100 * x, ".1f") + "%")


def num2(x):
    return "0.00" if x == 0.0 else format(x, ".2f")


tot_top = tot_top_diff = tot_fam = tot_fam_diff = 0
worst = (0.0, "")
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    C = SHAP + r"\out\%s\lead_0\compare" % p
    PL = json.load(open(C + r"\per_lead.json", encoding="utf-8"))
    IM = pd.read_parquet(C + r"\importance.parquet")
    FA = pd.read_parquet(C + r"\families.parquet")
    fam = PL["families"]
    n_regions = None
    for m in PL["models"]:
        R = pd.read_parquet(SHAP + r"\out\%s\lead_0\%s\rows.parquet" % (p, m))
        n_regions = R["group"].nunique()
        q = IM[(IM.level == "variable") & (IM.model == m) & (IM.active)].copy()
        cols = ["phiv__" + v for v in q.player]
        Ip = R.reindex(columns=cols, fill_value=0.0).abs().mean()
        q["plain"] = (Ip / Ip.sum()).values
        top = q.sort_values(["share", "player"], ascending=[False, True]).head(10)
        dif = sum(pct1(a) != pct1(b) for a, b in zip(top.share, top.plain))
        mx = float((q.plain - q.share).abs().max())
        tot_top += 10
        tot_top_diff += dif
        F = {}
        for f in FAMS:
            vs = ["phiv__" + v for v in q.player if fam.get(v) == f]
            F[f] = float(R.reindex(columns=vs, fill_value=0.0).sum(axis=1).abs().mean()) if vs else 0.0
        S = sum(F.values())
        fa = FA[FA.model == m].set_index("family").share
        fd = [(f, float(fa[f]), F[f] / S) for f in FAMS]
        fdif = sum(pct1(a) != pct1(b) for _, a, b in fd)
        tot_fam += 5
        tot_fam_diff += fdif
        oh = [x for x in fd if x[0] == "own history"][0]
        big = max(abs(a - b) for _, a, b in fd)
        if big > worst[0]:
            worst = (big, "%s %s" % (p, m))
        print("%-5s %-19s regions %3d | top-10 shares: %d of 10 print differently (largest share move %.4f) | family shares: %d of 5 print differently (largest move %.4f) | own history %s (stored) vs %s (plain mean)"
              % (p, m, n_regions, dif, mx, fdif, big, num2(oh[1]), num2(oh[2])))
print("printed top-10 shares that a plain mean would change: %d of %d; printed family shares: %d of %d; largest family-share move %.4f (%s)"
      % (tot_top_diff, tot_top, tot_fam_diff, tot_fam, worst[0], worst[1]))
