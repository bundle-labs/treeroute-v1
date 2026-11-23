"""Read-only: list the cells.json entries of main-text Table 9 (and the table names cells.json uses).

Run: py -3.9 -I -B cells_table9.py
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.dirname(STAGE)
CELLS = os.path.join(OUT, "reconcile", "cells.json")

sys.stdout.reconfigure(encoding="utf-8")
with open(CELLS, encoding="utf-8") as fh:
    d = json.load(fh)
print("top-level keys:", sorted(d.keys()))
for k in sorted(d.keys()):
    if k != "entries":
        v = d[k]
        print("  %s: %s" % (k, json.dumps(v, ensure_ascii=False)[:600]))
entries = d["entries"]
print("entries:", len(entries))
tables = collections.Counter(e["table"] for e in entries)
print("tables:", dict(sorted(tables.items())))
print("entry keys:", sorted({k for e in entries for k in e}))
t9 = [e for e in entries if str(e["table"]) in ("9", "Table 9", "T9", "table_9", "main")]
print("Table 9 entries:", len(t9))
for e in t9:
    print(json.dumps(e, ensure_ascii=False))
