# Exploration only (builder B): prints the structure of the section-1 source files. Writes nothing.
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]


def jl(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def short(o, depth=0, maxd=3):
    if isinstance(o, dict):
        if depth >= maxd:
            return "{...%d keys}" % len(o)
        return "{" + ", ".join("%s: %s" % (k, short(v, depth + 1, maxd)) for k, v in o.items()) + "}"
    if isinstance(o, list):
        if len(o) > 6:
            return "[%d items: %s ...]" % (len(o), ", ".join(short(x, depth + 1, maxd) for x in o[:3]))
        return "[" + ", ".join(short(x, depth + 1, maxd) for x in o) + "]"
    return repr(o)


for p in PROBS:
    C = os.path.join(SHAP, "out", p, "lead_0", "compare")
    pl = jl(os.path.join(C, "per_lead.json"))
    print("=" * 30, p)
    print("PL keys:", list(pl.keys()))
    for k in ["models", "main_set", "declined_by_guard", "links", "rows", "regions", "draws", "reference_link"]:
        print(" ", k, "=", pl.get(k))
    for L in ["variable", "feature"]:
        d = pl[L]
        print(" ", L, "keys:", list(d.keys()))
        print("   players", d["players"], "active", d["active"], "n_sz", len(d["structural_zero"]))
        print("   W", d["kendall_w_main_set"], "MPS", d["mean_pairwise_spearman_main_set"])
        print("   nonzero", d["nonzero_players"])
    print("  nonzero_forecast_rows keys:", list(pl.get("nonzero_forecast_rows", {}).keys()))
    fams = pl["families"]
    from collections import Counter
    print("  family counts:", Counter(fams.values()))
    pr = pd.read_parquet(os.path.join(C, "pairs.parquet"))
    print("  pairs columns:", list(pr.columns), pr.dtypes.to_dict())
    print("  pairs shape", pr.shape, "statistics:", sorted(pr["statistic"].unique()))
    print("  pair_label values:")
    for lab in sorted(pr["pair_label"].unique()):
        print("     ", repr(lab))
    im = pd.read_parquet(os.path.join(C, "importance.parquet"))
    print("  importance columns:", list(im.columns), im.dtypes.to_dict(), im.shape)
    fa = pd.read_parquet(os.path.join(C, "families.parquet"))
    print("  families columns:", list(fa.columns), fa.dtypes.to_dict(), fa.shape)
    print("  families families:", sorted(fa["family"].unique()))
    for m in pl["models"]:
        P = os.path.join(SHAP, "out", p, "lead_0", m)
        meta = jl(os.path.join(P, "meta.json"))
        print("  --", m, "meta keys:", list(meta.keys()))
        print("     ", {k: meta.get(k) for k in ["rows", "pass", "checks_passed", "link", "max_abs_additivity_error", "max_abs_additivity_error_variable", "structural_zero_violations", "pairs", "arm"]})
        print("      guard:", short(meta.get("guard"), maxd=2))
        if os.path.exists(os.path.join(P, "exactness.json")):
            ex = jl(os.path.join(P, "exactness.json"))
            print("      exactness:", short(ex, maxd=2))
        if os.path.exists(os.path.join(P, "ridge_shap_exactness.json")):
            ex = jl(os.path.join(P, "ridge_shap_exactness.json"))
            print("      ridge_shap_exactness:", short(ex, maxd=2))
