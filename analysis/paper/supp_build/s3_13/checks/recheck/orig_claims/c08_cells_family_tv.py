"""Where do the feature-level family-share distances and the B1 family-share distances come from? (read only)

Loads OUT/reconcile/cells.json, prints its top-level structure and one entry's keys, then every entry whose
column or selector names the family-share distance (tvd_family) for the feature level of the main pairs and
for B1, with its table, source and selector (first few per table). Also tallies the sources per table of
the sign-agreement intervals. No file outside OUT/reconcile is read.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
CELLS = os.path.join(OUT, "reconcile", "cells.json")


def entries(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("cells", "entries", "items"):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
    return []


def main():
    with open(CELLS, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        print("top-level keys:", list(data.keys())[:20])
    ents = entries(data)
    print("entries:", len(ents))
    if not ents:
        return 1
    print("first entry keys:", sorted(ents[0].keys()))
    print("first entry:", json.dumps(ents[0])[:600])
    shown = collections.Counter()
    for e in ents:
        blob = json.dumps(e)
        if "family" in blob.lower() and ("tvd" in blob.lower() or "distance" in blob.lower()):
            t = str(e.get("table"))
            if shown[t] < 3:
                print("  table %s | %s" % (t, json.dumps(e)[:500]))
            shown[t] += 1
    print("family-distance entries per table:", dict(shown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
