# Skeptic (version 5 check, item 3): no number changed and no line moved. Written independently of the reconciler's
# scripts (adapted from k31). Read-only; prints only.
#  a) line alignment of version 4 and version 5 (difflib): only same-size replacements, no line added, dropped or moved;
#  b) replay: version 4 with every OLD -> NEW pair of the change order (parsed from fix_order_v5.md, wrapped lines
#     joined by one space; the V5-5 sentence inserted after the Version 4 sentence) must give version 5, byte for byte;
#  c) number tokens (and marks) of every line: version 5 against version 4, the delta per line and in total, the tokens
#     outside the edited stretches in the same order, and every added token inside the order's NEW texts; a second,
#     broader token pattern (any digit run, any superscript or mark) as a cross-check;
#  d) every table cell of the changed lines: changed cells, and whether any changed cell holds a digit;
#  e) cells.json version 5 against version 4 (OUT\reconcile\cells_v4.json) entry by entry, and against both builders';
#     every entry's printed token in its cell and its cell a whole cell (or the whole note line) of its v5 line; the
#     entries on changed lines and their offsets;
#  f) the number tokens left in each data cell (and in each note line that holds entries) after the entries' printed
#     tokens are taken out, version 5 against version 4 (the same leftovers in both, apart from the order's NEW texts).
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


v4 = lines(os.path.join(RC, "tables_agreed_v4.md"))
v5 = lines(os.path.join(RC, "tables_agreed.md"))
print("lines: v4 %d, v5 %d" % (len(v4), len(v5)))
H = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
for who in ["A", "B"]:
    print("%s: tables.md == reconcile v5: %s | cells.json == reconcile: %s | tables_v4.md == reconcile v4: %s | cells_v4.json == reconcile cells_v4: %s" % (
        who, H(os.path.join(OUT, who, "tables.md")) == H(os.path.join(RC, "tables_agreed.md")),
        H(os.path.join(OUT, who, "cells.json")) == H(os.path.join(RC, "cells.json")),
        H(os.path.join(OUT, who, "tables_v4.md")) == H(os.path.join(RC, "tables_agreed_v4.md")),
        H(os.path.join(OUT, who, "cells_v4.json")) == H(os.path.join(RC, "cells_v4.json"))))

NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<±≤≥]")
BROAD = re.compile(r"\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵃᵇᶜᵈ†‡§×<>±≤≥∞½]")
toks = lambda s: NUM.findall(s)

