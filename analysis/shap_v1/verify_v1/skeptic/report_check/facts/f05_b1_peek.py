import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))

def tree(o, depth=0, maxdepth=4, prefix=""):
    if depth > maxdepth:
        return
    if isinstance(o, dict):
        for k, v in list(o.items())[:40]:
            if isinstance(v, (dict, list)):
                print("  " * depth + f"{k}: {type(v).__name__}({len(v)})")
                if k not in ("players",):
                    tree(v, depth + 1, maxdepth)
            else:
                print("  " * depth + f"{k}: {repr(v)[:120]}")
    elif isinstance(o, list):
        if o and isinstance(o[0], (dict, list)):
            tree(o[0], depth + 1, maxdepth)

print("A b1 keys", list(A["b1"].keys()))
tree(A["b1"]["fire"], 0, 3)
print("-----B")
print("B b1 keys", list(B["b1"].keys()))
tree(B["b1"]["fire"], 0, 3)
