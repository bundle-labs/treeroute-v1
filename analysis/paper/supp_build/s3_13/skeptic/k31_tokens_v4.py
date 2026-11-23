# Skeptic (version 4 check, item 3): no number changed and no line moved. Written independently of the reconciler's
# scripts (adapted from k19). Read-only; prints only.
#  a) line alignment of version 3 and version 4 (difflib): only same-size replacements, no line added, dropped or moved;
#  b) replay: version 3 with every OLD -> NEW pair of the change order (parsed from fix_order_v4.md, wrapped lines
#     joined by one space; the V4-13 sentence inserted after the Version 3 sentence) must give version 4;
#  c) number tokens (and marks) of every line: version 4 against version 3, the delta per line and in total, and the
#     tokens outside the edited stretches in the same order; whole-file token sequence outside the changed lines;
#  d) every table cell of the changed lines: changed cells, and whether any changed cell holds a digit;
#  e) cells.json version 4 against version 3 (OUT\reconcile\cells_v3.json) entry by entry, and against both builders';
#     every entry's printed token in its cell and its cell a whole cell (or the whole note line) of its v4 line;
#  f) the number tokens left in each data cell (and in each note line that holds entries) after the entries' printed
#     tokens are taken out, version 4 against version 3 (the same leftovers in both).
import difflib, hashlib, json, os, re, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
RC = os.path.join(OUT, "reconcile")


def lines(path):
    t = open(path, encoding="utf-8", newline="").read()
    assert t.endswith("\n") and not t.endswith("\n\n")
    return t[:-1].split("\n")


v3 = lines(os.path.join(RC, "tables_agreed_v3.md"))
v4 = lines(os.path.join(RC, "tables_agreed.md"))
print("lines: v3 %d, v4 %d" % (len(v3), len(v4)))
H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
for who in ["A", "B"]:
    print("%s: tables.md == reconcile v4: %s | cells.json == reconcile: %s | tables_v3.md == reconcile v3: %s | cells_v3.json == reconcile cells_v3: %s" % (
        who, H(os.path.join(OUT, who, "tables.md")) == H(os.path.join(RC, "tables_agreed.md")),
        H(os.path.join(OUT, who, "cells.json")) == H(os.path.join(RC, "cells.json")),
        H(os.path.join(OUT, who, "tables_v3.md")) == H(os.path.join(RC, "tables_agreed_v3.md")),
        H(os.path.join(OUT, who, "cells_v3.json")) == H(os.path.join(RC, "cells_v3.json"))))

NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<±≤≥]")
toks = lambda s: NUM.findall(s)

