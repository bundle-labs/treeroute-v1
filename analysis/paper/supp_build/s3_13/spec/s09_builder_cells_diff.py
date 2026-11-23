# s09_builder_cells_diff.py - version-2 maintenance of TABLE_SPEC.md: read-only comparison of the two
# version-1 builders' cells.json and tables.md (OUT\A, OUT\B), to see which gaps G1-G4 of the change order
# close. Prints only; writes nothing.  Run: py -3.9 -I -B s09_builder_cells_diff.py
import collections
import hashlib
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

OUT = "../"
for name in ("tables.md", "cells.json"):
    hs = []
    for x in ("A", "B"):
        with open(OUT + x + "/" + name, "rb") as fh:
            hs.append(hashlib.sha256(fh.read()).hexdigest())
    print(name, "A", hs[0][:12], "B", hs[1][:12], "equal" if hs[0] == hs[1] else "DIFFER")
with open(OUT + "reconcile/tables_agreed.md", "rb") as fh:
    print("tables_agreed.md", hashlib.sha256(fh.read()).hexdigest())

docs = []
for x in ("A", "B"):
    with open(OUT + x + "/cells.json", encoding="utf-8") as fh:
        docs.append(json.load(fh))
ea, eb = docs[0]["entries"], docs[1]["entries"]
print("entries A", len(ea), "B", len(eb))
diffs = collections.Counter()
examples = {}
for i, (a, b) in enumerate(zip(ea, eb)):
    for k in a:
        if a.get(k) != b.get(k):
            key = (a["table"], a["panel"], k, json.dumps(a.get(k), ensure_ascii=False)[:60],
                   json.dumps(b.get(k), ensure_ascii=False)[:60])
            diffs[key] += 1
            if key not in examples:
                examples[key] = (i, a["row"], a["column"], a["part"], b["part"], a["selector"], b["selector"])
for key, n in sorted(diffs.items()):
    print(n, "x", key)
    print("     e.g. entry", examples[key])

print()
print("== part names used by A per (table, panel, column-kind), with one selector")
seen = collections.OrderedDict()
for e in ea:
    col = e["column"]
    if e["table"] in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27") and e["panel"] in ("a", "b"):
        col = "<stat>"
    row = e["row"]
    if e["table"] in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27") and e["panel"] in ("a", "b"):
        row = "<pair>"
    if e["table"] in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27") and e["panel"] in ("d", "e", "g"):
        row = row.split("_")[0]
        col = "<model>"
    if e["table"] in ("S3.20",) and e["row"] != "note":
        row = "<p:model>"
    if e["table"] in ("9", "S3.19", "S3.22", "S3.28", "S3.29", "S3.30") or (e["table"] == "S3.21"):
        pass
    k = (e["table"], e["panel"], row if e["table"] not in ("9", "S3.19") else "<p>", col)
    seen.setdefault(k, collections.OrderedDict())
    seen[k].setdefault(e["part"], e["selector"])
for k, parts in seen.items():
    print(k, dict(parts))

print()
print("== A's S3.21 E3m entries and S3.22 coral own_history_per_rival entries")
for e in ea:
    if (e["table"] == "S3.21" and e["row"] == "E3m") or (
            e["table"] == "S3.22" and e["row"] == "own_history_per_rival" and e["column"] == "coral"):
        print(json.dumps(e, ensure_ascii=False))
