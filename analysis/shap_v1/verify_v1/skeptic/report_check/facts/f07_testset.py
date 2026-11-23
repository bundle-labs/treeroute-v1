import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))

def find(o, name, path=""):
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            p = path + "/" + k
            if k == name:
                out.append((p, v))
            out.extend(find(v, name, p))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            out.extend(find(v, name, path + f"[{i}]"))
    return out

for who, R in (("A", A), ("B", B)):
    print("=" * 10, who)
    for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
        hits = find(R["problems"][p], "test_set_records")
        for path, v in hits:
            print(p, path, json.dumps(v)[:1500])
        hits = find(R["problems"][p], "test_set_columns")
        for path, v in hits:
            print(p, path, "n=", len(v) if isinstance(v, list) else type(v).__name__)
        fam = R["problems"][p]["levels"]["variable"].get("families", {})
        print(p, "families keys:", list(fam.keys())[:20])
        gi = fam.get("global_indices")
        if gi is not None:
            print(p, "global_indices:", (len(gi) if isinstance(gi, list) else gi))

# set diffs of test_set_columns
for p in ["coral", "defo", "fire", "pm25", "ndvi"]:
    a = A["problems"][p]["levels"]["variable"]["families"]["test_set_columns"]
    b = B["problems"][p]["levels"]["variable"]["families"]["test_set_columns"]
    sa, sb = set(a), set(b)
    print(p, "A", len(a), "B", len(b), "onlyA", len(sa - sb), sorted(sa - sb)[:60], "onlyB", sorted(sb - sa))
