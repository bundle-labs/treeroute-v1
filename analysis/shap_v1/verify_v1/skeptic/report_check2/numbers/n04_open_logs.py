"""n04: counts and times of the reconciler's open logs (A1 item 3; section 1). Read-only; prints only."""
import json
from collections import Counter, defaultdict

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
for name in ("opened_official.jsonl", "opened_other.jsonl"):
    p = V + "\\reconcile\\work\\" + name
    rows = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    print("=====", name, "entries:", len(rows), "distinct files:", len(set(r["file"] for r in rows)))
    by = Counter(r["by"] for r in rows)
    print("  by:", dict(by))
    t = defaultdict(list)
    for r in rows:
        t[r["by"]].append(r["time"])
    for k, v in t.items():
        print("   %s: %s to %s (%d)" % (k, min(v), max(v), len(v)))
    # runs of reconcile.py: split where the time gap > 20 s
    rr = sorted(r["time"] for r in rows if r["by"].startswith("reconcile.py"))
    runs = []
    prev = None
    from datetime import datetime
    for s in rr:
        d = datetime.fromisoformat(s)
        if prev is None or (d - prev).total_seconds() > 20:
            runs.append([s, s, 0])
        runs[-1][1] = s
        runs[-1][2] += 1
        prev = d
    print("  reconcile.py runs (gap > 20 s):", len(runs))
    for r in runs:
        print("    ", r)
    # top-level folders
    tops = Counter("\\".join(r["file"].split("\\")[:2]) for r in rows)
    print("  top folders:", dict(tops))
    # paths outside SHAP?
    out = [r["file"] for r in rows if not r["file"].startswith("SHAP\\")]
    print("  entries not under SHAP\\:", len(out), out[:5])
    # compare files among other? V files?
    print("  entries under SHAP\\verify_v1:", sum(1 for r in rows if r["file"].startswith("SHAP\\verify_v1")))
    print("  entries under SHAP\\scripts:", sum(1 for r in rows if r["file"].startswith("SHAP\\scripts")))
    print("  PROTOCOL.md entries:", sum(1 for r in rows if "PROTOCOL" in r["file"]))
    if name == "opened_official.jsonl":
        first = [r for r in rows if "r10_open_official" in r["by"]]
        print("  r10 first openings:", len(first), "distinct:", len(set(r["file"] for r in first)))
        # earliest opening per file overall
        earliest = {}
        for r in rows:
            earliest.setdefault(r["file"], r["time"])
        print("  distinct compare files:", len(earliest), "earliest", min(earliest.values()),
              "latest first-open", max(earliest.values()))
