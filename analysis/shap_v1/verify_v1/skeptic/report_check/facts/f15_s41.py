import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
t = json.load(open(V + r"\skeptic\numbers\work\s41_tie_artifacts.json", encoding="utf-8"))
print("pairs in s41:", len(t))
for k, v in t.items():
    coinc = {}
    for var in ("base", "tie_ci", "tie_desc"):
        d = v.get(var, {})
        for kk in ("coincidental_top5", "coincidental_top10", "coincidental_top20"):
            if d.get(kk):
                coinc.setdefault(var, {})[kk] = d[kk]
    sp = v.get("spread", {})
    mx = max((abs(x) for x in sp.values() if isinstance(x, (int, float))), default=0)
    flag = "BARDL" if "bardl" in k else ""
    print(f"{k:45s} maxspread={mx:.3g} spread={ {a: float('%.3g' % b) for a, b in sp.items()} } coinc={coinc} zeros={v.get('zeros_in_J')} {flag}")
b = t.get("ndvi/variable/rival_bardl_h1|treeroute")
print(json.dumps(b, indent=1)[:3000])
