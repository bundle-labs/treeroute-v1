"""Count the register rows of the staged S1 by section and compare with its S1.10 count table (read only).

A register row is a table line whose first cell is an item ID (letters followed by digits, such as PH22).
Prints the rows per '## S1.x' section, the S1.10 table as written, and whether PH1..PH30 run in order.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
S1 = os.path.join(OUT, "stage", "paper", "draft", "S1_disclosures.md")

ID_RE = re.compile(r"^\| ([A-Z]{2,3}\d+[a-z]?) \|")


def main():
    with open(S1, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    section = None
    counts = {}
    order = {}
    for ln in lines:
        m = re.match(r"^## (S1\.\d+)\b(.*)$", ln)
        if m:
            section = m.group(1) + m.group(2)
            continue
        m = ID_RE.match(ln)
        if m and section:
            counts.setdefault(section, 0)
            counts[section] += 1
            order.setdefault(section, []).append(m.group(1))
    total = 0
    for s, n in counts.items():
        total += n
        print("%-70s %3d  first %s last %s" % (s[:70], n, order[s][0], order[s][-1]))
    print("total rows:", total)
    ph = [i for s in order for i in order[s] if i.startswith("PH")]
    print("PH ids in order 1..%d:" % len(ph), ph == ["PH%d" % k for k in range(1, len(ph) + 1)])
    # the S1.10 table
    inside = False
    for ln in lines:
        if ln.startswith("## S1.10"):
            inside = True
            print(ln)
            continue
        if inside and ln.startswith("## "):
            break
        if inside and ln.startswith("|"):
            print("   ", ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
