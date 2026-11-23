import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
rows = [json.loads(l) for l in open(V + r"\reconcile\work\opened_other.jsonl", encoding="utf-8") if l.strip()]
print("n rows", len(rows), "fields", collections.Counter(k for r in rows for k in r))
files = collections.OrderedDict()
for r in rows:
    f = r.get("file")
    files.setdefault(f, []).append((r.get("time"), r.get("by"), r.get("what") or r.get("note") or r.get("how")))
print("distinct files", len(files))
for f, lst in files.items():
    ts = sorted(x[0] for x in lst)
    bys = sorted(set(str(x[1]) for x in lst))
    whats = sorted(set(str(x[2]) for x in lst))
    print(f"{len(lst):3d} {ts[0][11:19]}..{ts[-1][11:19]} {f}  by={bys} what={whats[:2]}")
