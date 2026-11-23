# r01: compare OUT\A\tables.md with OUT\B\tables.md byte for byte, and OUT\A\cells.json with
# OUT\B\cells.json entry by entry. Read-only; prints a summary. Paths are found from this file's place
# (OUT\reconcile\scripts\r01_compare_builders.py), so no full path is written here.
import sys, json, hashlib, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

ta, tb = OUT / "A" / "tables.md", OUT / "B" / "tables.md"
ca, cb = OUT / "A" / "cells.json", OUT / "B" / "cells.json"
ba, bb = ta.read_bytes(), tb.read_bytes()
print("tables.md A sha256", sha(ta), len(ba))
print("tables.md B sha256", sha(tb), len(bb))
print("tables.md byte-identical:", ba == bb)
if ba != bb:
    n = min(len(ba), len(bb))
    i = next((k for k in range(n) if ba[k] != bb[k]), n)
    print("first differing byte at", i)
print("cells.json A sha256", sha(ca), ca.stat().st_size)
print("cells.json B sha256", sha(cb), cb.stat().st_size)

da = json.loads(ca.read_text(encoding="utf-8"))
db = json.loads(cb.read_text(encoding="utf-8"))
print("top keys A", list(da.keys()), "B", list(db.keys()))
for k in ("tables_file", "spec"):
    print(k, repr(da.get(k)), repr(db.get(k)), da.get(k) == db.get(k))
ea, eb = da["entries"], db["entries"]
print("entries A", len(ea), "B", len(eb))

diffs = collections.Counter()
examples = collections.defaultdict(list)
keyorder = collections.Counter()
n_same = 0
for i, (x, y) in enumerate(zip(ea, eb)):
    if list(x.keys()) != list(y.keys()):
        keyorder[(tuple(x.keys()), tuple(y.keys()))] += 1
    if x == y:
        n_same += 1
        continue
    ks = tuple(k for k in sorted(set(x) | set(y)) if x.get(k) != y.get(k))
    sig = (ks, x.get("table"), x.get("panel"), x.get("row") if x.get("table") in ("S3.21",) else None)
    # group by differing keys, table, and the pair of values of those keys
    vals = tuple((k, json.dumps(x.get(k), ensure_ascii=False), json.dumps(y.get(k), ensure_ascii=False)) for k in ks)
    grp = (ks, x.get("table"), x.get("panel"))
    diffs[grp] += 1
    if len(examples[grp]) < 4:
        examples[grp].append((i, x, y, vals))
print("entries equal:", n_same, "of", min(len(ea), len(eb)))
print("key-order mismatches:", dict(keyorder))
for grp, c in sorted(diffs.items(), key=lambda t: (str(t[0][1]), str(t[0][2]))):
    print("== differing keys", grp[0], "table", grp[1], "panel", repr(grp[2]), "count", c)
    for i, x, y, vals in examples[grp]:
        print("   idx", i, "line", x.get("line"), "row", x.get("row"), "col", x.get("column"))
        for k, va, vb in vals:
            print("      ", k, "A:", va, "| B:", vb)

# Distinct value pairs per differing key, over all entries
pairs = collections.defaultdict(collections.Counter)
for x, y in zip(ea, eb):
    for k in sorted(set(x) | set(y)):
        if x.get(k) != y.get(k):
            if k in ("part",):
                pairs[k][(x.get("table"), x.get("panel"), x.get(k), y.get(k))] += 1
            else:
                pairs[k][(x.get("table"), x.get("panel"), json.dumps(x.get(k), ensure_ascii=False)[:160], json.dumps(y.get(k), ensure_ascii=False)[:160])] += 1
for k, cnt in pairs.items():
    print("### key", k, "distinct (table, panel, A, B) combos:", len(cnt))
    for comb, c in sorted(cnt.items(), key=lambda t: str(t[0])):
        print("   ", c, comb)
