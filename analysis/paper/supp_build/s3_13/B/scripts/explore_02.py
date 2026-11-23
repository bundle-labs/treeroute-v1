# Exploration only (builder B): concise view of models, guards and exactness records. Writes nothing.
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]


def jl(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


for p in PROBS:
    C = os.path.join(SHAP, "out", p, "lead_0", "compare")
    pl = jl(os.path.join(C, "per_lead.json"))
    print("=" * 20, p, "models", pl["models"], "main", pl["main_set"], "declined", pl["declined_by_guard"])
    print("  links", pl["links"])
    print("  nzf keys", list(pl.get("nonzero_forecast_rows", {}).keys()), "regions", pl["regions"])
    for L in ["variable", "feature"]:
        d = pl[L]
        print("  %s players %d active %d nsz %d nonzero %s" % (L, d["players"], d["active"], len(d["structural_zero"]), d["nonzero_players"]))
    pr = pd.read_parquet(os.path.join(C, "pairs.parquet"))
    labs = pr.groupby(["level", "model_a", "model_b"])["pair_label"].unique()
    for k, v in labs.items():
        print("   label", k, list(v))
    for m in pl["models"]:
        P = os.path.join(SHAP, "out", p, "lead_0", m)
        meta = jl(os.path.join(P, "meta.json"))
        g = meta.get("guard", {})
        print("  --", m, "rows", meta["rows"], "pass", meta["pass"], "checks", meta["checks_passed"], "link", meta["link"],
              "add", meta["max_abs_additivity_error"], meta["max_abs_additivity_error_variable"], "szv", meta["structural_zero_violations"],
              "guard.passed", g.get("passed"), "pairs", meta.get("pairs"), "arm", meta.get("arm"))
        if os.path.exists(os.path.join(P, "exactness.json")):
            ex = jl(os.path.join(P, "exactness.json"))
            raw = ex.get("raw")
            print("     exactness: pass", ex.get("pass"), "rows", ex.get("rows"), "bit", ex.get("bit_equal_rows"), "max", ex.get("max_abs_diff"),
                  "has raw", "raw" in ex, (raw.get("bit_equal_rows") if isinstance(raw, dict) else None), "keys", list(ex.keys()))
        if os.path.exists(os.path.join(P, "ridge_shap_exactness.json")):
            ex = jl(os.path.join(P, "ridge_shap_exactness.json"))
            print("     ridge_shap: pass", ex.get("pass"), "stage", ex.get("stage"), "rows", ex.get("rows"), "bit", ex.get("bit_equal_rows"),
                  "max", ex.get("max_abs_diff"), "raw.bit", ex.get("raw", {}).get("bit_equal_rows"))
