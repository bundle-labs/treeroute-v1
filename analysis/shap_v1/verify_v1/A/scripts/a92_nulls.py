# Round 14, implementer A: list every null number of results.json (value or statistic), grouped by problem.
import json, os
from collections import defaultdict

V_A = r"D:\treeroute\analysis\shap_v1\verify_v1\A"
with open(os.path.join(V_A, "results.json"), "r", encoding="utf-8") as fh:
    r = json.load(fh)

out = defaultdict(list)


def walk(node, path, top):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "extra" or k.endswith("_why"):
                continue
            if v is None and k not in ("ci_low", "ci_high", "n_finite"):
                out[top].append(("/".join(path + [k]), node.get(k + "_why", "")))
            elif isinstance(v, dict) and set(("value", "ci_low", "ci_high", "n_finite")) <= set(v):
                if v["value"] is None:
                    out[top].append(("/".join(path + [k, "value"]), v.get("value_why", "")))
                if v["n_finite"] is not None and v["n_finite"] < 2000 and path and path[0] != "players":
                    out[top + " (n_finite<2000)"].append(("/".join(path + [k]), str(v["n_finite"])))
            else:
                walk(v, path + [k], top)


for p, pr in r["problems"].items():
    walk(pr, [], p)
for p, b in r["b1"].items():
    walk(b, [], "b1/" + p)
for top in sorted(out):
    items = out[top]
    # compress per-player repeats
    print("==", top, len(items))
    seen = defaultdict(int)
    for path, why in items:
        key = path
        parts = path.split("/")
        if "players" in parts:
            i = parts.index("players")
            key = "/".join(parts[:i + 1]) + "/<player>/" + "/".join(parts[i + 2:])
        seen[(key, why)] += 1
    for (k, why), n in sorted(seen.items()):
        print("   %s (x%d) :: %s" % (k, n, why[:140]))