# a) alignment
sm = difflib.SequenceMatcher(a=v4, b=v5, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
print("a) non-equal opcodes:", len(ops), "| kinds:", dict(Counter(o[0] for o in ops)),
      "| all same-size replacements at the same line numbers:", all(o[0] == "replace" and o[1] == o[3] and o[2] == o[4] for o in ops))
changed = [i + 1 for i in range(len(v5)) if v4[i] != v5[i]]
print("   changed lines (%d): %s" % (len(changed), changed))

# b) replay from the change order
order = open(os.path.join(OUT, "_brief", "fix_order_v5.md"), encoding="utf-8").read().split("\n")
blocks, cur, inside = [], None, False
for ln in order:
    if ln.startswith("## "):
        inside = bool(re.match(r"## V5-\d+\.", ln))
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
    for m in re.finditer(r"OLD: `([^`]+)`\s+NEW: `([^`]+)`", b):
        pairs.append((m.group(1), m.group(2)))
ins = re.search(r"after the Version 4 sentence, add `([^`]+)`", " ".join(blocks)).group(1)
anchor = "CHANGES_v4.md lists; no number changed."
print("b) OLD/NEW pairs parsed: %d; V5-5 sentence parsed; anchor occurs %d time(s) in v4" % (len(pairs), "\n".join(v4).count(anchor)))
rep = "\n".join(v4)
cnt = []
for o, n in pairs:
    cnt.append((rep.count(o), o, n))
    rep = rep.replace(o, n)
rep = rep.replace(anchor, anchor + " " + ins, 1)
print("   replay of version 4 == version 5 (text): %s | as bytes with the final LF: %s" % (
    rep.split("\n") == v5, (rep + "\n").encode("utf-8") == open(os.path.join(RC, "tables_agreed.md"), "rb").read()))
for c, o, n in cnt:
    print("   %2d x  %s -> %s" % (c, o[:60], n[:60]))

# c) tokens
tot_add, tot_rem, b_add, b_rem = Counter(), Counter(), Counter(), Counter()
outside_bad = []
for k in changed:
    x, y = v4[k - 1], v5[k - 1]
    tx, ty = Counter(toks(x)), Counter(toks(y))
    add, rem = ty - tx, tx - ty
    tot_add += add
    tot_rem += rem
    bx, by = Counter(BROAD.findall(x)), Counter(BROAD.findall(y))
    b_add += by - bx
    b_rem += bx - by
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
    print("c) line %3d: tokens v4 %d, v5 %d; added %s removed %s" % (k, len(toks(x)), len(toks(y)), dict(add), dict(rem)))
print("c) TOTAL tokens added:", dict(tot_add), "| removed:", dict(tot_rem))
print("   broad pattern: added", dict(b_add), "| removed", dict(b_rem))
print("   lines whose tokens outside the edited stretches differ:", outside_bad)
print("   whole file: tokens v4 %d, v5 %d (broad: v4 %d, v5 %d); unchanged lines' tokens equal: %s" % (
    sum(len(toks(x)) for x in v4), sum(len(toks(x)) for x in v5),
    sum(len(BROAD.findall(x)) for x in v4), sum(len(BROAD.findall(x)) for x in v5),
    all(toks(v4[i]) == toks(v5[i]) for i in range(len(v5)) if v4[i] == v5[i])))
newtxt = " ".join(n for _, n in pairs) + " " + ins
nt = Counter(toks(newtxt))
oldtxt = " ".join(o for o, _ in pairs)
print("   every added token occurs in the order's NEW texts (with multiplicity):", all(nt[t] >= c for t, c in tot_add.items()),
      "| NEW texts' tokens:", dict(nt), "| OLD texts' tokens:", dict(Counter(toks(oldtxt))))


# d) cells
def split_row(x):
    return x[2:-2].split(" | ") if x.startswith("| ") and x.endswith(" |") else None


nchg = 0
for k in changed:
    a, b = split_row(v4[k - 1]), split_row(v5[k - 1])
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
print("d) changed table cells: %d" % nchg)

# e) cells.json
J5 = json.load(open(os.path.join(RC, "cells.json"), encoding="utf-8"))
J4 = json.load(open(os.path.join(RC, "cells_v4.json"), encoding="utf-8"))
E5, E4 = J5["entries"], J4["entries"]
print("e) entries v4 %d, v5 %d; top-level keys v5 %s (v4 %s); tables_file %r, spec %r (v4: %r, %r)" % (
    len(E4), len(E5), list(J5), list(J4), J5["tables_file"], J5["spec"], J4["tables_file"], J4["spec"]))
nd = Counter()
for a, b in zip(E4, E5):
    if list(a) != list(b):
        nd["key order"] += 1
    for k in set(a) | set(b):
        if json.dumps(a.get(k), ensure_ascii=False) != json.dumps(b.get(k), ensure_ascii=False):
            nd[k] += 1
print("   keys differing v4 -> v5 (entry by entry):", dict(nd), "| other top-level values equal:",
      all(json.dumps(J4[k]) == json.dumps(J5[k]) for k in J5 if k != "entries"),
      "| byte-identical files:", H(os.path.join(RC, "cells.json")) == H(os.path.join(RC, "cells_v4.json")))
miss = [e for e in E5 if e["cell"] not in v5[e["line"] - 1] or e["printed"] not in e["cell"]]
print("   v5 entries whose cell is not on its line or whose printed token is not in its cell:", len(miss))
notwhole = []
for e in E5:
    x = v5[e["line"] - 1]
    cs = split_row(x)
    if not ((cs is not None and e["cell"] in cs) or e["cell"] == x):
        notwhole.append((e["line"], e["cell"][:40]))
print("   entries whose cell is not a whole cell of its v5 line (or the whole note line):", len(notwhole), notwhole[:5])
for k in changed:
    es = [e for e in E5 if e["line"] == k]
    cs5, cs4 = split_row(v5[k - 1]), split_row(v4[k - 1])
    print("   changed line %3d holds %2d entries%s" % (k, len(es), (
        "; cells %s at columns %s; changed columns of the line %s; char offsets v4 %s -> v5 %s" % (
            sorted(set(e["cell"] for e in es)), sorted(set(cs5.index(e["cell"]) for e in es)),
            [j for j, (p, q) in enumerate(zip(cs4, cs5)) if p != q],
            [v4[k - 1].find("| " + e["cell"] + " |", 0) for e in es][:3], [v5[k - 1].find("| " + e["cell"] + " |", 0) for e in es][:3])
        if es and cs5 and cs4 else "")))
over = []
by_line = defaultdict(Counter)
for e in E5:
    by_line[e["line"]][e["printed"]] += 1
for ln, c in by_line.items():
    for tok, n in c.items():
        if v5[ln - 1].count(tok) < n:
            over.append((ln, tok, n, v5[ln - 1].count(tok)))
print("   lines where a printed token occurs fewer times than its entries:", over[:5])


# f) leftover number tokens
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


l4, l5 = leftovers(v4, E4), leftovers(v5, E5)
print("f) leftover tokens in data cells: v4 %d, v5 %d; added in v5 %s; gone in v5 %s" % (
    sum(l4.values()), sum(l5.values()), dict(l5 - l4), dict(l4 - l5)))
