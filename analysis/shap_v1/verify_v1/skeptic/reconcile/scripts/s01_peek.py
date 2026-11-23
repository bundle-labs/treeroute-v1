"""Skeptic (round 14, reconciliation lens): peek at the reconciler's mismatches.json header and summary.json.
Read-only on V\\reconcile; writes only into V\\skeptic\\reconcile\\out."""
import json
import os
import collections

RC = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\reconcile\out"

with open(os.path.join(RC, "mismatches.json"), encoding="utf-8") as f:
    M = json.load(f)
head = {k: v for k, v in M.items() if k not in ("keys", "keys_without_a_number_anywhere")}
print(json.dumps({k: head[k] for k in ("key_counts", "number_counts", "n_mismatch_keys")}, indent=1))
for g in head["groups"]:
    print("%-32s %-12s affects=%-5s n=%d" % (g["group"], g["kind"], g["affects_reported_numbers"], g["n_keys"]))
print("keys rows:", len(M["keys"]))
print("no-number keys:", len(M["keys_without_a_number_anywhere"]["keys"]))

with open(os.path.join(RC, "work", "summary.json"), encoding="utf-8") as f:
    S = json.load(f)
print("summary top keys:", list(S.keys()))
for k in ("key_counts", "number_counts", "verdicts", "groups", "derived_second_check", "seconds", "no_number_keys_count",
          "closeness", "structural_zero_rows_official", "pairs_with_no_sign_determined_in_both", "by_item"):
    print("==", k)
    print(json.dumps(S.get(k), indent=1)[:3000])
