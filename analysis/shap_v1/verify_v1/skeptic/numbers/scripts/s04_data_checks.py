"""Skeptic (numbers lens): data-level checks that all three sources share.

1. every piece's (row, unit, group, time, year) equals the registered sample's;
2. each sampled (unit, time) is in the lead-0 test export file named after its group (group = the export's region);
3. per row: sum of phi__ vs sum of phiv__ (both should equal eta - base - resid); base + sum phi + resid - eta;
4. for the linear models (ridge, BARDL): phiv of a variable == sum of its players' phi (map applied consistently);
   for every model: the largest |phiv_v - sum_{j in v} phi_j| (non-additive models differ legitimately).
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
res = {}
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    r = {}
    smp = pq.read_table(os.path.join(L.SHAP, "sample", p, "sample.parquet")).to_pandas().sort_values("row").reset_index(drop=True)
    mods = list(L.per_lead(p)["models"])
    if os.path.exists(os.path.join(L.piece(p, "treeroute_B1"), "rows.parquet")):
        mods.append("treeroute_B1")
    keys_ok = {}
    add = {}
    for m in mods:
        path = os.path.join(L.piece(p, m), "rows.parquet")
        t = pq.read_table(path).to_pandas().sort_values("row").reset_index(drop=True)
        ok = all((t[c].astype(str).to_numpy() == smp[c].astype(str).to_numpy()).all() for c in ["row", "unit", "group", "time", "year"])
        keys_ok[m] = bool(ok)
        phic = [c for c in t.columns if c.startswith("phi__")]
        phivc = [c for c in t.columns if c.startswith("phiv__")]
        sphi = t[phic].to_numpy().sum(axis=1)
        sphiv = t[phivc].to_numpy().sum(axis=1)
        e = t["eta"].to_numpy() - t["base"].to_numpy()
        res_ = t["resid"].to_numpy()
        vm = L.meta(p, m)["variable_map"]
        worst = 0.0
        worst_v = None
        for v in phivc:
            vv = v[len("phiv__"):]
            members = ["phi__" + k for k, x in vm.items() if x == vv and ("phi__" + k) in t.columns]
            if not members:
                continue
            dlt = np.abs(t[v].to_numpy() - t[members].to_numpy().sum(axis=1)).max()
            if dlt > worst:
                worst, worst_v = float(dlt), vv
        add[m] = dict(max_abs_sum_phi_minus_sum_phiv=float(np.abs(sphi - sphiv).max()),
                      max_abs_base_plus_phi_plus_resid_minus_eta=float(np.abs(sphi + res_ - e).max()),
                      max_abs_base_plus_phiv_plus_resid_minus_eta=float(np.abs(sphiv + res_ - e).max()),
                      max_abs_eta_minus_base=float(np.abs(e).max()),
                      max_abs_phiv_minus_member_sum=worst, at_variable=worst_v,
                      columns_without_map=[c[5:] for c in phic if c[5:] not in vm])
    r["keys_equal_sample"] = keys_ok
    r["additivity"] = add
    # group vs export file
    files = {os.path.splitext(os.path.basename(f))[0]: f for f in glob.glob(os.path.join(EXPORT[p], "*.parquet"))}
    miss_file = sorted(set(smp["group"]) - set(files))
    found = 0
    notfound = 0
    for g, sub in smp.groupby("group"):
        if g not in files:
            notfound += len(sub)
            continue
        tt = pq.read_table(files[g], columns=["unit", "time"]).to_pandas()
        kk = set(zip(tt["unit"].astype(str), tt["time"].astype(np.int64)))
        hit = sum((u, int(ti)) in kk for u, ti in zip(sub["unit"].astype(str), sub["time"]))
        found += hit
        notfound += len(sub) - hit
    r["groups_without_export_file"] = miss_file
    r["sample_rows_found_in_own_group_file"] = found
    r["sample_rows_not_found"] = notfound
    g = smp.groupby("group")
    r["rows_per_region_min_max"] = [int(g.size().min()), int(g.size().max())]
    r["units_per_region_min_max"] = [int(g["unit"].nunique().min()), int(g["unit"].nunique().max())]
    res[p] = r
    print(p, json.dumps({k: v for k, v in r.items() if k != "additivity"}))
    for m, a in add.items():
        print("   ", m, json.dumps(a))
with open(os.path.join(OUT, "s04_data_checks.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
