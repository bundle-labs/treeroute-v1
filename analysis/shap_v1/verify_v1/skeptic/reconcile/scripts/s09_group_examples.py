"""Skeptic: print the full records of the small mismatch groups (the ones whose diagnosis carries the most weight)."""
import json
import os

RC = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
with open(os.path.join(RC, "mismatches.json"), encoding="utf-8") as f:
    M = json.load(f)
want = {"fire_main_row_missing", "C23_median_rival_name", "undefined_nan_zero_replicates", "C22_range_no_interval",
        "C15_feature_family_tvd_B1", "test_set_columns_text"}
for rec in M["keys"]:
    if rec[1] in want:
        s = json.dumps(rec)
        print(s if len(s) < 700 else s[:700] + " ...")
# C15_empty_family: coral main row
for rec in M["keys"]:
    if rec[1] == "C15_empty_family" and "/main_row/" in rec[0]:
        print(json.dumps(rec))
# sign_agreement_no_interval: a few, with the pair
n = 0
for rec in M["keys"]:
    if rec[1] == "sign_agreement_no_interval" and n < 6:
        print(json.dumps(rec))
        n += 1
for g in M["groups"]:
    if g["group"] in ("sign_agreement_no_interval", "fire_main_row_missing", "C15_empty_family"):
        print(g["group"], g["affects_reported_numbers"], g["kind"])
