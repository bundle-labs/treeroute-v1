"""Sources of the feature-level family-share distance cells (panel b) and of Table S3.28's rows (read only).

From OUT/reconcile/cells.json: the first entries of S3.23 panel b with column tvd_family, and, for Table S3.28,
every distinct (panel, row, column) with its source and selector of the value part. No other file is read.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
CELLS = os.path.join(OUT, "reconcile", "cells.json")


def main():
    with open(CELLS, "r", encoding="utf-8") as fh:
        ents = json.load(fh)["entries"]
    n = 0
    for e in ents:
        if e["table"] == "S3.23" and e["panel"] == "b" and e["column"] == "tvd_family" and e["part"] == "value":
            print("S3.23 b", e["row"], "|", e["source"], "|", e["selector"], "| printed", e["printed"])
            n += 1
            if n >= 3:
                break
    seen = set()
    for e in ents:
        if e["table"] == "S3.28" and e["part"] in ("value", ""):
            key = (e["panel"], e["row"], e["column"])
            if key in seen:
                continue
            seen.add(key)
            if "fam" in e["row"].lower() or "fam" in e["column"].lower() or e["row"].startswith("tvd"):
                print("S3.28", e["panel"], e["row"], e["column"], "|", e["source"], "|", e["selector"], "| printed", e["printed"])
    rows28 = sorted({(e["panel"], e["row"]) for e in ents if e["table"] == "S3.28"})
    print("S3.28 rows:", rows28)
    return 0


if __name__ == "__main__":
    sys.exit(main())
