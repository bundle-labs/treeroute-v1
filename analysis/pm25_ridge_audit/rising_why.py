# POST-HOC (owner question): why does our nowcast beat Ridge on units that were RISING before 2020?
# Looks at the rising >3%/yr units (pre-test slope 2013-19) at lead 0: which regions, bias, spike vs ordinary months.
import sys, os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend_strata.py"), encoding="utf-8").read().split("rows = []")[0]
exec(compile(src, "trend_strata_head", "exec"))
d = preds(0).join(feat, on="unit")
d["year"] = (d.time - 1) // 12
# spike month = the unit's test value above its own 2003-2019 90th percentile (from training labels, any month)
p90 = h.groupby("unit").y.quantile(0.9).rename("p90")
d = d.join(p90, on="unit"); d["spike"] = d.y > d.p90
def show(x, name):
    eo, er = (x.ours - x.y).abs(), (x.ridge - x.y).abs()
    print("%-28s rows %6d  MAE ours %.3f ridge %.3f  gap %+.3f | bias ours %+.3f ridge %+.3f | mean y %.2f normal %.2f ours %.2f ridge %.2f"
          % (name, len(x), eo.mean(), er.mean(), er.mean() - eo.mean(), (x.ours - x.y).mean(), (x.ridge - x.y).mean(), x.y.mean(), x.normal.mean(), x.ours.mean(), x.ridge.mean()))
for lab, sel in (("rising >3%/yr", d.slope_pct > 3), ("rising 1-3%/yr", (d.slope_pct > 1) & (d.slope_pct <= 3)), ("flat", d.slope_pct.abs() <= 1), ("falling >3%/yr", d.slope_pct < -3)):
    x = d[sel]; print("\n=== %s: %d units in %d regions" % (lab, x.unit.nunique(), x.group.nunique()))
    show(x, "all months")
    show(x[x.spike], "spike months (y > own p90)"); show(x[~x.spike], "ordinary months")
    for yv in range(2020, 2024): show(x[x.year == yv], "year %d" % yv)
x = d[d.slope_pct > 3]
g = x.assign(eo=(x.ours - x.y).abs(), er=(x.ridge - x.y).abs()).groupby("group").agg(units=("unit", "nunique"), slope=("slope_pct", "mean"),
      mae_ours=("eo", "mean"), mae_ridge=("er", "mean"), y=("y", "mean"), normal=("normal", "mean"), spike_share=("spike", "mean"))
g["gap"] = g.mae_ridge - g.mae_ours
print("\nrising >3%/yr units by region (gap > 0 = ours better):")
print(g.sort_values("gap", ascending=False).round(3).to_string())
