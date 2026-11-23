# Skeptic (version 3 check, item 5): the constant "passed (the adopted arm)" of S3.18 a and S3.20 against each
# treeroute meta.json (guard, arm) and the rebuild record's result. Read-only; prints only.
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
SHAP = r"D:\treeroute\analysis\shap_v1"
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    m = json.load(open(SHAP + r"\out\%s\lead_0\treeroute\meta.json" % p, encoding="utf-8"))
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    gd = m.get("guard")
    print("%-5s meta guard: %s | arm: %s | rebuild result: %s" % (
        p, json.dumps(gd, ensure_ascii=False)[:300], m.get("arm"), json.dumps(g.get("result"), ensure_ascii=False)[:200]))
