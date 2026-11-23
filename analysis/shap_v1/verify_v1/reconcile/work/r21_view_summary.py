"""Exploration: print chosen parts of work\\summary.json (argv: top-level keys; 'b1:<p>' for one B1 problem)."""
import json, sys

S = json.load(open(r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\summary.json", encoding="utf-8"))
for k in sys.argv[1:]:
    if k.startswith("b1:"):
        o = S["b1"][k[3:]]
        o = {kk: vv for kk, vv in o.items() if kk not in ("A_status", "B_status")}
        print("=====", k)
        print(json.dumps(o, indent=1)[:6000])
    elif k == "matched_patterns":
        print("=====", k, len(S[k]))
        for pat, n in S[k]:
            print("  %6d %s" % (n, pat))
    else:
        print("=====", k)
        print(json.dumps(S[k], indent=1)[:8000])