# a) alignment
sm = difflib.SequenceMatcher(a=v3, b=v4, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
print("a) non-equal opcodes:", len(ops), "| kinds:", dict(Counter(o[0] for o in ops)),
      "| all same-size replacements at the same line numbers:", all(o[0] == "replace" and o[1] == o[3] and o[2] == o[4] for o in ops))
changed = [i + 1 for i in range(len(v4)) if v3[i] != v4[i]]
print("   changed lines (%d): %s" % (len(changed), changed))

# b) replay from the change order
order = open(os.path.join(OUT, "_brief", "fix_order_v4.md"), encoding="utf-8").read().split("\n")
blocks, cur, inside = [], None, False
for ln in order:
    if ln.startswith("## "):
        inside = bool(re.match(r"## V4-\d+\.", ln))
    if ln.startswith("- "):
        if cur is not None:
            blocks.append(cur)
        cur = ln[2:] if inside else None
    elif ln.startswith("  ") and cur is not None:
        cur += " " + ln[2:]
    else:
        if cur is not None:
            blocks.append(cur)
        cur = None
if cur is not None:
    blocks.append(cur)
pairs = []
for b in blocks:
    for m in re.finditer(r"OLD: `([^`]+)` NEW: `([^`]+)`", b):
        pairs.append((m.group(1), m.group(2)))
ins = re.search(r"after the Version 3 sentence, add `([^`]+)`", " ".join(blocks)).group(1)
anchor = "CHANGES_v3.md lists; no number changed."
print("b) OLD/NEW pairs parsed: %d; V4-13 sentence parsed; anchor occurs %d time(s) in v3" % (len(pairs), "\n".join(v3).count(anchor)))
rep = "\n".join(v3)
cnt = []
for o, n in pairs:
    cnt.append((rep.count(o), o, n))
    rep = rep.replace(o, n)
rep = rep.replace(anchor, anchor + " " + ins, 1)
R = rep.split("\n")
print("   replay of version 3 == version 4:", R == v4)
for c, o, n in cnt:
    print("   %2d x  %s -> %s" % (c, o[:60], n[:60]))

# c) tokens
tot_add, tot_rem = Counter(), Counter()
outside_bad = []
for k in changed:
    x, y = v3[k - 1], v4[k - 1]
    tx, ty = Counter(toks(x)), Counter(toks(y))
    add, rem = ty - tx, tx - ty
    tot_add += add
    tot_rem += rem
    cm = difflib.SequenceMatcher(a=x, b=y, autojunk=False)
    mx, my = list(x), list(y)
    for t, a1, a2, b1, b2 in cm.get_opcodes():
        if t == "equal":
            continue
        while a1 > 0 and x[a1 - 1] not in " (": a1 -= 1
        while a2 < len(x) and x[a2] not in " ),;:.": a2 += 1
        while b1 > 0 and y[b1 - 1] not in " (": b1 -= 1
        while b2 < len(y) and y[b2] not in " ),;:.": b2 += 1
        for i in range(a1, a2): mx[i] = "\0"
        for i in range(b1, b2): my[i] = "\0"
    ox = [t for seg in "".join(mx).split("\0") for t in toks(seg)]
    oy = [t for seg in "".join(my).split("\0") for t in toks(seg)]
    if ox != oy:
        outside_bad.append(k)
    print("c) line %3d: tokens v3 %d, v4 %d; added %s removed %s" % (k, len(toks(x)), len(toks(y)), dict(add), dict(rem)))
print("c) TOTAL tokens added:", dict(tot_add), "| removed:", dict(tot_rem))
print("   lines whose tokens outside the edited stretches differ:", outside_bad)
print("   whole file: tokens v3 %d, v4 %d; unchanged lines' tokens equal: %s" % (
    sum(len(toks(x)) for x in v3), sum(len(toks(x)) for x in v4),
    all(toks(v3[i]) == toks(v4[i]) for i in range(len(v4)) if v3[i] == v4[i])))
# the added tokens must lie inside the order's NEW texts
newtxt = " ".join(n for _, n in pairs) + " " + ins
nt = Counter(toks(newtxt))
print("   every added token occurs in the order's NEW texts (with multiplicity):", all(nt[t] >= c for t, c in tot_add.items()),
      "| NEW texts' tokens:", dict(nt))


# d) cells
def split_row(x):
    return x[2:-2].split(" | ") if x.startswith("| ") and x.endswith(" |") else None


nchg = 0
for k in changed:
    a, b = split_row(v3[k - 1]), split_row(v4[k - 1])
    if a is None or b is None:
        continue
    if len(a) != len(b):
        print("d) line %d: column count differs %d vs %d" % (k, len(a), len(b)))
        continue
    for j, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            nchg += 1
            dig = bool(re.search(r"\d", ca)) or bool(re.search(r"\d", cb))
            print("d) line %3d col %d changed (digit in old or new: %s): %r -> %r" % (k, j, dig, ca[:50], cb[:50]))
print("d) changed cells: %d" % nchg)

# e) cells.json
J4 = json.load(open(os.path.join(RC, "cells.json"), encoding="utf-8"))
J3 = json.load(open(os.path.join(RC, "cells_v3.json"), encoding="utf-8"))
E4, E3 = J4["entries"], J3["entries"]
print("e) entries v3 %d, v4 %d; top-level keys v4 %s (v3 %s); tables_file %r, spec %r (v3: %r, %r)" % (
    len(E3), len(E4), list(J4), list(J3), J4["tables_file"], J4["spec"], J3["tables_file"], J3["spec"]))
nd = Counter()
for a, b in zip(E3, E4):
    if list(a) != list(b):
        nd["key order"] += 1
    for k in set(a) | set(b):
        if json.dumps(a.get(k), ensure_ascii=False) != json.dumps(b.get(k), ensure_ascii=False):
            nd[k] += 1
print("   keys differing v3 -> v4 (entry by entry):", dict(nd), "| other top-level values equal:",
      all(json.dumps(J3[k]) == json.dumps(J4[k]) for k in J4 if k != "entries"))
miss = [e for e in E4 if e["cell"] not in v4[e["line"] - 1] or e["printed"] not in e["cell"]]
print("   v4 entries whose cell is not on its line or whose printed token is not in its cell:", len(miss))
notwhole = []
for e in E4:
    x = v4[e["line"] - 1]
    cs = split_row(x)
    if not ((cs is not None and e["cell"] in cs) or e["cell"] == x):
        notwhole.append((e["line"], e["cell"][:40]))
print("   entries whose cell is not a whole cell of its v4 line (or the whole note line):", len(notwhole), notwhole[:5])
for k in changed:
    es = [e for e in E4 if e["line"] == k]
    if es:
        cs4, cs3 = split_row(v4[k - 1]), split_row(v3[k - 1])
        cols = sorted(set((cs4 or []).index(e["cell"]) for e in es if cs4 and e["cell"] in cs4))
        print("   changed line %3d holds %2d entries; their cells whole cells of v3 and v4 lines: %d of %d; at columns %s (changed column of this line: %s)" % (
            k, len(es), sum(1 for e in es if cs3 and e["cell"] in cs3 and e["cell"] in cs4), len(es), cols,
            [j for j, (p, q) in enumerate(zip(cs3, cs4)) if p != q] if cs3 and cs4 else None))
over = []
by_line = defaultdict(Counter)
for e in E4:
    by_line[e["line"]][e["printed"]] += 1
for ln, c in by_line.items():
    for tok, n in c.items():
        if v4[ln - 1].count(tok) < n:
            over.append((ln, tok, n, v4[ln - 1].count(tok)))
print("   lines where a printed token occurs fewer times than its entries:", over[:5])
print("   entries on changed lines with a printed token that also occurs in a changed cell:",
      [(e["line"], e["printed"]) for e in E4 if e["line"] in changed and split_row(v4[e["line"] - 1]) and any(
          e["printed"] in cb for ca, cb in zip(split_row(v3[e["line"] - 1]), split_row(v4[e["line"] - 1])) if ca != cb)])


# f) leftover number tokens (v3 and v4 must give the same leftovers)
def leftovers(V, E):
    by_cell = defaultdict(list)
    for e in E:
        by_cell[(e["line"], e["cell"])].append(e["printed"])
    left = Counter()
    for i, x in enumerate(V, 1):
        cs = split_row(x)
        targets = []
        if cs is not None and not set(x) <= set("|- "):
            targets = [c for j, c in enumerate(cs) if j > 0]
        elif (i, x) in by_cell:
            targets = [x]
        for c in targets:
            rest = c
            for pr in sorted(by_cell.get((i, c), []), key=len, reverse=True):
                rest = rest.replace(pr, "\0", 1)
            rest = re.sub(r"`[^`]*`", "", rest)
            for t in NUM.findall(rest):
                left[(i, t)] += 1
    return left


l3, l4 = leftovers(v3, E3), leftovers(v4, E4)
print("f) leftover tokens in data cells: v3 %d, v4 %d; differences: %s" % (
    sum(l3.values()), sum(l4.values()), dict((l4 - l3) + Counter({("-" + str(k[0]), k[1]): v for k, v in (l3 - l4).items()}))))
