"""Exploration: per group, how many keys have each A-vs-B / A-vs-official / B-vs-official status."""
import json, collections

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\mismatches.json"
M = json.load(open(P, encoding="utf-8"))
c = collections.defaultdict(collections.Counter)
for rec in M["keys"]:
    key, g, sec, st = rec[0], rec[1], rec[2], rec[3]
    d = dict(x.split("=") for x in st.split())
    c[g]["AB=" + d["AB"]] += 1
    if "AO" in d:
        c[g]["AO=" + d["AO"]] += 1
        c[g]["BO=" + d["BO"]] += 1
for g, v in c.items():
    print(g, dict(v))
print("groups:", [(x["group"], x["n_keys"], x["kind"]) for x in M["groups"]])
print("n_mismatch_keys", M["n_mismatch_keys"], "keys listed", len(M["keys"]),
      "no-number keys", len(M["keys_without_a_number_anywhere"]["keys"]))
