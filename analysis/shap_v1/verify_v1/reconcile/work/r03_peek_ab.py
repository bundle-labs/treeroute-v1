"""Exploration: print a few A/B objects (representation of undefined numbers, sign agreement, main row, item 8)."""
import json, sys

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
RES = {}
for X in ("A", "B"):
    with open(V + "\\" + X + "\\results.json", encoding="utf-8") as f:
        RES[X] = json.load(f)


def get(R, path):
    o = R
    for k in path.split("/"):
        o = o[k]
    return o


def strip(o, depth=0):
    if isinstance(o, dict):
        return {k: strip(v, depth + 1) for k, v in o.items() if k not in ("players",) and not (
            k.endswith("_why") and depth > 0) and k != "extra"}
    if isinstance(o, list) and len(o) > 12:
        return o[:12] + ["...%d" % len(o)]
    return o


for path in sys.argv[1:]:
    for X in ("A", "B"):
        try:
            o = get(RES[X], path)
        except KeyError as e:
            o = "KEYERROR %s" % e
        print("=====", X, path)
        print(json.dumps(strip(o), indent=1)[:4000])
