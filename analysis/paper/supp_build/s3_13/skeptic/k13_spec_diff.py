# Skeptic (version 2 check, item 1): every changed line of the spec, version 1 -> version 2, against the change list of
# CHANGES_v2.md and spec section 9. Read-only; prints only.
import difflib, os, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
a = open(os.path.join(OUT, "spec", "TABLE_SPEC_v1.md"), encoding="utf-8").read().split("\n")
b = open(os.path.join(OUT, "spec", "TABLE_SPEC.md"), encoding="utf-8").read().split("\n")
listed = {"C1": [416, (446, 452), 752, (760, 763), (765, 769), 980, (1013, 1016), (1191, 1193)],
          "C2": [(637, 638), 337], "C3": [883, 284, (1185, 1186)], "C4": [526, 532, 1090], "C5": [717],
          "C6": [681, 686], "C7": [876], "C8": [736], "C9": [309], "G1": [1120, (912, 913)],
          "G2": [(100, 105), (1046, 1047), 1056, (1140, 1141)], "G3": [(691, 692)], "G4": [727],
          "S9": [15, (1254, 1301)]}


def owner(n):
    for k, v in listed.items():
        for r in v:
            lo, hi = (r, r) if isinstance(r, int) else r
            if lo <= n <= hi:
                return k
    return None


sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
unlisted, nchg1, nchg2 = [], 0, 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    nchg1 += i2 - i1
    nchg2 += j2 - j1
    owners = sorted(set(filter(None, (owner(n) for n in range(j1 + 1, j2 + 1)))))
    print("%-7s v1 %4d-%-4d -> v2 %4d-%-4d %s" % (tag, i1 + 1, i2, j1 + 1, j2, owners))
    for n in range(j1 + 1, j2 + 1):
        if owner(n) is None:
            unlisted.append((n, b[n - 1][:110]))
    if tag == "delete":
        print("      deleted v1 lines:", [x[:80] for x in a[i1:i2]])
print("changed lines: v1 %d, v2 %d; changed v2 lines outside the listed ranges: %d" % (nchg1, nchg2, len(unlisted)))
for u in unlisted:
    print("   ", u)
fa = sum(1 for x in a if x.startswith("```"))
fb = sum(1 for x in b if x.startswith("```"))
print("fence lines: v1 %d, v2 %d (blocks %d / %d)" % (fa, fb, fa // 2, fb // 2))
