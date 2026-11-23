# Skeptic (version 3 check, item 3): no number changed and no line moved. Written independently of the reconciler's
# scripts. Read-only; prints only.
#  a) line alignment of version 2 and version 3 (difflib): only same-size replacements, no line added, dropped or moved;
#  b) replay: version 2 with every OLD -> NEW pair of the change order (parsed from fix_order_v3.md, wrapped lines
#     joined by one space; "..." tails stripped; the Table 9 sentence inserted after its anchor) must give version 3;
#  c) number tokens (and marks) of every line: version 3 against version 2, the delta per line and in total, and the
#     tokens outside the edited stretches in the same order;
#  d) every table cell: changed cells, and whether any changed cell holds a digit;
#  e) cells.json version 3 against version 2 (OUT\reconcile\cells_v2.json) entry by entry, and against both builders';
#     every entry's printed token in its cell and its cell on its line;
#  f) the header comment's claim "every printed data number is listed in cells.json": the number tokens left in each
#     data cell (and in each note line that holds entries) after the entries' printed tokens are taken out;
#  g) version 1 -> version 2 token delta (the CHANGES_v2.md correction of V3-7) and the line counts of versions 1 and 2.
import difflib, hashlib, json, os, re, sys
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
RC = os.path.join(OUT, "reconcile")


def lines(path):
    t = open(path, encoding="utf-8", newline="").read()
    assert t.endswith("\n")
    return t[:-1].split("\n")


v1 = lines(os.path.join(RC, "tables_agreed_v1.md"))
v2 = lines(os.path.join(RC, "tables_agreed_v2.md"))
v3 = lines(os.path.join(RC, "tables_agreed.md"))
print("lines: v1 %d, v2 %d, v3 %d" % (len(v1), len(v2), len(v3)))
for who in ["A", "B"]:
    for f, g in [("tables.md", os.path.join(RC, "tables_agreed.md")), ("cells.json", os.path.join(RC, "cells.json"))]:
        a = hashlib.sha256(open(os.path.join(OUT, who, f), "rb").read()).hexdigest()
        b = hashlib.sha256(open(g, "rb").read()).hexdigest()
        print("%s\\%s == reconcile copy: %s (%s...%s)" % (who, f, a == b, a[:8], a[-6:]))
for f in ["tables_v2.md", "cells_v2.json"]:
    for who in ["A", "B"]:
        p = os.path.join(OUT, who, f)
        if os.path.exists(p):
            g = os.path.join(RC, "tables_agreed_v2.md" if f.endswith(".md") else "cells_v2.json")
            print("%s\\%s == reconcile %s: %s" % (who, f, os.path.basename(g),
                                                  open(p, "rb").read() == open(g, "rb").read()))

NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<]")
toks = lambda s: NUM.findall(s)

# a) alignment
sm = difflib.SequenceMatcher(a=v2, b=v3, autojunk=False)
ops = [o for o in sm.get_opcodes() if o[0] != "equal"]
print("a) non-equal opcodes:", len(ops), "| kinds:", dict(Counter(o[0] for o in ops)),
      "| all same-size replacements at the same line numbers:", all(o[0] == "replace" and o[1] == o[3] and o[2] == o[4] for o in ops))
changed = [i + 1 for i in range(len(v3)) if v2[i] != v3[i]]
print("   changed lines (%d): %s" % (len(changed), changed))

# b) replay from the change order
order = open(os.path.join(OUT, "_brief", "fix_order_v3.md"), encoding="utf-8").read().split("\n")
blocks, cur = [], None
for ln in order:
    if ln.startswith("- "):
        if cur is not None:
            blocks.append(cur)
        cur = ln[2:]
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
    m = re.search(r"OLD(?: row label)?: `([^`]+)`.*?NEW: `([^`]+)`", b)
    if m:
        o, n = m.group(1), m.group(2)
        if o.startswith("...") and n.startswith("..."):
            o, n = o[3:], n[3:]
        pairs.append((o, n))
