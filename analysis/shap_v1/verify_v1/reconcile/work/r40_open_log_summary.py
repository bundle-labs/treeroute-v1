"""Summarise work\\opened_official.jsonl: the first opening of each official file (in order) and the later reads."""
import json, collections

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\opened_official.jsonl"
rows = [json.loads(x) for x in open(P, encoding="utf-8") if x.strip()]
first = collections.OrderedDict()
later = collections.defaultdict(list)
for r in rows:
    if r["file"] not in first:
        first[r["file"]] = r
    else:
        later[r["by"]].append(r["time"])
print("total opens:", len(rows), "distinct files:", len(first))
for i, (f, r) in enumerate(first.items(), 1):
    print("%2d %s %s (%s)" % (i, r["time"], f, r["by"]))
for by, ts in later.items():
    print("later reads by %s: %d opens, from %s to %s" % (by, len(ts), min(ts), max(ts)))
