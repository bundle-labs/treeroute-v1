"""Read-only: summarise V\\reconcile\\work\\opened_official.jsonl (and opened_other.jsonl) by script and time."""
import collections
import json

P = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\opened_official.jsonl"
rows = [json.loads(l) for l in open(P, "r", encoding="utf-8") if l.strip()]
print("n_rows", len(rows))
print("fields", sorted(set().union(*[set(r.keys()) for r in rows])))
print("first row", json.dumps(rows[0])[:400])
print("last row", json.dumps(rows[-1])[:400])


def g(r, *names):
    for n in names:
        if n in r:
            return r[n]
    return None


by_script = collections.OrderedDict()
for r in rows:
    s = g(r, "script", "by", "who", "caller")
    by_script.setdefault(s, []).append(r)
for s, rs in by_script.items():
    times = [g(x, "time", "t", "when", "local_time") for x in rs]
    kinds = collections.Counter(g(x, "mode", "kind", "how", "action") for x in rs)
    print("script", s, "n", len(rs), "first", times[0], "last", times[-1], "kinds", dict(kinds))

# first openings: first time each path appears
seen = collections.OrderedDict()
for r in rows:
    p = g(r, "path", "file")
    if p not in seen:
        seen[p] = r
print("distinct paths", len(seen))
for i, (p, r) in enumerate(seen.items()):
    short = p.split("shap_v1\\")[-1] if isinstance(p, str) else p
    print("%2d" % (i + 1), g(r, "time", "t", "when", "local_time"), g(r, "script", "by", "who", "caller"), short,
          g(r, "mode", "kind", "how", "action"))

# runs of reconcile.py: group by run (gap > 60 s) and count opens and byte reads
import datetime as dt


def ts(x):
    try:
        return dt.datetime.fromisoformat(x)
    except Exception:
        return None


rec = [r for r in rows if isinstance(g(r, "script", "by", "who", "caller"), str) and "reconcile.py" in g(r, "script", "by", "who", "caller")]
runs = []
for r in rec:
    t = ts(g(r, "time", "t", "when", "local_time"))
    if not runs or (t - runs[-1][-1][0]).total_seconds() > 30:
        runs.append([])
    runs[-1].append((t, r))
print("reconcile.py runs", len(runs))
tot = collections.Counter()
for run in runs:
    c = collections.Counter(g(r, "mode", "kind", "how", "action") for _, r in run)
    tot.update(c)
    print("  run", run[0][0].isoformat(), "to", run[-1][0].isoformat(), "n", len(run), dict(c))
print("  total", dict(tot), "n", sum(tot.values()))

# AW4_main_row reads by any non-r10 script
for r in rows:
    p = g(r, "path", "file") or ""
    s = g(r, "script", "by", "who", "caller") or ""
    if "AW4_main_row.json" in p and "r10_" not in s and "reconcile.py" not in s:
        print("AW4_main_row read", g(r, "time", "t", "when", "local_time"), s, p.split("shap_v1\\")[-1])

P2 = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work\opened_other.jsonl"
rows2 = [json.loads(l) for l in open(P2, "r", encoding="utf-8") if l.strip()]
print("other n_rows", len(rows2))
paths2 = collections.Counter()
for r in rows2:
    p = g(r, "path", "file") or ""
    # never print anything under bardl_fix; just flag it
    if "bardl_fix" in p.lower():
        print("!! other log names bardl_fix")
        continue
    if "smoke" in p.lower():
        print("other log names smoke path (not printed)")
    key = p.split("shap_v1\\")[-1] if "shap_v1\\" in p else p.split("\\")[0:3]
    paths2[str(key)[:110]] += 1
for k, v in sorted(paths2.items()):
    print("  other", v, k)
times2 = [g(r, "time", "t", "when", "local_time") for r in rows2]
print("other first", times2[0], "last", times2[-1])
