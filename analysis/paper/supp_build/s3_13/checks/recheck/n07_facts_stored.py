# n07: every "printed (stored ...)" pair in facts A9-A28 of the staged PAPER_FACTS.md: format the stored double once and
# compare with the printed value; check that the stored double is one of cells.json's stored values (exact repr), and
# flag numbers whose three-decimal printout, re-rounded, would print differently (rounding traps). Read-only.
import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
OUT = os.path.join(ROOT, r"paper\supp_build\s3_13")
FACTS = os.path.join(OUT, r"stage\paper\PAPER_FACTS.md")
CELLS = os.path.join(OUT, r"reconcile\cells.json")

facts = open(FACTS, "rb").read().decode("utf-8")
cells = json.loads(open(CELLS, "rb").read().decode("utf-8"))["entries"]
stored_reprs = {}
for e in cells:
    for v in e["stored"]:
        if isinstance(v, float):
            stored_reprs.setdefault(repr(v), []).append((e["table"], e["panel"], e["line"], e["row"], e["column"], e["part"], e["printed"]))

fact = {}
for m in re.finditer(r"^- \*\*(A\d+) \(final, post hoc \(Part 628\)\)\.(.*)$", facts, flags=re.M):
    fact[m.group(1)] = m.group(2)
print("facts found:", sorted(fact, key=lambda x: int(x[1:])))


def f2(x):
    s = format(x, ".2f")
    if s.startswith("-"):
        s = "\u2212" + s[1:]
    if s == "\u22120.00":
        s = "0.00"
    return s


def fp1(x):
    return format(x * 100, ".1f") + "%"


def fmt_like(printed, x):
    return fp1(x) if printed.endswith("%") else f2(x)


def trap(printed, x):
    # what a re-round of a three-decimal printout would give (half-up and half-even)
    if printed.endswith("%"):
        three = Decimal(format(x * 100, ".2f"))  # a two-decimal percent printout
        r1 = str(three.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) + "%"
        r2 = str(three.quantize(Decimal("0.1"), rounding=ROUND_HALF_EVEN)) + "%"
    else:
        three = Decimal(format(x, ".3f"))
        r1 = str(three.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)).replace("-", "\u2212")
        r2 = str(three.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)).replace("-", "\u2212")
    return r1, r2


NUM = r"[\u2212-]?\d+(?:\.\d+)?%?"
SNUM = r"-?\d+(?:\.\d+)?(?:e-?\d+)?"
pat_ci = re.compile(r"(%s) \[(%s), (%s)\] \(stored (%s) \[(%s), (%s)\]" % (NUM, NUM, NUM, SNUM, SNUM, SNUM))
pat_one = re.compile(r"(%s) \(stored (%s)\)" % (NUM, SNUM))
n = 0
bad = 0
traps = 0
for fid in sorted(fact, key=lambda x: int(x[1:])):
    txt = fact[fid]
    pairs = []
    for m in pat_ci.finditer(txt):
        for i in range(3):
            pairs.append((m.group(1 + i), m.group(4 + i)))
    for m in pat_one.finditer(txt):
        pairs.append((m.group(1), m.group(2)))
    for printed, st in pairs:
        n += 1
        x = float(st)
        exp = fmt_like(printed, x)
        incells = repr(x) in stored_reprs or st in ("0.0",)
        ok = exp == printed
        r1, r2 = trap(printed, x)
        t = (r1 != exp or r2 != exp)
        if t:
            traps += 1
        flag = "" if ok else "  <== MISMATCH"
        if not ok:
            bad += 1
        print("%s printed=%s stored=%s -> once=%s %s cells=%s%s%s" % (
            fid, printed, st, exp, "ok" if ok else "BAD", "yes" if incells else "NO",
            ("  [trap: 3-dec re-round gives %s/%s]" % (r1, r2)) if t else "", flag))
        if repr(x) != st and st != "0.0":
            print("   note: stored text %s is not repr %s" % (st, repr(x)))
print("pairs:", n, "mismatches:", bad, "traps:", traps)

# the "shares 44.5%, 32.1% and 54.2%; stored a, b and c" form in A22
m = re.search(r"shares ([\d.]+%), ([\d.]+%) and ([\d.]+%); stored (" + SNUM + "), (" + SNUM + ") and (" + SNUM + r")\)", fact["A22"])
if m:
    for i in range(3):
        p, s = m.group(1 + i), m.group(4 + i)
        print("A22 top share", p, s, fp1(float(s)), "ok" if fp1(float(s)) == p else "BAD", "cells" if repr(float(s)) in stored_reprs else "NOT IN CELLS")
# A12 scientific numbers
for p, s in re.findall(r"(\d\.\d × 10⁻[⁰¹²³⁴⁵⁶⁷⁸⁹]+), stored (" + SNUM + r")\)", fact["A12"]):
    x = float(s)
    mant, ex = format(x, ".1e").split("e")
    sup = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
    exp = "%s × 10%s" % (mant, str(int(ex)).translate(sup))
    print("A12 sci", p, s, exp, "ok" if exp == p else "BAD", "cells" if repr(x) in stored_reprs else "NOT IN CELLS")
