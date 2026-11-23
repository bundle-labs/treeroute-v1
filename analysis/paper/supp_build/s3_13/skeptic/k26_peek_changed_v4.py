# Skeptic (version 4 check): print every line that differs between version 3 (tables_agreed_v3.md) and version 4
# (tables_agreed.md), both texts in full, plus the lines around them that give the table and column context.
# Read-only; prints only.
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
RC = os.path.join(OUT, "reconcile")


def lines(path):
    t = open(path, encoding="utf-8", newline="").read()
    assert t.endswith("\n")
    return t[:-1].split("\n")


v3 = lines(os.path.join(RC, "tables_agreed_v3.md"))
v4 = lines(os.path.join(RC, "tables_agreed.md"))
print("lines v3 %d, v4 %d" % (len(v3), len(v4)))
ch = [i + 1 for i in range(min(len(v3), len(v4))) if v3[i] != v4[i]]
print("changed lines (%d): %s" % (len(ch), ch))
for k in ch:
    print("=" * 30, "line", k)
    print("v3:", v3[k - 1])
    print("v4:", v4[k - 1])
ctx = sorted(set([k for k in ch] + [126, 127, 128, 129, 131, 132, 133, 137, 139, 140, 141, 142, 144, 145, 147, 148,
                                    149, 150, 151, 152, 153, 154, 156, 157, 52, 53, 54, 55, 57, 58, 59, 60, 61, 62, 63,
                                    64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 84, 85, 2, 3,
                                    4, 6, 7, 8, 18, 19, 20, 21, 23, 24, 119, 120, 121, 122, 123, 124, 125, 666, 667, 668,
                                    670, 671, 672]))
print()
print("#" * 30, "context of version 4")
for k in ctx:
    print("%4d: %s" % (k, v4[k - 1][:400]))
