# POST-HOC, OUTCOME-CONDITIONAL (owner request 2026-10-22): ours vs the rivals on "spike months", i.e. test cell-months
# whose observed PM2.5 is above the unit's own 2003-2019 percentile q (q = 75, 90, 95; from training labels only).
# d = rival MAE - ours (>0 = ours better), averaged over regions, LOGO jackknife 95% CI (board method).
# The normal is printed too: if the plain normal also beats a rival on spikes, the win is about that rival's level, not skill.
import os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_strata.py"), encoding="utf-8").read().split("rows = []")[0]
exec(compile(src, "trend_strata_head", "exec"))
def jk2(x, a, b):
    m = x.assign(ea=(x[a] - x.y).abs(), eb=(x[b] - x.y).abs()).groupby("group")[["ea", "eb"]].mean()
    dg = (m.ea - m.eb).values; G = len(dg); th = dg.mean(); loo = (dg.sum() - dg) / (G - 1)
    se = np.sqrt((G - 1) / G * ((loo - loo.mean()) ** 2).sum()); return th, th - 1.96 * se, th + 1.96 * se, G
out = []
for L in (0, 6, 12):
    d = preds(L)
    for q in (75, 90, 95):
        thr = h.groupby("unit").y.quantile(q / 100).rename("thr")
        x0 = d.join(thr, on="unit")
        for lab, sel in (("spike", x0.y > x0.thr), ("ordinary", x0.y <= x0.thr)):
            x = x0[sel]
            for who in (["answer"] if L != 12 else ["answer", "ours"]):
                r = dict(lead=L, q=q, months=lab, ours_is=("headline answer" if who == "answer" else "rejected model (secondary)"),
                         rows=len(x), units=x.unit.nunique(), regions=x.group.nunique(), mean_y=x.y.mean())
                for c in (who, "ridge", "rf", "lgbm", "normal"):
                    r["mae_" + ("ours" if c == who else c)] = (x[c] - x.y).abs().mean()
                    r["bias_" + ("ours" if c == who else c)] = (x[c] - x.y).mean()
                for c in ("ridge", "rf", "lgbm", "normal"):
                    th, lo, hi, G = jk2(x, c, who); r["d_" + c] = th; r["lo_" + c] = lo; r["hi_" + c] = hi
                out.append(r)
res = pd.DataFrame(out); res.to_csv(os.path.join(HERE, "spike_months.csv"), index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 50)
cols = ["lead", "q", "months", "ours_is", "rows", "regions", "mean_y", "mae_ours", "mae_ridge", "mae_rf", "mae_lgbm", "mae_normal",
        "d_ridge", "lo_ridge", "hi_ridge", "d_rf", "lo_rf", "hi_rf", "d_lgbm", "lo_lgbm", "hi_lgbm", "bias_ours", "bias_ridge", "bias_normal"]
print(res[cols].round(3).to_string(index=False))
