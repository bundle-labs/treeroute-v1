# Threshold-free robustness for trend_strata.py: Spearman between each unit's pre-test slope / drift and the unit's
# MAE gap (Ridge - ours; >0 = ours better), and tercile splits instead of hand-picked cut points. POST-HOC.
import sys, os, numpy as np, pandas as pd
sys.argv = [sys.argv[0]]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_strata.py"), encoding="utf-8").read()
src = src.split("rows = []")[0]                                   # reuse loaders + unit features only
exec(compile(src, "trend_strata_head", "exec"))
from scipy.stats import spearmanr
for L in (0, 6, 12):
    d = preds(L).join(feat, on="unit")
    for who, col in (("answer", "answer"), ("model", "ours")):
        if L != 12 and who == "model": continue
        u = d.assign(g=(d.ridge - d.y).abs() - (d[col] - d.y).abs()).groupby("unit").agg(gap=("g", "mean"), slope=("slope_pct", "first"), drift=("drift_pct", "first")).dropna()
        rs = spearmanr(u.slope, u.gap).correlation; rd = spearmanr(u.drift, u.gap).correlation
        u["t"] = pd.qcut(u.slope, 3, labels=["falling third", "middle third", "rising third"])
        tt = u.groupby("t", observed=True).agg(units=("gap", "size"), mean_gap=("gap", "mean"), ours_better=("gap", lambda s: int((s > 0).sum())),
                                              slope_lo=("slope", "min"), slope_hi=("slope", "max"))
        print("lead %d [%s]: Spearman(slope, gap) %+.3f; Spearman(drift, gap) %+.3f" % (L, who, rs, rd))
        print(tt.round(3).to_string()); print()
