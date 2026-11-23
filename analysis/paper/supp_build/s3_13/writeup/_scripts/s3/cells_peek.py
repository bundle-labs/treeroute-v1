"""Print cells.json entries for chosen tables (read only).

Usage: py -3.9 -I -B cells_peek.py <cells.json> <table> [<table> ...]
Prints line, table, panel, row, column, part, printed, source, selector and stored for each entry.
"""
import json
import sys


def main():
    path = sys.argv[1]
    want = set(sys.argv[2:])
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    print("keys:", sorted(d.keys()))
    ents = d["entries"]
    print("entries:", len(ents))
    tables = {}
    for e in ents:
        tables[e["table"]] = tables.get(e["table"], 0) + 1
    print("per table:", tables)
    for e in ents:
        if e["table"] in want:
            print("L%s | %s | %s | %s | %s | %s | printed=%r | %s :: %s | stored=%r" % (
                e.get("line"), e.get("table"), e.get("panel"), e.get("row"), e.get("column"),
                e.get("part"), e.get("printed"), e.get("source"), e.get("selector"), e.get("stored")))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
