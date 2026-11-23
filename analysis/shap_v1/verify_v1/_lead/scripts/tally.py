"""Lead's tallies for the round-14 report addendum.

Usage: py -3.12 -X utf8 -I tally.py <mismatches.json> <A results.json> <B results.json> <out json>
1. Per mismatch group: the counts of each pair status (AB, AO, BO, AOd, BOd) over its keys.
2. Every results.json entry whose key path contains 'test_set' in A and in B (records of what was read).
"""
import collections
import json
import sys


def walk(x, path, out):
    if isinstance(x, dict):
        for k, v in x.items():
            p = path + "/" + str(k) if path else str(k)
            if "test_set" in str(k):
                out[p] = v
            walk(v, p, out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk(v, path + "[%d]" % i, out)


def short(v, n=400):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 3] + "..."


def main():
    mm, pa, pb, outp = sys.argv[1:5]
    with open(mm, encoding="utf-8") as f:
        d = json.load(f)
    cols = d["columns"]
    i_key, i_grp, i_sec, i_st = (cols.index(c) for c in ("key", "group", "secondary_groups", "status"))
    tallies = collections.OrderedDict()
    sec_count = collections.Counter()
    for g in d["groups"]:
        tallies[g["group"]] = collections.OrderedDict(n=0, declared=g.get("n_keys"), kind=g.get("kind"),
                                                      affects=g.get("affects_reported_numbers"))
    for row in d["keys"]:
        grp = row[i_grp]
        t = tallies.setdefault(grp, collections.OrderedDict(n=0, declared=None, kind=None, affects=None))
        t["n"] += 1
        for part in str(row[i_st]).split():
            if "=" in part:
                k, v = part.split("=", 1)
                t.setdefault(k, collections.Counter())[v] += 1
        for s in row[i_sec] or []:
            sec_count[s] += 1
    print("group | kind | affects | n (declared) | AB | AO | BO | AOd | BOd")
    for grp, t in tallies.items():
        def fmt(k):
            c = t.get(k)
            return ", ".join("%s %d" % kv for kv in sorted(c.items())) if c else "-"
        print("%s | %s | %s | %d (%s) | %s | %s | %s | %s | %s" % (grp, t["kind"], t["affects"], t["n"],
                                                                    t["declared"], fmt("AB"), fmt("AO"), fmt("BO"),
                                                                    fmt("AOd"), fmt("BOd")))
    print("secondary groups:", dict(sec_count))
    kw = d.get("keys_without_a_number_anywhere") or {}
    print("keys_without_a_number_anywhere:", {k: (len(v) if hasattr(v, "__len__") else v) for k, v in kw.items()})
    res = {"tallies": {g: {k: (dict(v) if isinstance(v, collections.Counter) else v) for k, v in t.items()}
                       for g, t in tallies.items()},
           "secondary_groups": dict(sec_count)}
    for name, p in (("A", pa), ("B", pb)):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        found = collections.OrderedDict()
        walk(r, "", found)
        res["test_set_" + name] = found
        print()
        print("=== %s: %d entries with 'test_set' in the key ===" % (name, len(found)))
        for k, v in found.items():
            print(" ", k, "=", short(v))
    with open(outp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("wrote", outp)


if __name__ == "__main__":
    main()
