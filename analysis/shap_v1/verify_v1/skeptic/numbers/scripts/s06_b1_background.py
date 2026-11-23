"""Skeptic (numbers lens): is each B1 run's background what section 5 says, relative to its main (B2) run?
B1: all of the unit's router fit rows at or before the cut -> one key set per unit, a superset of every B2 set of that
unit; B2: the same calendar month as the explained row's target step (monthly problems)."""
import os, sys, json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s_lib as L

OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\numbers\work"
res = {}
for p in ["fire", "pm25", "ndvi", "defo"]:
    b2 = pq.read_table(os.path.join(L.piece(p, "treeroute"), "background_keys.parquet")).to_pandas()
    b1 = pq.read_table(os.path.join(L.piece(p, "treeroute_B1"), "background_keys.parquet")).to_pandas()
    smp = pq.read_table(os.path.join(L.SHAP, "sample", p, "sample.parquet")).to_pandas().set_index("row")
    r = {"n_b2": len(b2), "n_b1": len(b1)}
    g1 = b1.groupby("row")
    g2 = b2.groupby("row")
    sets1 = {k: set(zip(v["unit"], v["time"])) for k, v in g1}
    sets2 = {k: set(zip(v["unit"], v["time"])) for k, v in g2}
    r["rows_b1"] = len(sets1)
    r["rows_b2"] = len(sets2)
    r["b2_subset_of_b1_all_rows"] = all(sets2[k] <= sets1.get(k, set()) for k in sets2)
    # same unit for every background key
    r["b1_keys_same_unit"] = bool((b1["unit"].to_numpy() == smp.loc[b1["row"], "unit"].to_numpy()).all())
    r["b2_keys_same_unit"] = bool((b2["unit"].to_numpy() == smp.loc[b2["row"], "unit"].to_numpy()).all())
    # one B1 set per unit
    per_unit = {}
    ok = True
    for k, s in sets1.items():
        u = smp.loc[k, "unit"]
        if u in per_unit and per_unit[u] != s:
            ok = False
        per_unit.setdefault(u, s)
    r["b1_one_set_per_unit"] = ok
    # background times before the explained rows' times
    r["b1_all_before_explained"] = bool((b1["time"].to_numpy() < smp.loc[b1["row"], "time"].to_numpy()).all())
    if p != "defo":
        # monthly time index: same month of year <=> time difference multiple of 12
        dt2 = smp.loc[b2["row"], "time"].to_numpy() - b2["time"].to_numpy()
        dt1 = smp.loc[b1["row"], "time"].to_numpy() - b1["time"].to_numpy()
        r["b2_same_month_all"] = bool((dt2 % 12 == 0).all())
        r["b1_share_same_month"] = float((dt1 % 12 == 0).mean())
        r["b1_rows_per_unit_min_max"] = [int(min(len(s) for s in sets1.values())), int(max(len(s) for s in sets1.values()))]
        r["b2_rows_per_row_min_max"] = [int(min(len(s) for s in sets2.values())), int(max(len(s) for s in sets2.values()))]
    res[p] = r
    print(p, json.dumps(r))
with open(os.path.join(OUT, "s06_b1_background.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
