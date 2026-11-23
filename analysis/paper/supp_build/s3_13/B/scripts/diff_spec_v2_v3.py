# Check only (builder B): the lines of OUT\spec\TABLE_SPEC.md (version 3) that differ from OUT\spec\TABLE_SPEC_v2.md,
# grouped as difflib's opcodes, so that every spec change can be matched to a change of build_tables.py or to a text
# that the build reads from the spec. Writes nothing.
# Run as: py -3.9 -I -B <this file>
import sys
import os
import difflib
import hashlib

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "spec")


def rd(name):
    with open(os.path.join(SPEC_DIR, name), "rb") as f:
        b = f.read()
    print("%-16s sha256 %s" % (name, hashlib.sha256(b).hexdigest()))
    return b.decode("utf-8").split("\n")


V2, V3 = rd("TABLE_SPEC_v2.md"), rd("TABLE_SPEC.md")
print("lines: v2 %d, v3 %d" % (len(V2) - 1, len(V3) - 1))
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, V2, V3, autojunk=False).get_opcodes():
    if tag == "equal":
        continue
    print("\n== %s v2 %s -> v3 %s" % (tag, "%d-%d" % (i1 + 1, i2) if i2 > i1 else "(none)",
                                     "%d-%d" % (j1 + 1, j2) if j2 > j1 else "(none)"))
    for k in range(i1, i2):
        print("  - %4d: %s" % (k + 1, V2[k][:150] + (" ..." if len(V2[k]) > 150 else "")))
    for k in range(j1, j2):
        print("  + %4d: %s" % (k + 1, V3[k][:150] + (" ..." if len(V3[k]) > 150 else "")))
