"""Read-only: tally V\\reconcile\\mismatches.json statuses per group (to check report.md A2)."""
import collections
import json

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\mismatches.json"
M = json.load(open(P, "r", encoding="utf-8"))
print("columns", M["columns"])
print("status_codes", json.dumps(M["status_codes"])[:1500])
print("what", str(M["what"])[:600])
print("groups type", type(M["groups"]).__name__)
if isinstance(M["groups"], dict):
    for g, v in M["groups"].items():
        print("  group", g, json.dumps(v)[:400])
elif isinstance(M["groups"], list):
    for v in M["groups"]:
        print("  group", json.dumps(v)[:400])
cols = M["columns"]
E = M["keys"]
print("n keys", len(E), "example", json.dumps(E[0])[:400])
ix = {c: i for i, c in enumerate(cols)}
tally = collections.OrderedDict()
for e in E:
    g = e[ix["group"]] if "group" in ix else None
    d = tally.setdefault(g, collections.OrderedDict())
    d["n"] = d.get("n", 0) + 1
    for f in cols:
        if f in ("key", "group", "A", "B", "official", "A_value", "B_value", "official_value", "O"):
            continue
        val = e[ix[f]]
        if isinstance(val, (list, dict)):
            val = json.dumps(val)[:40]
        c = d.setdefault(f, collections.Counter())
        c[val] += 1
for g, d in tally.items():
    print("== %s n=%d" % (g, d["n"]))
    for f, c in d.items():
        if f == "n":
            continue
        print("     %-16s %s" % (f, dict(c) if len(c) < 12 else ("%d distinct" % len(c))))
kw = M["keys_without_a_number_anywhere"]
print("keys_without_a_number_anywhere", type(kw).__name__, len(kw) if hasattr(kw, "__len__") else kw)
