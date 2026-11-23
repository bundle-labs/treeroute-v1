# Skeptic (version 3 check, item 2e): what the rebuild records hold for the gates whose "What it checks" text version 3
# rewords (E3a, E3m, E3, E6, E10), per problem. Read-only; prints only (values shortened).
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"


def short(v, n=700):
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= n else s[:n] + " ...(%d chars)" % len(s)


for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    G = g["gates"]
    print("==", p, "| gate keys in order:", list(G))
    for k in G:
        if k.startswith(("E3", "E6", "E10")):
            v = G[k].get("values")
            print("  ", k, "pass:", G[k].get("pass"))
            if isinstance(v, dict):
                for kk, vv in v.items():
                    print("      .%s = %s" % (kk, short(vv)))
            else:
                print("      values =", short(v))
