"""Skeptic (numbers lens): my own global-index classification from the lead-0 test set (rival export, lead_0\\test).

Rule (section 8): a variable all of whose columns take one value per time step across every unit of the lead's test set.
Reading: exact equality of the stored values; a step where every unit is missing counts as one value; a mix fails.
Also reported: the variant that ignores missing values, and the columns that fail only by a small spread.
"""
import os, sys, json, glob
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
EXPORT = {
    "coral": r"D:\treeroute\rival_export\coral\20261020_f3b8e3da\lead_0\test",
    "defo": r"D:\treeroute\rival_export\defo\20261017_d71c61f4\lead_0\test",
    "fire": r"D:\treeroute\rival_export\fire\20261017_869d1f38\lead_0\test",
    "pm25": r"D:\treeroute\rival_export\pm25\20261007_74e67609\lead_0\test",
    "ndvi": r"D:\treeroute\rival_export\ndvi\20261016_d1de3158\lead_0\test",
}
probs = sys.argv[1:] or ["coral", "fire", "pm25", "ndvi", "defo"]
res = {}
for p in probs:
    pl = L.per_lead(p)
    vmap = {}
    for m in pl["models"]:
        vm = L.meta(p, m)["variable_map"]
        for k, v in vm.items():
            if k in vmap and vmap[k] != v:
                print("MAP CONFLICT", p, k, vmap[k], v)
            vmap[k] = v
    xcols = sorted(k for k in vmap if k.startswith("x__"))
    files = sorted(glob.glob(os.path.join(EXPORT[p], "*.parquet")))
    have = set(pq.ParquetFile(files[0]).schema_arrow.names)
    cols = [c for c in xcols if c in have]
    missing = [c for c in xcols if c not in have]
    parts = [pq.read_table(f, columns=["unit", "time"] + cols).to_pandas() for f in files]
    df = pd.concat(parts, ignore_index=True)
    g = df.groupby("time")
    mn = g[cols].min()
    mx = g[cols].max()
    nn = g[cols].count()
    sz = g.size()
    allnan = nn.eq(0)
    full = nn.eq(sz, axis=0)
    same = mn.eq(mx)
    ok = (allnan | (full & same)).all(axis=0)
    ok_ignore_nan = (allnan | same).all(axis=0)
    spread = ((mx - mn).abs() / (mx.abs().clip(lower=1e-30))).max(axis=0)
    passing = set(ok[ok].index)
    passing_nn = set(ok_ignore_nan[ok_ignore_nan].index)
    var_cols = {}
    for k, v in vmap.items():
        if k.startswith("x__"):
            var_cols.setdefault(v, []).append(k)
    gvars = sorted(v for v, cs in var_cols.items() if all(c in passing for c in cs))
    gvars_nn = sorted(v for v, cs in var_cols.items() if all(c in passing_nn for c in cs))
    near = sorted([c for c in cols if c not in passing and np.isfinite(spread[c]) and spread[c] < 1e-4])
    partial = sorted(v for v, cs in var_cols.items() if any(c in passing for c in cs) and not all(c in passing for c in cs))
    res[p] = dict(rows=len(df), units=int(df["unit"].nunique()), times=int(df["time"].nunique()),
                  n_xcols=len(xcols), missing_in_test=missing, global_vars=gvars, global_vars_ignore_nan=gvars_nn,
                  near_global_columns=near, partially_global_vars=partial,
                  global_columns=sorted(passing))
    print(p, "rows", len(df), "units", res[p]["units"], "times", res[p]["times"], "xcols", len(xcols),
          "missing", len(missing), "global vars", len(gvars), gvars, "ignore-nan differs:", gvars != gvars_nn,
          "near", near, "partial", partial)
    del df, parts
with open(os.path.join(OUT, "s01_global_%s.json" % "_".join(probs)), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
