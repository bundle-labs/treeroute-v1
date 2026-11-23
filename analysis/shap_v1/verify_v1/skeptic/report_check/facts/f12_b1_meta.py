import json, os
SHAP = r"D:\treeroute\analysis\shap_v1"
reg = open(os.path.join(SHAP, "SAMPLE_REGISTER.txt"), encoding="utf-8").read()
print("SAMPLE_REGISTER lines:", len(reg.splitlines()))
for line in reg.splitlines():
    print("   ", line[:260])
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    d = os.path.join(SHAP, "out", p, "lead_0", "treeroute_B1")
    print("=" * 10, p, "exists", os.path.isdir(d))
    if not os.path.isdir(d):
        continue
    print("   files:", sorted(os.listdir(d)))
    meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    keys = ["pass", "checks_passed", "rows", "background", "pairs", "trees_used", "sample_sha256", "duplicates_merged",
            "players_nonzero", "variables_nonzero", "tree_shap_seconds"]
    for k in keys:
        v = meta.get(k)
        if isinstance(v, dict) and k == "checks_passed":
            v = {kk: (vv if not isinstance(vv, dict) else vv.get("passed", vv)) for kk, vv in v.items()}
        print("   meta", k, json.dumps(v)[:300])
    done = json.load(open(os.path.join(d, "rows.parquet.done.json"), encoding="utf-8"))
    print("   done keys", list(done.keys()))
    print("   done seconds", done.get("seconds"), "finished", done.get("finished"), "sample", str(done.get("sample_sha256"))[:8])
    mm = json.load(open(os.path.join(SHAP, "out", p, "lead_0", "treeroute", "meta.json"), encoding="utf-8"))
    print("   MAIN meta players_nonzero", mm.get("players_nonzero"), "variables_nonzero", mm.get("variables_nonzero"),
          "dups", json.dumps(mm.get("duplicates_merged"))[:300], "trees", mm.get("trees_used"), "pairs", mm.get("pairs"))
# also the per_lead nonzero_forecast_rows and structural zero counts
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    per = json.load(open(os.path.join(SHAP, "out", p, "lead_0", "compare", "per_lead.json"), encoding="utf-8"))
    nz = per.get("nonzero_forecast_rows", {})
    print(p, "nonzero_forecast_rows:", {m: v.get("rows") for m, v in nz.items()})
    for lev in ["feature", "variable"]:
        print("   ", lev, "players", per[lev]["players"], "active", per[lev]["active"], "structural_zero n", len(per[lev]["structural_zero"]))
    print("    models", per["models"], "main_set", per["main_set"], "regions", per["regions"], "draws", per["draws"])
    # item 8 shares distinct?
    for m, v in nz.items():
        sh = [x[1] for x in v["top10"]]
        print("    item8", m, "top10 distinct", len(set(sh)) == len(sh), "min gap", min(abs(a - b) for a, b in zip(sh, sh[1:])) if len(sh) > 1 else None)
