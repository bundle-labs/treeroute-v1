"""Skeptic: per mismatch group, the distribution of the status codes (AB, AO, BO, AOd, BOd), so that a group whose
diagnosis says "A and B agree" can be checked against the keys it holds. Also: the keys whose AB status is not
'match' (any group), listed in full."""
import collections
import json
import os

RC = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile"
OUT = r"D:\treeroute\analysis\shap_v1\verify_v1\skeptic\reconcile\out"
with open(os.path.join(RC, "mismatches.json"), encoding="utf-8") as f:
    M = json.load(f)
cols = M["columns"]
print("columns:", cols)
tally = collections.defaultdict(collections.Counter)
ab_not_match = []
for rec in M["keys"]:
    key, g, sec, st = rec[0], rec[1], rec[2], rec[3]
    tally[g][st] += 1
    d = dict(x.split("=") for x in st.split())
    if d.get("AB") not in ("match",):
        ab_not_match.append(rec)
for g, c in tally.items():
    print("==", g)
    for st, n in c.most_common():
        print("   %6d  %s" % (n, st))
print("== keys with AB != match:", len(ab_not_match))
for rec in ab_not_match:
    print(json.dumps(rec)[:400])
