# r07_part628_status.py - lead item 4 / claims C13: does S3.0's facts comment (staged S3_posthoc.md) quote the status
# words of Part 628's heading in the staged PENDING_PARTS.md exactly, and name its addendum's date? Read-only. The
# heading line is printed only if it holds no id-shaped or path-shaped string.
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.normpath(os.path.join(HERE, "..", "..", "stage"))
s3 = open(os.path.join(ST, "paper", "draft", "S3_posthoc.md"), "rb").read().decode("utf-8").split("\n")
pp = open(os.path.join(ST, "engine", "PENDING_PARTS.md"), "rb").read().decode("utf-8").split("\n")
heads = [(i + 1, l) for i, l in enumerate(pp) if re.match(r"^#+ .*\b628\b", l)]
print("Part 628 heading lines:", [i for i, _ in heads])
bad = re.compile(r"(?i)wf_[0-9a-f]{6}|[A-Za-z]:[\\/]+users|[A-Za-z]--users-|[0-9a-f]{8}-[0-9a-f]{4}-|@")
for i, l in heads:
    print("  line %d (%d chars)%s" % (i, len(l), "" if bad.search(l) else ": " + l))
c = s3[36]
m = re.search(r'628: 2026-11-12, "([^"]+)", with its dated addendum of (\d{4}-\d\d-\d\d)\)', c)
print("S3.0 comment quote found:", bool(m))
if m and heads:
    q, d = m.group(1), m.group(2)
    h = heads[0][1]
    print("  quote occurs verbatim in the heading:", q in h)
    print("  heading's parenthetical equals the quote:", ("(" + q + ")") in h)
    add = [(i + 1, l[:120]) for i, l in enumerate(pp) if d in l and re.search(r"(?i)addendum", l)]
    print("  addendum lines with %s: %s" % (d, [a for a, _ in add]))
    for a, t in add:
        print("   ", a, t if not bad.search(t) else "(not printed)")
