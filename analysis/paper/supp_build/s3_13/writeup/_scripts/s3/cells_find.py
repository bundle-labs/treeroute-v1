"""Find cells.json entries of one table whose row, column, part or selector contains a text (read only).

Usage: py -3.9 -I -B cells_find.py <cells.json> <table> <text> [<line>]
With <line>, only entries printed on that line of tables_agreed.md.
"""
import json
import sys


def main():
    path, table, text = sys.argv[1], sys.argv[2], sys.argv[3].lower()
    line = int(sys.argv[4]) if len(sys.argv) > 4 else None
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    for e in d["entries"]:
        if e["table"] != table:
            continue
        if line is not None and e.get("line") != line:
            continue
        hay = " ".join(str(e.get(k, "")) for k in ("row", "column", "part", "selector", "panel")).lower()
        if text == "*" or text in hay:
            print("L%s | %s | %s | %s | %s | %s | printed=%r | %s :: %s | stored=%r" % (
                e.get("line"), e.get("panel"), e.get("row"), e.get("column"), e.get("part"),
                e.get("cell", "")[:40], e.get("printed"), e.get("source"), e.get("selector"), e.get("stored")))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
