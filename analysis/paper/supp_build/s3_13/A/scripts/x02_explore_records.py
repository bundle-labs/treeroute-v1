# Exploration only (prints to console): run records, samples, results.json tree, maxima, logs.
import sys, json, os, re

sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
V = SHAP + r"\verify_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def jl(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get(d, dotted):
    cur = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return "<missing>"
        cur = cur[k]
    return cur


for p in PROBLEMS:
    print("=" * 20, p)
    pl = jl(SHAP + "\\out\\" + p + "\\lead_0\\compare\\per_lead.json")
    for m in pl["models"]:
        P = SHAP + "\\out\\" + p + "\\lead_0\\" + m + "\\"
        meta = jl(P + "meta.json")
        keys = ["rows", "pass", "checks_passed", "link", "guard.passed", "max_abs_additivity_error",
                "max_abs_additivity_error_variable", "structural_zero_violations", "sample_sha256", "pairs", "arm"]
        print(" ", m, {k: get(meta, k) for k in keys})
        if os.path.exists(P + "exactness.json"):
            ex = jl(P + "exactness.json")
            print("    exactness:", {k: get(ex, k) for k in ["pass", "rows", "bit_equal_rows", "max_abs_diff", "raw.bit_equal_rows", "stage"]}, "has raw:", "raw" in ex)
        if os.path.exists(P + "ridge_shap_exactness.json"):
            ex = jl(P + "ridge_shap_exactness.json")
            print("    ridge_shap:", {k: get(ex, k) for k in ["pass", "stage", "rows", "bit_equal_rows", "max_abs_diff", "raw.bit_equal_rows"]})
    B1 = SHAP + "\\out\\" + p + "\\lead_0\\treeroute_B1\\"
    if os.path.exists(B1 + "meta.json"):
        mb = jl(B1 + "meta.json")
        db = jl(B1 + "rows.parquet.done.json")
        print("  B1 meta pairs:", mb.get("pairs"), "tree_shap_seconds:", mb.get("tree_shap_seconds"), "done:", db)
    man = jl(SHAP + "\\sample\\" + p + "\\sample_manifest.json")
    print("  manifest:", {k: man.get(k) for k in ["n", "frame_rows", "regions_in_sample", "units_in_sample"]},
          "bg0:", man.get("background_rows", {}).get("0"), "sha:", man.get("sha256", {}).get("sample.parquet"))
    print("  manifest keys:", list(man.keys()))

print("=" * 20, "register")
with open(SHAP + "\\SAMPLE_REGISTER.txt", "r", encoding="utf-8") as f:
    for i, line in enumerate(f.read().split("\n"), 1):
        print(i, repr(line))

print("=" * 20, "maxima")
with open(V + "\\_lead\\outputs\\bardl_maxima.txt", "r", encoding="utf-8") as f:
    for i, line in enumerate(f.read().split("\n"), 1):
        if i <= 12:
            print(i, repr(line))

print("=" * 20, "logs")
for p in PROBLEMS:
    path = SHAP + "\\logs\\tr_shap_" + p + "_lead0.log"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    print("--", p, len(lines))
    for i, line in enumerate(lines, 1):
        if " background pairs," in line or "done in" in line:
            print(i, repr(line))
