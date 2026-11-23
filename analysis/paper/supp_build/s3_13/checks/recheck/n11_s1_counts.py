# n11: count S1's item rows by section (staged and live), print S1.10's table, and show fact M14b's date words.
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
for name, p in (("live", os.path.join(ROOT, r"paper\draft\S1_disclosures.md")), ("staged", os.path.join(OUT, r"stage\paper\draft\S1_disclosures.md"))):
    t = open(p, "rb").read().decode("utf-8").replace("\r\n", "\n")
    lines = t.split("\n")
    sec = None
    counts = {}
    ids = {}
    for l in lines:
        m = re.match(r"^## (S1\.\d+) (.*)$", l)
        if m:
            sec = m.group(1) + " " + m.group(2)
            continue
        m = re.match(r"^\| ([A-Z]{2,3}\d+[a-z]?) \|", l)
        if m and sec:
            counts[sec] = counts.get(sec, 0) + 1
            ids.setdefault(sec, []).append(m.group(1))
    print(name, counts, "total", sum(v for k, v in counts.items() if not k.startswith("S1.10")))
    for k, v in ids.items():
        if k.startswith("S1.7"):
            print("  S1.7 ids:", v)
    i = [j for j, l in enumerate(lines) if l.startswith("## S1.10")][0]
    print("  " + "\n  ".join(lines[i:i + 16]))
facts = open(os.path.join(OUT, r"stage\paper\PAPER_FACTS.md"), "rb").read().decode("utf-8")
m = re.search(r"^- \*\*M14b.*$", facts, flags=re.M)
s = m.group(0)
print("\nM14b length", len(s))
for mm in re.finditer(r"2026-11-\d\d", s):
    print("  ", s[max(0, mm.start() - 120):mm.end() + 60].replace("\n", " "))
