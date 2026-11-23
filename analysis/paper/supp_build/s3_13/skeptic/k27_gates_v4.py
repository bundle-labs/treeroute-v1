# Skeptic (version 4 check, item 2): what the five rebuild records (SHAP\rebuild\<p>\lead_0\gates.json) hold for the
# gates whose "What it checks" text version 4 rewords (E3a, E3m, E3, E5, E8) and for the result (the adopted arm).
# Path-like string values are masked. Read-only; prints only.
import json, re, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
pathlike = re.compile(r"(?i)[a-z]:[\\/]|[\\/]users[\\/]|\\\\")


def mask(v):
    if isinstance(v, str):
        return "<path>" if pathlike.search(v) else v
    if isinstance(v, list):
        return [mask(x) for x in v]
    if isinstance(v, dict):
        return {k: mask(x) for k, x in v.items()}
    return v


def short(v, n=900):
    s = json.dumps(mask(v), ensure_ascii=False, sort_keys=False)
    return s if len(s) <= n else s[:n] + " ...(%d chars)" % len(s)


for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    G = g["gates"]
    print("=" * 20, p, "| top-level keys:", list(g), "| gate keys:", list(G))
    print("  result:", short(g.get("result"), 1200))
    for k in G:
        if k.startswith(("E3", "E5", "E8")):
            v = G[k].get("values")
            print("  %s pass=%s | gate keys %s" % (k, G[k].get("pass"), list(G[k])))
            if isinstance(v, dict):
                for kk, vv in v.items():
                    print("      .%s = %s" % (kk, short(vv)))
            else:
                print("      values =", short(v))
            for kk in G[k]:
                if kk not in ("values", "pass"):
                    print("      [%s] = %s" % (kk, short(G[k][kk], 500)))
