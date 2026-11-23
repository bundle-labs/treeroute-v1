# Exploration only (builder B): edge cases in pairs.parquet, A's sign agreement, importance ties, B1 records. Writes nothing.
import sys, json, os, math
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np
import pandas as pd

SHAP = r"D:\treeroute\analysis\shap_v1"
V = os.path.join(SHAP, "verify_v1")
PROBS = ["pm25", "ndvi", "fire", "defo", "coral"]


def jl(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


A = jl(os.path.join(V, "A", "results.json"))
for p in PROBS:
    C = os.path.join(SHAP, "out", p, "lead_0", "compare")
    pr = pd.read_parquet(os.path.join(C, "pairs.parquet"))
    print("=" * 10, p, "pairs rows", len(pr))
    nonsign = pr[pr["statistic"] != "sign_agreement_top10"]
    print("  non-sign: NaN value", int(nonsign["value"].isna().sum()), "NaN ci_low", int(nonsign["ci_low"].isna().sum()),
          "NaN ci_high", int(nonsign["ci_high"].isna().sum()), "finite<2000", int((nonsign["finite_replicates"] < 2000).sum()),
          "signs_compared notna", int(nonsign["signs_compared"].notna().sum()))
    sub = nonsign[(nonsign["finite_replicates"] < 2000) | nonsign["value"].isna()]
    if len(sub):
        print(sub.to_string())
    sg = pr[pr["statistic"] == "sign_agreement_top10"]
    for _, r in sg.iterrows():
        key = r["model_a"] + "|" + r["model_b"]
        a = A["problems"][p]["levels"][r["level"]]["pairs"][key]
        sa = a["sign_agreement"]
        sn = a["sign_n_determined"]
        print("  sign %-8s %-40s value %-20r ci %r %r nf %r signs %r | A %r [%r, %r] nf %r nd %r" % (
            r["level"], key, r["value"], r["ci_low"], r["ci_high"], r["finite_replicates"], r["signs_compared"],
            sa["value"], sa["ci_low"], sa["ci_high"], sa["n_finite"], sn["value"]))
    im = pd.read_parquet(os.path.join(C, "importance.parquet"))
    for (L, m), g in im.groupby(["level", "model"]):
        ga = g[g["active"]]
        ga = ga.sort_values(["mean_abs", "player"], ascending=[False, True], kind="mergesort")
        top = list(zip(ga["player"].tolist()[:11], ga["mean_abs"].tolist()[:11], ga["share"].tolist()[:11]))
        # ties among the first 11 mean_abs values
        vals = [t[1] for t in top]
        ties = len(vals) - len(set(vals))
        print("  imp %-8s %-20s active %d nonzero %d ties_in_top11 %d share_sum %.15f" % (L, m, len(ga), int((ga["mean_abs"] > 0).sum()), ties, ga["share"].sum()))
        if ties:
            print("     top11", top)
    fa = pd.read_parquet(os.path.join(C, "families.parquet"))
    print("  families rows", len(fa), "models", sorted(fa["model"].unique()))
    # B1 records
    B1 = os.path.join(SHAP, "out", p, "lead_0", "treeroute_B1")
    if os.path.isdir(B1):
        mb = jl(os.path.join(B1, "meta.json"))
        dn = jl(os.path.join(B1, "rows.parquet.done.json"))
        print("  B1 meta pairs", mb.get("pairs"), "tree_shap_seconds", mb.get("tree_shap_seconds"), "sample_sha256", mb.get("sample_sha256"), "done keys", list(dn.keys()), "seconds", dn.get("seconds"))
    g = jl(os.path.join(SHAP, "rebuild", p, "lead_0", "gates.json"))
    e3m = g["gates"].get("E3m_recorded_path_map")
    if e3m:
        for fobj in e3m["values"]["files"]:
            print("  E3m file keys", list(fobj.keys()), "equal", fobj.get("equal"))
