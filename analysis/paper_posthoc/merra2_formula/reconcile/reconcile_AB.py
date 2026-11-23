"""Part 624 reconciliation: compare implementer A's and B's row-level predictions and headline numbers (read-only)."""
import hashlib, json, sys
import numpy as np, pandas as pd
R = r"D:/treeroute/analysis/paper_posthoc/merra2_formula"
PAIRS = {
    "merra2_lag1 full": ("A/preds_merra2_lag1_full.parquet", "B/preds_merra2_lag1_oc1_full.parquet"),
    "merra2_lag1 forced F5": ("A/preds_merra2_lag1_forcedF5.parquet", "B/preds_merra2_lag1_oc1_forcedF5logc.parquet"),
    "merra2_same full": ("A/preds_merra2_same_full.parquet", "B/preds_merra2_same_oc1_full.parquet"),
    "placebo full": ("A/preds_merra2_lag1_placebo_full.parquet", "B/preds_merra2_lag1_placebo_oc1_full.parquet"),
    "sulfate side check": ("A/preds_merra2_lag1_gmao_full.parquet", "B/preds_merra2_lag1_oc1_so4gmao_forcedF5logc.parquet"),
    "locked repro": ("A/preds_merra2_lag1_locked_repro.parquet", "B/preds_merra2_lag1_locked_repro.parquet"),
}
KEYS = ["unit", "time", "lead"]
out = {}
for name, (a, b) in PAIRS.items():
    A = pd.read_parquet(f"{R}/{a}"); B = pd.read_parquet(f"{R}/{b}")
    cols = [c for c in ("x_locked", "x_new", "raw", "guarded") if c in A.columns and c in B.columns]
    m = A[KEYS + cols].merge(B[KEYS + cols], on=KEYS, how="outer", suffixes=("_A", "_B"), indicator=True)
    r = {"rows_A": len(A), "rows_B": len(B), "only_A": int((m._merge == "left_only").sum()), "only_B": int((m._merge == "right_only").sum())}
    both = m[m._merge == "both"]
    for c in cols:
        x, y = both[c + "_A"].to_numpy(float), both[c + "_B"].to_numpy(float)
        nan_mismatch = int((np.isnan(x) != np.isnan(y)).sum())
        ok = ~np.isnan(x) & ~np.isnan(y)
        r[c] = {"max_abs_diff": float(np.max(np.abs(x[ok] - y[ok]))) if ok.any() else None, "nan_mismatch": nan_mismatch, "n": int(ok.sum())}
    out[name] = r
ra = json.load(open(f"{R}/A/result_A.json", encoding="utf-8")); rb = json.load(open(f"{R}/B/result_B.json", encoding="utf-8"))
out["_sha256"] = {p: hashlib.sha256(open(f"{R}/{p}", "rb").read()).hexdigest() for p in ("A/result_A.json", "B/result_B.json", "reconcile/reconcile_AB.py")}
json.dump(out, open(f"{R}/reconcile/reconcile_AB.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
