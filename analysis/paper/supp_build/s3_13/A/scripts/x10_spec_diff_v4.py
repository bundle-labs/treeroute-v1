# -*- coding: utf-8 -*-
# Exploration only (prints to console; writes nothing): every changed line between the spec's version 3
# (OUT\spec\TABLE_SPEC_v3.md) and version 4 (OUT\spec\TABLE_SPEC.md), with line numbers of both, and the SHA-256
# and line count of each file.
# Run as: py -3.9 -I -B <this script>
import sys
import os
import hashlib
import difflib

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
raw = {}
for n in ("TABLE_SPEC_v3.md", "TABLE_SPEC.md"):
    with open(os.path.join(OUT, "spec", n), "rb") as f:
        raw[n] = f.read()
    print("%s  %d bytes  %d LF  CR:%s BOM:%s  %s" % (hashlib.sha256(raw[n]).hexdigest(), len(raw[n]),
                                                     raw[n].count(b"\n"), b"\r" in raw[n],
                                                     raw[n].startswith(b"\xef\xbb\xbf"), n))
a = raw["TABLE_SPEC_v3.md"].decode("utf-8").split("\n")
b = raw["TABLE_SPEC.md"].decode("utf-8").split("\n")
print("v3 lines (split on LF): %d; v4: %d" % (len(a), len(b)))
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
n = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    n += 1
    print("=== %s v3 %d-%d -> v4 %d-%d" % (tag, i1 + 1, i2, j1 + 1, j2))
    if j2 - j1 > 12 and tag == "insert":
        print("  (%d inserted lines, v4 %d-%d; first: %s)" % (j2 - j1, j1 + 1, j2, b[j1][:100]))
        continue
    for i in range(i1, i2):
        print("  - v3 %d: %s" % (i + 1, a[i]))
    for j in range(j1, j2):
        print("  + v4 %d: %s" % (j + 1, b[j]))
print("hunks: %d" % n)
