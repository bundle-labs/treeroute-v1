# -*- coding: utf-8 -*-
# Exploration only (prints to console; writes nothing): every changed line between the spec's version 1
# (OUT\spec\TABLE_SPEC_v1.md) and version 2 (OUT\spec\TABLE_SPEC.md), with line numbers of both.
# Run as: py -3.9 -I -B <this script>
import sys
import os
import difflib

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
with open(os.path.join(OUT, "spec", "TABLE_SPEC_v1.md"), "r", encoding="utf-8") as f:
    a = f.read().split("\n")
with open(os.path.join(OUT, "spec", "TABLE_SPEC.md"), "r", encoding="utf-8") as f:
    b = f.read().split("\n")
print("v1 lines (split on LF): %d; v2: %d" % (len(a), len(b)))
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n += 1
    print("=== %s v1 %d-%d -> v2 %d-%d" % (tag, i1 + 1, i2, j1 + 1, j2))
    for i in range(i1, i2):
        print("  - v1 %d: %s" % (i + 1, a[i]))
    for j in range(j1, j2):
        print("  + v2 %d: %s" % (j + 1, b[j]))
print("hunks: %d" % n)
