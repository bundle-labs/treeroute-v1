# Skeptic (version 2 check, item 3): every number token of version 2 against version 1, written independently of the
# reconciler's scripts. Read-only; prints only.
#  a) line alignment (difflib) and, per changed line, the number tokens and number words added or removed;
#  b) each added / removed token must lie inside a text that the change order quotes (its code spans, wrapped lines
#     joined) or in the dropped S3.18 row;
#  c) every table cell of version 2 that holds a digit, matched to version 1 by (table, panel, row key, column header),
#     must be byte-equal;
#  d) cells.json of version 2 against both builders' version-1 cells.json, entry by entry.
import difflib, json, os, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
v1 = open(os.path.join(OUT, "reconcile", "tables_agreed_v1.md"), encoding="utf-8").read().split("\n")[:-1]
v2 = open(os.path.join(OUT, "reconcile", "tables_agreed.md"), encoding="utf-8").read().split("\n")[:-1]
print("lines v1", len(v1), "v2", len(v2))

NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<]")
WORD = re.compile(r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|hundred|thousand|"
                  r"half|once|twice|both|single|first|second|third|fourth|fifth|last|every|all|none|only|no)\b", re.I)


def toks(s):
    return NUM.findall(s)


def words(s):
    return [w.lower() for w in WORD.findall(s)]


# the change order's quoted texts (code spans), wrapped lines joined with one space
order = open(os.path.join(OUT, "_brief", "fix_order_v2.md"), encoding="utf-8").read().split("\n")
joined, cur = [], None
for ln in order:
    if ln.startswith("- "):
        if cur is not None:
            joined.append(cur)
        cur = ln[2:]
    elif ln.startswith("  ") and cur is not None:
        cur += " " + ln[2:]
    else:
        if cur is not None:
            joined.append(cur)
        cur = None
if cur is not None:
    joined.append(cur)
spans = []
for b in joined:
    spans += re.findall(r"`([^`]+)`", b)
dropped = [x for x in v1 if x.startswith("| Coral bleaching | CRW Outlook |")]
print("order code spans:", len(spans), "| dropped row found in v1:", len(dropped))
quoted = spans + dropped

sm = difflib.SequenceMatcher(a=v1, b=v2, autojunk=False)
tot_add, tot_rem, bad = Counter(), Counter(), []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    a, b = v1[i1:i2], v2[j1:j2]
    print("== %s v1 %d-%d -> v2 %d-%d" % (tag, i1 + 1, i2, j1 + 1, j2))
    ta, tb = Counter(t for x in a for t in toks(x)), Counter(t for x in b for t in toks(x))
    add, rem = tb - ta, ta - tb
    wa, wb = Counter(w for x in a for w in words(x)), Counter(w for x in b for w in words(x))
    print("   number tokens added:", dict(add), "removed:", dict(rem))
    print("   number words added:", dict(wb - wa), "removed:", dict(wa - wb))
    tot_add += add
    tot_rem += rem
    # each changed stretch of characters must sit inside a quoted text
    for k in range(max(len(a), len(b))):
        x = a[k] if k < len(a) else ""
        y = b[k] if k < len(b) else ""
        cm = difflib.SequenceMatcher(a=x, b=y, autojunk=False)
        for t2, p1, p2, q1, q2 in cm.get_opcodes():
            if t2 == "equal":
                continue
            # widen each changed stretch to whole words for the containment test
            while p1 > 0 and x[p1 - 1] not in " (": p1 -= 1
            while p2 < len(x) and x[p2] not in " ),;:.": p2 += 1
            while q1 > 0 and y[q1 - 1] not in " (": q1 -= 1
            while q2 < len(y) and y[q2] not in " ),;:.": q2 += 1
            ox, ny = x[p1:p2].strip(), y[q1:q2].strip()
            okx = (not ox) or any(ox in s for s in quoted)
            oky = (not ny) or any(ny in s for s in quoted)
            if not (okx and oky):
                bad.append((i1 + k + 1, j1 + k + 1, ox[:80], ny[:80]))
print("TOTAL number tokens added:", dict(tot_add))
print("TOTAL number tokens removed:", dict(tot_rem))
print("changed stretches outside the order's quoted texts:", len(bad))
for r in bad[:20]:
    print("   ", r)

# c) table cells with a digit, keyed by table, panel, first cell and column header
def cells(L):
    out, table, panel, header = {}, None, "", None
    for n, x in enumerate(L, 1):
        m = re.match(r"\*\*Table (S?[0-9.]+)", x)
        if m:
            table, panel, header = m.group(1), "", None
            continue
        m = re.match(r"\*\*([a-g])\. ", x)
        if m:
            panel, header = m.group(1), None
            continue
        if x.startswith("|"):
            c = x[2:-2].split(" | ")
            if header is None:
                header = c
            elif set(x) <= set("|-"):
                continue
            else:
                for h, v in zip(header[1:], c[1:]):
                    if re.search(r"\d", v):
                        out[(table, panel, c[0], h)] = (n, v)
        else:
            header = None if x == "" else header
    return out
c1, c2 = cells(v1), cells(v2)
diff = [(k, c1.get(k), c2[k]) for k in c2 if c1.get(k, (0, None))[1] != c2[k][1]]
only1 = [k for k in c1 if k not in c2]
print("table cells with a digit: v1 %d, v2 %d; differing or new in v2: %d; in v1 only: %d" % (len(c1), len(c2), len(diff), len(only1)))
for d in diff[:10]:
    print("   v2-diff", d)
for k in only1[:10]:
    print("   v1-only", k, c1[k])

# d) cells.json
J2 = json.load(open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8"))
for who in ["A", "B"]:
    J1 = json.load(open(os.path.join(OUT, who, "cells_v1.json"), encoding="utf-8"))
    e1, e2 = J1["entries"], J2["entries"]
    keys = ["line", "table", "panel", "row", "column", "printed", "source", "selector", "stored"]
    nd = Counter()
    for a, b in zip(e1, e2):
        for k in keys + ["part", "cell"]:
            if json.dumps(a[k], ensure_ascii=False) != json.dumps(b[k], ensure_ascii=False):
                nd[k] += 1
    print("cells.json v2 vs %s v1: entries %d / %d; differing keys: %s" % (who, len(e1), len(e2), dict(nd)))
# every v2 entry's printed token sits in its cell, and the cell on its line of v2
miss = [e for e in J2["entries"] if e["cell"] not in v2[e["line"] - 1] or e["printed"] not in e["cell"]]
print("v2 entries whose cell is not on its line or whose printed token is not in its cell:", len(miss))
# the number tokens of the lines that hold entries are those of version 1 on the same line
lines = sorted(set(e["line"] for e in J2["entries"]))
chg = [n for n in lines if toks(v1[n - 1]) != toks(v2[n - 1])]
print("lines with entries: %d; of those, number tokens differing from v1's same line: %s" % (len(lines), chg))
