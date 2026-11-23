"""Read-only: print the structure of V\\reconcile\\work\\summary.json (keys, scalar values, list lengths)."""
import json

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\summary.json"
S = json.load(open(P, "r", encoding="utf-8"))


def walk(o, path, depth, maxdepth):
    if isinstance(o, dict):
        if depth >= maxdepth:
            print("  " * depth + path + " {dict, %d keys: %s}" % (len(o), ", ".join(list(o.keys())[:12])))
            return
        for k, v in o.items():
            walk(v, path + "/" + str(k), depth + 1, maxdepth)
    elif isinstance(o, list):
        if len(o) <= 6 and all(not isinstance(x, (dict, list)) for x in o):
            print("  " * depth + path + " = " + json.dumps(o)[:300])
        else:
            print("  " * depth + path + " [list, %d]" % len(o) + (" first=" + json.dumps(o[0])[:300] if o else ""))
    else:
        s = json.dumps(o)
        print("  " * depth + path + " = " + s[:300])


walk(S, "", 0, 3)
