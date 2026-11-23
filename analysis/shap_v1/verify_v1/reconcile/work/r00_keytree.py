"""Exploration: print the key tree of A's and B's results.json (structure only, collapsing player maps)."""
import json, sys

V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def tree(o, depth=0, maxdepth=9, path=""):
    pad = "  " * depth
    if isinstance(o, dict):
        keys = list(o.keys())
        collapse = len(keys) > 12
        shown = keys[:4] if collapse else keys
        for k in shown:
            v = o[k]
            if isinstance(v, (dict, list)):
                desc = type(v).__name__ + ("[%d]" % len(v))
                print(pad + str(k) + ": " + desc)
                if depth < maxdepth:
                    tree(v, depth + 1, maxdepth, path + "/" + str(k))
            else:
                s = repr(v)
                print(pad + str(k) + ": " + (s[:100]))
        if collapse:
            print(pad + "... (%d keys total)" % len(keys))
    elif isinstance(o, list):
        if o and isinstance(o[0], (dict,)):
            tree(o[0], depth + 1, maxdepth, path + "[0]")
        else:
            print(pad + repr(o[:6])[:150])


for X in sys.argv[1:]:
    with open(V + "\\" + X + "\\results.json", encoding="utf-8") as f:
        R = json.load(f)
    print("=" * 30, X)
    top = {k: v for k, v in R.items() if k not in ("problems", "b1")}
    tree(top, 0, 2)
    print("--- problems.fire")
    tree(R["problems"]["fire"], 0, 7)
    print("--- b1.ndvi")
    tree(R["b1"]["ndvi"], 0, 6)
    print("--- b1.defo")
    tree(R["b1"]["defo"], 0, 6)