m = re.search(r"a new sentence directly after `([^`]+)` NEW: `([^`]+)`", " ".join(blocks))
anchor, ins = m.group(1), m.group(2)
pairs.append((anchor, anchor + " " + ins))
print("b) OLD/NEW pairs parsed: %d (incl. the inserted Table 9 sentence)" % len(pairs))
T2 = "\n".join(v2)
rep = T2
cnt = {}
for o, n in pairs:
    cnt[(o, n)] = rep.count(o)
    rep = rep.replace(o, n)
R = rep.split("\n")
print("   replay of version 2 == version 3:", R == v3)
for (o, n), c in cnt.items():
    print("   %2d x  %s" % (c, (o[:70] + " -> " + n[:50]).replace("\n", " ")))
if R != v3:
    for i, (x, y) in enumerate(zip(R, v3)):
        if x != y:
            print("   replay differs at line", i + 1)
            sm2 = difflib.SequenceMatcher(a=x, b=y, autojunk=False)
            for t, a1, a2, b1, b2 in sm2.get_opcodes():
                if t != "equal":
                    print("      ", t, repr(x[max(0, a1 - 30):a2 + 30]), "|", repr(y[max(0, b1 - 30):b2 + 30]))

# c) tokens
tot_add, tot_rem = Counter(), Counter()
outside_bad = []
for k in changed:
    x, y = v2[k - 1], v3[k - 1]
    tx, ty = Counter(toks(x)), Counter(toks(y))
    add, rem = ty - tx, tx - ty
    tot_add += add
    tot_rem += rem
    # tokens outside the edited stretches: mask the edits (char-level opcodes widened to word boundaries)
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
    if add or rem:
        print("c) line %3d: tokens added %s removed %s" % (k, dict(add), dict(rem)))
print("c) TOTAL tokens added:", dict(tot_add), "| removed:", dict(tot_rem))
print("   lines whose tokens outside the edited stretches differ:", outside_bad)
print("   whole file: tokens v2 %d, v3 %d; unchanged lines' tokens equal: %s" % (
    sum(len(toks(x)) for x in v2), sum(len(toks(x)) for x in v3),
    all(toks(v2[i]) == toks(v3[i]) for i in range(len(v3)) if v2[i] == v3[i])))


# d) cells
def split_row(x):
    return x[2:-2].split(" | ") if x.startswith("| ") and x.endswith(" |") else None


ccount = Counter()
for k in changed:
    a, b = split_row(v2[k - 1]), split_row(v3[k - 1])
    if a is None or b is None:
        continue
    if len(a) != len(b):
        print("d) line %d: column count differs %d vs %d" % (k, len(a), len(b)))
        continue
    for j, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            ccount[k] += 1
            dig = bool(re.search(r"\d", ca)) or bool(re.search(r"\d", cb))
            print("d) line %3d col %d changed (digit in old or new: %s): %r -> %r" % (k, j, dig, ca[:60], cb[:60]))
print("d) table lines with changed cells: %d, changed cells: %d" % (len(ccount), sum(ccount.values())))

# e) cells.json
J3 = json.load(open(os.path.join(RC, "cells.json"), encoding="utf-8"))
J2 = json.load(open(os.path.join(RC, "cells_v2.json"), encoding="utf-8"))
E3, E2 = J3["entries"], J2["entries"]
print("e) entries v2 %d, v3 %d; top-level keys v3 %s; tables_file %r, spec %r (v2: %r, %r)" % (
    len(E2), len(E3), list(J3), J3["tables_file"], J3["spec"], J2["tables_file"], J2["spec"]))
nd = Counter()
cell_lines = Counter()
for a, b in zip(E2, E3):
    if list(a) != list(b):
        nd["key order"] += 1
    for k in a:
        if json.dumps(a[k], ensure_ascii=False) != json.dumps(b.get(k), ensure_ascii=False):
            nd[k] += 1
            if k == "cell":
                cell_lines[b["line"]] += 1
print("   keys differing v2 -> v3:", dict(nd), "| lines of the changed cells:", dict(cell_lines))
on344 = [e for e in E3 if e["line"] == 344]
print("   line 344 entries:", len(on344), "| their cell == v3 line 344:", all(e["cell"] == v3[343] for e in on344),
      "| columns:", [e["column"] for e in on344])
