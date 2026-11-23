# Exploration only (builder B): key tree of V\A\results.json and the objects the spec names. Writes nothing.
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
with open(os.path.join(V, "A", "results.json"), "r", encoding="utf-8") as f:
    A = json.load(f)


def tree(o, prefix="", depth=0, maxd=3):
    if isinstance(o, dict):
        if depth >= maxd:
            print(prefix, "{%d keys: %s}" % (len(o), ", ".join(list(o.keys())[:8])))
            return
        for k, v in o.items():
            if isinstance(v, (dict, list)):
                tree(v, prefix + "." + k, depth + 1, maxd)
            else:
                print(prefix + "." + k, "=", repr(v)[:100])
    elif isinstance(o, list):
        print(prefix, "[list len %d] first: %s" % (len(o), repr(o[0])[:120] if o else ""))
    else:
        print(prefix, repr(o)[:100])


print("top keys", list(A.keys()))
for k in A:
    if k not in ("problems", "b1"):
        tree(A[k], k, 0, 2)
print("problems keys", list(A["problems"].keys()))
p = A["problems"]["fire"]
print("fire keys", list(p.keys()))
print("fire levels keys", list(p["levels"].keys()))
lv = p["levels"]["variable"]
print("fire variable keys", list(lv.keys()))
print("fire variable pairs keys", list(lv["pairs"].keys()))
pk = list(lv["pairs"].keys())[0]
print("pair object keys", list(lv["pairs"][pk].keys()))
print("sign_agreement", lv["pairs"][pk]["sign_agreement"])
print("sign_n_determined", lv["pairs"][pk]["sign_n_determined"])
print("fire main_row", json.dumps(p.get("main_row"), indent=None)[:3000])
print()
print("b1 keys", list(A["b1"].keys()))
for q, b in A["b1"].items():
    print("== b1", q, "keys", list(b.keys()))
    print("   status", b.get("status"))
    if "run" in b:
        print("   run", b["run"])
    if "identity" in b:
        print("   identity", b["identity"])
    for L in ("variable", "feature"):
        if L in b:
            print("   ", L, "keys", list(b[L].keys()))
            bl = b[L]
            if "pair_main_b1" in bl:
                for kk, vv in bl["pair_main_b1"].items():
                    print("      pair_main_b1.%s = %s" % (kk, vv))
            if "importance" in bl:
                imp = bl["importance"]
                print("      importance keys", list(imp.keys())[:10])
                print("      importance.n_nonzero", imp.get("n_nonzero"))
            if "top10" in bl:
                print("      top10", bl["top10"])
            if "top3" in bl:
                print("      top3", bl["top3"])
            if "families" in bl:
                for fk, fv in bl["families"].items():
                    print("      families.%s = %s" % (fk, fv))
            if "own_history_share" in bl:
                print("      own_history_share", bl["own_history_share"])
