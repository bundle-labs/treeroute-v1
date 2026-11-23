import json, collections
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
rows = [json.loads(l) for l in open(V + r"\reconcile\work\opened_official.jsonl", encoding="utf-8") if l.strip()]
print("n rows", len(rows))
print("keys of first", list(rows[0].keys()))
print("first 3", rows[:3])
print("last 3", rows[-3:])
by_script = collections.Counter()
for r in rows:
    by_script[(r.get("by") or r.get("script") or r.get("who") or "?", r.get("how") or r.get("mode") or r.get("kind") or "")] += 1
print(by_script)
# figure out field names
fields = collections.Counter()
for r in rows:
    for k in r:
        fields[k] += 1
print(fields)
