"""Read-only: compare A's and B's test-set records (columns read, folder named) per problem."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
R = {X: json.load(open(V + "\\" + X + r"\results.json", encoding="utf-8")) for X in ("A", "B")}

for p in ("coral", "defo", "fire", "pm25", "ndvi"):
    print("==", p)
    for X in ("A", "B"):
        fam = R[X]["problems"][p]["levels"]["variable"]["families"]
        print("  ", X, "families keys:", list(fam.keys()))
        for k, v in fam.items():
            if k in ("test_set_columns",):
                continue
            if "test" in k or "record" in k:
                print("     ", k, json.dumps(v)[:600])
    ca = set(R["A"]["problems"][p]["levels"]["variable"]["families"].get("test_set_columns") or [])
    cb = set(R["B"]["problems"][p]["levels"]["variable"]["families"].get("test_set_columns") or [])
    print("   n cols A", len(ca), "B", len(cb))
    oa = sorted(ca - cb)
    ob = sorted(cb - ca)
    print("   only A (%d):" % len(oa), oa[:20], "..." if len(oa) > 20 else "")
    print("   only B (%d):" % len(ob), ob[:20])
    kinds = {}
    for c in oa:
        k = "hist" if c.startswith("x__hist_") else ("ctx" if c.startswith("c__") else "other")
        kinds[k] = kinds.get(k, 0) + 1
    print("   only-A kinds", kinds)
