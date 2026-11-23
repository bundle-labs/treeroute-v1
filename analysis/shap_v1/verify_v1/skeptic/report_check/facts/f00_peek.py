import json, sys
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
m = json.load(open(V + r"\reconcile\mismatches.json", encoding="utf-8"))
print(type(m))
if isinstance(m, dict):
    for k, v in m.items():
        if isinstance(v, (list, dict)):
            print(k, type(v).__name__, len(v))
        else:
            print(k, repr(v)[:300])
    for k, v in m.items():
        if isinstance(v, list) and v:
            print("first of", k, json.dumps(v[0])[:1500])
            if len(v) > 1:
                print("second of", k, json.dumps(v[1])[:1500])
        if isinstance(v, dict):
            ks = list(v.keys())[:10]
            print("keys of", k, ks)
            for kk in ks[:3]:
                print("  ", kk, json.dumps(v[kk])[:1500])
s = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
print("SUMMARY type", type(s))
if isinstance(s, dict):
    for k, v in s.items():
        if isinstance(v, (list, dict)):
            print(k, type(v).__name__, len(v), json.dumps(v)[:600])
        else:
            print(k, repr(v)[:300])
