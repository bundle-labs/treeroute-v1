import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
s = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
print("INDEPENDENCE")
print(json.dumps(s["independence"], indent=1)[:12000])
print("B1")
for p, d in s["b1"].items():
    dd = {k: v for k, v in d.items()}
    print(p, json.dumps(dd, indent=1)[:6000])
