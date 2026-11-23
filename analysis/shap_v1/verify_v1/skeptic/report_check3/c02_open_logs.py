"""Report check 3: the two open logs of the reconciler (entry counts, who read, time windows, runs, V or not).
Read-only. Run: py -3.9 -I -B c02_open_logs.py
"""
import collections
import json
import os

W = r"D:\treeroute\analysis\shap_v1\verify_v1\reconcile\work"
V = r"D:\treeroute\analysis\shap_v1\verify_v1"


def load(name):
    rows = []
    with open(os.path.join(W, name), encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                rows.append(json.loads(ln))
    return rows


def main():
    for name in ("opened_official.jsonl", "opened_other.jsonl"):
        rows = load(name)
        keys = collections.Counter(k for r in rows for k in r)
        print("==", name, "entries:", len(rows), "| fields:", dict(keys))
        # guess the field names
        tkey = next((k for k in ("time", "t", "opened_at", "at", "when", "ts") if k in keys), None)
        bkey = next((k for k in ("by", "script", "who") if k in keys), None)
        pkey = next((k for k in ("path", "file", "p") if k in keys), None)
        mkey = next((k for k in ("mode", "how", "kind", "what") if k in keys), None)
        print("   time field:", tkey, "| by field:", bkey, "| path field:", pkey, "| mode field:", mkey)
        print("   first entry:", json.dumps(rows[0])[:300])
        groups = collections.defaultdict(list)
        for r in rows:
            label = str(r.get(bkey))
            if mkey and r.get(mkey) is not None:
                label += " / " + str(r.get(mkey))
            groups[label].append(r)
        for g, rs in sorted(groups.items()):
            ts = sorted(str(r.get(tkey)) for r in rs)
            nfiles = len(set(str(r.get(pkey)) for r in rs))
            print("   %-40s %4d entries, %3d files, %s .. %s" % (g, len(rs), nfiles, ts[0], ts[-1]))
        # paths inside V?
        inside = [r for r in rows if str(r.get(pkey, "")).lower().startswith(V.lower())]
        print("   entries with a path inside V:", len(inside))
        print("   distinct files:", len(set(str(r.get(pkey)) for r in rows)))
        # other fields that may mark a run
        for k in keys:
            if k not in (tkey, bkey, pkey):
                vals = collections.Counter(str(r.get(k)) for r in rows)
                if len(vals) <= 12:
                    print("   field %s values: %s" % (k, dict(vals)))
                else:
                    print("   field %s: %d distinct values" % (k, len(vals)))
        yield_rows = rows
        if name == "opened_official.jsonl":
            official = yield_rows
        else:
            other = yield_rows
    # runs of reconcile.py: cluster the entries by time gaps (> 20 s starts a new run)
    import datetime

    def parse(t):
        t = str(t)
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(t, fmt)
            except ValueError:
                pass
        return None

    for name, rows in (("opened_official.jsonl", official), ("opened_other.jsonl", other)):
        keys = set(k for r in rows for k in r)
        tkey = next((k for k in ("time", "t", "opened_at", "at", "when", "ts") if k in keys), None)
        bkey = next((k for k in ("by", "script", "who") if k in keys), None)
        mkey = next((k for k in ("mode", "how", "kind", "what") if k in keys), None)
        for who in sorted(set(str(r.get(bkey)) for r in rows)):
            rs = [r for r in rows if str(r.get(bkey)) == who]
            ts = sorted(parse(r.get(tkey)) for r in rs)
            if any(t is None for t in ts):
                print(name, who, ": unparsed times")
                continue
            runs = []
            for t in ts:
                if not runs or (t - runs[-1][-1]).total_seconds() > 20:
                    runs.append([t])
                else:
                    runs[-1].append(t)
            print("%s by %s: %d entries in %d clusters (gap > 20 s): %s" % (
                name, who, len(rs), len(runs),
                "; ".join("%s-%s (%d)" % (r[0].strftime("%H:%M:%S"), r[-1].strftime("%H:%M:%S"), len(r)) for r in runs)))


if __name__ == "__main__":
    main()
