"""n05: structure of reconcile\work\summary.json and of mismatches.json (keys only, small values). Read-only."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
S = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
print("summary top keys:", list(S.keys()))
for k, v in S.items():
    if isinstance(v, dict):
        print("  %s: dict keys %s" % (k, list(v.keys())[:30]))
    else:
        print("  %s: %s" % (k, json.dumps(v)[:300]))
print()
print("second_checks:", json.dumps(S.get("second_checks"))[:3000])
print()
print("verdicts:", json.dumps(S.get("verdicts"))[:2000])
print()
b1 = S.get("b1")
if isinstance(b1, dict):
    for p, v in b1.items():
        print("b1", p, ":", list(v.keys()) if isinstance(v, dict) else v)

M = json.load(open(V + r"\reconcile\mismatches.json", encoding="utf-8"))
print()
print("mismatches top keys:", list(M.keys()) if isinstance(M, dict) else type(M))
if isinstance(M, dict):
    for k, v in M.items():
        if isinstance(v, list):
            print("  %s: list(%d) first %s" % (k, len(v), json.dumps(v[0])[:600] if v else None))
        elif isinstance(v, dict):
            print("  %s: dict(%d) keys %s" % (k, len(v), list(v.keys())[:20]))
        else:
            print("  %s: %s" % (k, json.dumps(v)[:300]))
