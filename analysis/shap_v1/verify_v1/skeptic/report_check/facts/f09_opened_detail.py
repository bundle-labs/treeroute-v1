import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
rows = [json.loads(l) for l in open(V + r"\reconcile\work\opened_official.jsonl", encoding="utf-8") if l.strip()]
by = collections.defaultdict(list)
for r in rows:
    by[r["by"]].append(r)
for k, lst in by.items():
    ts = sorted(r["time"] for r in lst)
    print(k, len(lst), ts[0], ts[-1])
    files = collections.Counter(r["file"] for r in lst)
    print("   distinct files", len(files), "count per file", sorted(set(files.values())))
    # run starts: distinct times grouped
    tc = collections.Counter(r["time"][11:19] for r in lst)
    print("   times:", sorted(tc.items()))
# first openings in order
r10 = by["work\\r10_open_official.py"]
for i, r in enumerate(r10, 1):
    print(i, r["time"][11:19], r["file"])
# reconcile.py bytes reads
for r in by["reconcile.py (bytes, for its SHA-256)"]:
    print("bytes", r["time"][11:19], r["file"])
for r in by["work\\r30_tables.py"]:
    print("r30", r["time"][11:19], r["file"])
# check first-ever open per file
first = {}
for r in rows:
    if r["file"] not in first or r["time"] < first[r["file"]]["time"]:
        first[r["file"]] = r
print("distinct files overall", len(first))
print("earliest", min(r["time"] for r in rows))
# is any reconcile.py open earlier than the last r10 open?
print("r10 last", max(r["time"] for r in r10))
