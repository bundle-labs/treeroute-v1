"""Count reconcile.py's passes over the compare files in V\\reconcile\\work\\opened_official.jsonl.

Usage: py -3.12 -X utf8 -I -B count_passes.py <opened_official.jsonl>
Prints, per second, the number of plain opens and byte reads by each script, then the passes: a pass is a run of
consecutive opens by reconcile.py; it is complete when it covers all 50 compare files (10 per problem).
"""
import collections
import json
import sys


def main():
    rows = []
    with open(sys.argv[1], encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print("entries:", len(rows), "| keys of the first:", sorted(rows[0].keys()))
    by = collections.Counter(r.get("by") for r in rows)
    print("by script:", dict(by))
    per_sec = collections.OrderedDict()
    for r in rows:
        t = str(r.get("time") or r.get("t") or r.get("ts") or r.get("local") or "")[:19]
        k = (t, r.get("by"), r.get("how") or r.get("mode") or r.get("kind") or "")
        per_sec[k] = per_sec.get(k, 0) + 1
    print("per second (time, by, how): count")
    for k, v in per_sec.items():
        print("  ", k, v)
    # passes: reconcile.py's plain opens (the 'by' field is exactly 'reconcile.py'; byte reads carry another label),
    # a new pass starting whenever more than 5 seconds pass between two opens
    import datetime
    passes = []
    cur = []
    last = None
    for r in rows:
        if r.get("by") != "reconcile.py":
            continue
        t = datetime.datetime.fromisoformat(str(r.get("time"))[:19])
        if last is not None and (t - last).total_seconds() > 5:
            passes.append(cur)
            cur = []
        cur.append(r)
        last = t
    if cur:
        passes.append(cur)
    print("passes (a gap of more than 5 s starts a new pass):")
    total = 0
    for p in passes:
        probs = sorted(set(str(x.get("path") or x.get("file")).split("\\out\\")[-1].split("\\")[0] for x in p))
        t0 = str(p[0].get("time") or p[0].get("t") or "")[:19]
        print("   start %s  opens %d  problems %s" % (t0, len(p), probs))
        total += len(p)
    print("plain opens by reconcile.py:", total)


if __name__ == "__main__":
    main()
