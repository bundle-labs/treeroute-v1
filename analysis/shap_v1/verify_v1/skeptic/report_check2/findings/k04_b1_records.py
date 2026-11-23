# Read-only. Compare the B1 records that work\summary.json keeps side by side for A and B
# (A1 item 17's claim: "A's equal B's in every field for all five problems").
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
S = json.load(open(V + r"\reconcile\work\summary.json", encoding="utf-8"))
b1 = S.get("b1")
print("summary.json top-level keys:", list(S)[:40])
print("b1 type:", type(b1).__name__, "keys:", list(b1) if isinstance(b1, dict) else None)
for p, d in (b1 or {}).items():
    if not isinstance(d, dict):
        print(p, "->", repr(d)[:200])
        continue
    ks = list(d)
    print("==", p, ks)
    pairs = {}
    for k in ks:
        if k.startswith("A_"):
            pairs.setdefault(k[2:], [None, None])[0] = d[k]
        elif k.startswith("B_"):
            pairs.setdefault(k[2:], [None, None])[1] = d[k]
    for name, (a, b) in pairs.items():
        print("   %s: A == B -> %s" % (name, a == b))
        if a != b:
            print("      A:", json.dumps(a)[:400])
            print("      B:", json.dumps(b)[:400])
    for k in ks:
        if not (k.startswith("A_") or k.startswith("B_")):
            print("   other field", k, json.dumps(d[k])[:300])
