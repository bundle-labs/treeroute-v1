# n15: pass flags of every rebuild gate on the five problems (read-only), and the sign-agreement entries with no finite
# draw in results.json (to confirm they carry no interval).
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
S = r"D:\treeroute\analysis\shap_v1"
for p in ("pm25", "ndvi", "fire", "defo", "coral"):
    g = json.load(open(os.path.join(S, "rebuild", p, "lead_0", "gates.json"), encoding="utf-8"))
    fails = [k for k, v in g["gates"].items() if not v.get("pass")]
    print(p, "gates", len(g["gates"]), "not passed:", fails, "stopped_at:", g.get("stopped_at"))
R = json.load(open(os.path.join(S, r"verify_v1\A\results.json"), encoding="utf-8"))
for p in ("fire", "ndvi"):
    for lv in ("feature", "variable"):
        for k, pr in R["problems"][p]["levels"][lv]["pairs"].items():
            sa = pr.get("sign_agreement")
            if sa and sa.get("n_finite") == 0:
                print(p, lv, k, {kk: vv for kk, vv in sa.items() if kk in ("value", "ci_low", "ci_high", "n_finite")})
