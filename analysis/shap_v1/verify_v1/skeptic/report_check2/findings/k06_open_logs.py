# Read-only. Summarise the reconciler's two open logs: who read what, when (A1 items 1 and 3; section 1's
# "its runs from 18:34:26 to 18:46:03").
import collections
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
for name in ("opened_official.jsonl", "opened_other.jsonl"):
    rows = [json.loads(l) for l in open(V + r"\reconcile\work\\" + name, encoding="utf-8") if l.strip()]
    print("==", name, len(rows), "entries; keys:", sorted(rows[0].keys()))
    by = collections.defaultdict(list)
    for r in rows:
        by[r.get("by")].append(r)
    for b, rs in by.items():
        ts = sorted(str(r.get("time") or r.get("t") or r.get("when")) for r in rs)
        modes = collections.Counter(str(r.get("mode") or r.get("how") or "") for r in rs)
        print("   by %-28s n %4d  first %s  last %s  modes %s" % (b, len(rs), ts[0], ts[-1], dict(modes)))
    paths = collections.Counter()
    for r in rows:
        p = str(r.get("path") or r.get("file"))
        low = p.lower()
        if "\\verify_v1\\" in low:
            paths["inside V"] += 1
        elif "\\compare\\" in low:
            paths["compare"] += 1
        else:
            paths["other SHAP"] += 1
    print("   path classes:", dict(paths))
