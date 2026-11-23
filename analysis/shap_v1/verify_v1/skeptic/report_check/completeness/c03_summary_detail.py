"""Read-only: print selected parts of V\\reconcile\\work\\summary.json in full."""
import json

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\summary.json"
S = json.load(open(P, "r", encoding="utf-8"))


def find(o, name, path=""):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            p = path + "/" + str(k)
            if k == name:
                out.append((p, v))
            out.extend(find(v, name, p))
    return out


print("TOP KEYS", list(S.keys()))
for name in ("second_checks",):
    for p, v in find(S, name):
        tot = {"n": 0, "official_table_eq_unrounded": 0, "A_eq": 0, "B_eq": 0}
        for prob, d in v.items():
            for k in tot:
                tot[k] += d.get(k, 0)
            print(p, prob, {k: d.get(k) for k in tot}, "not_ok:", len(d.get("not_ok", [])))
            for row in d.get("not_ok", []):
                print("    ", json.dumps(row))
        print("TOTALS", tot)
        print("other keys in a second_checks entry:", sorted(set().union(*[set(d.keys()) for d in v.values()])))

for p, v in find(S, "b1"):
    if not isinstance(v, dict) or "fire" not in v:
        continue
    for prob, d in v.items():
        print("== b1", prob)
        for k in ("A_status", "B_status", "meta", "nonzero_counts", "nonzero_vs_meta", "A_run", "B_run", "log",
                  "identity_reconciler", "A_identity", "B_identity"):
            if k in d:
                print("  ", k, json.dumps(d[k])[:900])

for p, v in find(S, "independence"):
    for prob, d in v.items():
        print("== independence", prob, json.dumps(d.get("compare_file_mtimes"))[:900])

for p, v in find(S, "per_draw"):
    tot_ok = {}
    for k, d in v.items():
        for kk, dd in d.items():
            print("per_draw", k, kk, {x: (dd[x] if not isinstance(dd[x], list) else ("list", len(dd[x]))) for x in dd})

for p, v in find(S, "pairs_with_no_sign_determined_in_both"):
    print(p, json.dumps(v))
