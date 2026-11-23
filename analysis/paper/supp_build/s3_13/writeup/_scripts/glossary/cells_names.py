"""List the distinct column names and selector stems in cells.json (read only).

Usage: py -3.9 -I -B cells_names.py <cells.json>
Prints, per source file name, the distinct selectors with digits and bracketed
indices collapsed, and the distinct 'column' values, so that the code names of
each statistic can be read without opening any analysis script.
"""
import json
import re
import sys
from collections import defaultdict


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    entries = data["entries"]
    by_src = defaultdict(set)
    cols = defaultdict(int)
    for e in entries:
        src = re.split(r"[\\/]", e.get("source", ""))[-1]
        sel = e.get("selector", "")
        sel = re.sub(r"\[\d+\]", "[i]", sel)
        sel = re.sub(r"(problems|b1)\.(pm25|ndvi|fire|defo|coral)", r"\1.<p>", sel)
        by_src[src].add(sel)
        cols[e.get("column", "")] += 1
    print("entries:", len(entries))
    for src in sorted(by_src):
        print("==", src, len(by_src[src]))
        for s in sorted(by_src[src])[:80]:
            print("   ", s)
    print("== columns")
    for c, n in sorted(cols.items()):
        print("   %s %d" % (c, n))


if __name__ == "__main__":
    main()