miss = [e for e in E3 if e["cell"] not in v3[e["line"] - 1] or e["printed"] not in e["cell"]]
print("   v3 entries whose cell is not on its line or whose printed token is not in its cell:", len(miss))
# a cell must be a whole cell of its line (or the whole note line)
notwhole = []
for e in E3:
    x = v3[e["line"] - 1]
    cs = split_row(x)
    if not ((cs is not None and e["cell"] in cs) or e["cell"] == x):
        notwhole.append((e["line"], e["cell"][:40]))
print("   entries whose cell is not a whole cell (or the whole note line):", len(notwhole), notwhole[:5])
# entries on changed lines and whether their cell changed
for k in changed:
    es = [e for e in E3 if e["line"] == k]
    if es:
        cs3 = split_row(v3[k - 1])
        cs2 = split_row(v2[k - 1])
        same = [(e["cell"] in (cs2 or [v2[k - 1]])) for e in es]
        print("   changed line %3d holds %2d entries; their cell also a whole cell of the v2 line: %d of %d" % (
            k, len(es), sum(same), len(es)))
# the printed tokens per line fit the line
over = []
by_line = defaultdict(Counter)
for e in E3:
    by_line[e["line"]][e["printed"]] += 1
for ln, c in by_line.items():
    for tok, n in c.items():
        if v3[ln - 1].count(tok) < n:
            over.append((ln, tok, n, v3[ln - 1].count(tok)))
print("   lines where a printed token occurs fewer times than its entries:", over[:5])

# f) leftover number tokens in data cells and in note lines with entries
by_cell = defaultdict(list)
for e in E3:
    by_cell[(e["line"], e["cell"])].append(e["printed"])
left = Counter()
left_ex = defaultdict(list)
cur_table = None
for i, x in enumerate(v3, 1):
    mt = re.match(r"\*\*Table (S?[0-9.]+)", x)
    if mt:
        cur_table = mt.group(1)
    cs = split_row(x)
    targets = []
    if cs is not None and not set(x) <= set("|- "):
        targets = [(c, j) for j, c in enumerate(cs) if j > 0]
    elif (i, x) in by_cell:
        targets = [(x, -1)]
    for c, j in targets:
        rest = c
        for pr in sorted(by_cell.get((i, c), []), key=len, reverse=True):
            rest = rest.replace(pr, "\0", 1)
        rest = re.sub(r"`[^`]*`", "", rest)
        rest = re.sub(r"\b(PM2\.5|MERRA-2|EAC4|SEAS5|VT0007|E\d+a?|D\d+|AG1|AY\d|BB\d|S\d\.\d+|S-[A-Z]+)\b", "", rest)
        lt = [t for t in NUM.findall(rest) if not re.fullmatch(r"[ᵃᵇᶜᵈ†‡§×<]", t)]
        for t in lt:
            left[(cur_table, t)] += 1
            if len(left_ex[(cur_table, t)]) < 2:
                left_ex[(cur_table, t)].append("L%d: %s" % (i, c[:70]))
print("f) number tokens left in data cells / entry-holding note lines after the entries are taken out:")
for k in sorted(left, key=lambda z: (str(z[0]), z[1])):
    print("   table %-6s token %-8r x%-4d e.g. %s" % (k[0], k[1], left[k], " || ".join(left_ex[k])))

# g) version 1 -> version 2
d12 = Counter()
r12 = Counter()
for x, y in zip(v1, v2):
    if x != y:
        d12 += Counter(toks(y)) - Counter(toks(x))
        r12 += Counter(toks(x)) - Counter(toks(y))
print("g) v1 -> v2 by position: tokens added %s | removed %s" % (dict(d12), dict(r12)))
sm12 = difflib.SequenceMatcher(a=v1, b=v2, autojunk=False)
A, Rm = Counter(), Counter()
for t, a1, a2, b1, b2 in sm12.get_opcodes():
    if t != "equal":
        A += Counter(z for y in v2[b1:b2] for z in toks(y))
        Rm += Counter(z for y in v1[a1:a2] for z in toks(y))
print("   v1 -> v2 aligned (difflib): added %s | removed %s" % (dict(A - Rm), dict(Rm - A)))
