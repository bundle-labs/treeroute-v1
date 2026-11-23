# s16_v2_number_tokens.py - version 3 of TABLE_SPEC.md (2026-11-17). Read-only check of the two corrections that the
# change order (OUT\_brief\fix_order_v3.md, V3-7) makes to CHANGES_v2.md: the line count of tables.md in versions 1
# and 2, and the number tokens that the version-2 changes added or removed in tables.md (version 1:
# OUT\reconcile\tables_agreed_v1.md; version 2: OUT\reconcile\tables_agreed.md), with the token regex of the second
# check (OUT\skeptic\k09_number_tokens.py). Each changed line is assigned to its version-2 change by the line list of
# CHANGES_v2.md. Prints only. Run from this folder: py -3.9 -I -B s16_v2_number_tokens.py
import collections
import difflib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lines(name):
    with open(os.path.join(OUT, "reconcile", name), "rb") as fh:
        raw = fh.read()
    return raw.count(b"\n"), raw.decode("utf-8").split("\n")[:-1]


n1, v1 = lines("tables_agreed_v1.md")
n2, v2 = lines("tables_agreed.md")
print("tables.md lines: version 1 {}, version 2 {}".format(n1, n2))
NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<]")
# version-2 line -> change (CHANGES_v2.md, "The lines that change"); the dropped version-1 row 65 is C4's
V2_CHANGE = {1: "C9", 5: "C1", 65: "C4", 66: "C4", 67: "C4", 121: "C2", 122: "C2", 144: "C6", 146: "C6", 155: "C5",
             171: "C8", 174: "C1", 251: "C7", 256: "C1", 342: "C7", 344: "C3", 348: "C1", 451: "C7", 457: "C1",
             543: "C7", 548: "C1", 661: "C7", 711: "C1", 784: "C4"}
add = collections.defaultdict(collections.Counter)
rem = collections.defaultdict(collections.Counter)
sm = difflib.SequenceMatcher(a=v1, b=v2, autojunk=False)
seen2 = []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    a = collections.Counter(t for x in v1[i1:i2] for t in NUM.findall(x))
    b = collections.Counter(t for x in v2[j1:j2] for t in NUM.findall(x))
    ids = sorted(set(V2_CHANGE.get(j + 1, "?") for j in range(j1, j2)) | ({"C4"} if i2 > i1 and j2 == j1 else set()))
    seen2 += [j + 1 for j in range(j1, j2)]
    key = "+".join(ids)
    add[key] += b - a
    rem[key] += a - b
    print("  {} v1 {}-{} -> v2 {}-{} ({}): added {} removed {}".format(tag, i1 + 1, i2, j1 + 1, j2, key,
                                                                     dict(b - a), dict(a - b)))
print("version-2 lines that differ:", seen2)
print("not in CHANGES_v2.md's line list:", [j for j in seen2 if j not in V2_CHANGE])
for key in sorted(add):
    print("  {:6s} tokens added {} removed {}".format(key, dict(add[key]), dict(rem[key])))
c1 = add.get("C1", collections.Counter())
c6 = add.get("C6", collections.Counter())
c9 = add.get("C9", collections.Counter())
print("C1: '-10' (Top-10 / top-10) {}, '-3' (Top-3) {}, '0' (above 0) {}".format(c1["-10"], c1["-3"], c1["0"]))
print("C6: '8' (E8, D8 of S3.21 note a) {}; C9: '2' (Version 2) {}".format(c6["8"], c9["2"]))
