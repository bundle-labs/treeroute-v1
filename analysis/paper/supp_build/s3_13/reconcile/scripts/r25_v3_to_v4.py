# r25 (version 4, step 2b): diff of version 3 (OUT\reconcile\tables_agreed_v3.md) with version 4 (the builders' common
# tables.md, OUT\A\tables.md = OUT\B\tables.md). Read-only; prints; stops on any failure.
#  1. The order's texts are the code spans of the bullets of OUT\_brief\fix_order_v4.md, sections V4-1 to V4-13 (a
#     bullet's wrapped lines joined with one space): each OLD and NEW span ("OLD:", "NEW:") and the sentence that V4-13
#     adds ("add `...`"). V4-13 puts it "after the Version 3 sentence": in version 3's header comment, the one sentence
#     that starts "Version 3 (" and ends with the text that CHANGES_v4.md quotes as that sentence's end, followed by the
#     text that CHANGES_v4.md quotes as the next (the sentence is replaced by itself + " " + the added sentence). Each
#     printed text is also a single-line fenced text of OUT\spec\CHANGES_v4.md.
#  2. Every OLD text is found in version 3 exactly once, in the table, on the kind of line and (for table rows) in the
#     column that the order names. Version 3 with exactly those replacements (positions taken in version 3; no two on
#     a line overlap) must give the builders' version 4 byte for byte, and no OLD text may be left in version 4 outside
#     a NEW text.
#  3. A difflib alignment of the two files must find changed lines exactly where step 2 applied a change (no line
#     added, dropped or moved); every changed line is attributed to its changes of the order. The list is compared with
#     CHANGES_v4.md's list of changed lines.
#  4. Number tokens: on every changed line, no token straddles a replaced span, the tokens outside the replaced spans
#     are the same and in the same order in both versions, and the tokens added and removed are exactly those of the
#     line's NEW and OLD texts; the same over the whole file (every other line is equal, so its tokens are too).
#  5. cells.json: version 4 (A = B) against version 3 (OUT\reconcile\cells_v3.json = both builders' cells_v3.json):
#     bytes, keys, order and values; every entry's printed token found in its cell on its line in both versions, at
#     its version-3 position plus the length change of the replaced texts before it, and outside every replaced span.
#  6. V4-13's two bullets that change no line of tables.md, read-only: OUT\spec\CHANGES_v3.md holds the corrected text
#     that CHANGES_v4.md quotes and not the text before the correction; TABLE_SPEC.md has the heading
#     "## 11. Version 4 (2026-11-17)"; OUT\spec\CHANGES_v4.md exists.
import sys, re, json, difflib, hashlib, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]


def stop(msg):
    raise SystemExit("stop: " + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- 1. the order's texts ----------------
order = (OUT / "_brief" / "fix_order_v4.md").read_text(encoding="utf-8").split("\n")
bullets, cur, inb = collections.OrderedDict(), None, False
for l in order:
    m = re.match(r"^## (V4-\d+)\. ", l)
    if m:
        cur, inb = m.group(1), False
        bullets[cur] = []
        continue
    if l.startswith("## "):
        cur, inb = None, False
        continue
    if cur is None:
        continue
    if l.startswith("- "):
        bullets[cur].append(l[2:])
        inb = True
    elif inb and l.startswith("  ") and l.strip():
        bullets[cur][-1] += " " + l.strip()
    else:
        inb = False
IDS = ["V4-%d" % k for k in range(1, 14)]
if list(bullets) != IDS:
    stop("the order's sections are not V4-1 to V4-13: %s" % list(bullets))
SP = {c: [re.findall(r"`([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
WANT = {"V4-1": [2], "V4-2": [2], "V4-3": [2, 2, 2], "V4-4": [2], "V4-5": [2], "V4-6": [2, 2], "V4-7": [2], "V4-8": [2],
        "V4-9": [2], "V4-10": [2], "V4-11": [2], "V4-12": [2], "V4-13": [1, 1, 1]}
got = {c: [len(x) for x in v] for c, v in SP.items()}
print("order: sections", list(bullets), "; code spans per bullet:", got)
if got != WANT:
    stop("the order's bullets are not as expected")
OLDS = {c: [re.findall(r"\bOLD: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
NEWS = {c: [re.findall(r"\bNEW: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
n_old = sum(len(x) for v in OLDS.values() for x in v)
n_new = sum(len(x) for v in NEWS.values() for x in v)
ch = (OUT / "spec" / "CHANGES_v4.md").read_text(encoding="utf-8")
chs = re.sub(r"\s+", " ", ch)
mm = re.search(r"\((\d+) OLD, (\d+) NEW and the sentence that V4-13 adds;", chs)
print("order: OLD texts", n_old, "; NEW texts", n_new, "; CHANGES_v4.md says", mm.group(1) if mm else None, "OLD and",
      mm.group(2) if mm else None, "NEW, and the sentence that V4-13 adds")
if not mm or (n_old, n_new) != (int(mm.group(1)), int(mm.group(2))):
    stop("the number of OLD and NEW texts")
used = set()


def on(c, k):
    """the OLD and NEW texts of bullet k (0-based) of section c"""
    o, n = OLDS[c][k], NEWS[c][k]
    if len(o) != 1 or len(n) != 1:
        stop("%s bullet %d: not one OLD and one NEW" % (c, k + 1))
    if o[0].startswith("...") or n[0].startswith("..."):
        stop("%s bullet %d: a text starts with '...'" % (c, k + 1))
    used.add((c, k))
    return o[0], n[0]


b13 = bullets["V4-13"][0]
adds = re.findall(r"\badd `([^`]*)`", b13)
if len(adds) != 1 or "after the Version 3 sentence" not in b13 or OLDS["V4-13"][0] or NEWS["V4-13"][0]:
    stop("V4-13, first bullet: the added sentence")
used.add(("V4-13", 0))
NEWSENT = adds[0]
ma = re.search(r"added directly after the Version 3 sentence \(which ends `([^`]*)`\) and before `([^`]*)`", chs)
if not ma:
    stop("CHANGES_v4.md: the place of the V4-13 sentence")
END3, AFTER3 = ma.group(1), ma.group(2)
print("V4-13: added sentence (order):", NEWSENT)
print("V4-13: the Version 3 sentence ends (CHANGES_v4.md): %r ; followed by: %r" % (END3, AFTER3))
for c in ("V4-13",):
    for k in (1, 2):
        if OLDS[c][k] or NEWS[c][k]:
            stop("V4-13 bullet %d has an OLD or NEW text" % (k + 1))
print("V4-13 bullets 2 and 3 (no text of tables.md):", [bullets["V4-13"][1][:90], bullets["V4-13"][2][:90]])

# version 3 and version 4
v3b = (OUT / "reconcile" / "tables_agreed_v3.md").read_bytes()
v4b = (OUT / "A" / "tables.md").read_bytes()
if v4b != (OUT / "B" / "tables.md").read_bytes():
    stop("OUT\\A\\tables.md and OUT\\B\\tables.md differ")
for X in ("A", "B"):
    if (OUT / X / "tables_v3.md").read_bytes() != v3b:
        stop("OUT\\%s\\tables_v3.md differs from tables_agreed_v3.md" % X)
mv3 = re.search(r"\b([0-9a-f]{64})\b, 785 lines, a byte copy of both builders' tables\.md", chs)
print("version 3 (tables_agreed_v3.md = A, B tables_v3.md):", len(v3b), "bytes,", v3b.count(b"\n"), "LF, sha256", sha(v3b),
      "; the SHA-256 that CHANGES_v4.md gives:", bool(mv3) and mv3.group(1) == sha(v3b))
print("version 4 (A = B tables.md):                        ", len(v4b), "bytes,", v4b.count(b"\n"), "LF, sha256", sha(v4b))
if not (mv3 and mv3.group(1) == sha(v3b)):
    stop("version 3 is not the file CHANGES_v4.md names")
s3, s4 = v3b.decode("utf-8"), v4b.decode("utf-8")
L3, L4 = s3.split("\n"), s4.split("\n")

# the anchor of V4-13: the Version 3 sentence of version 3's header comment
k_end = s3.find(END3)
if k_end == -1 or s3.count(END3) != 1 or not s3.startswith(" " + AFTER3, k_end + len(END3)):
    stop("V4-13: the end of the Version 3 sentence is not once in version 3, followed by the quoted text")
k_start = s3.rfind("Version 3 (", 0, k_end)
if k_start < 2 or s3[k_start - 2:k_start] != ". " or ". " in s3[k_start:k_end] or "\n" in s3[k_start:k_end]:
    stop("V4-13: the Version 3 sentence")
ANCHOR = s3[k_start:k_end + len(END3)]
print("V4-13: the Version 3 sentence of version 3 (%d characters, line %d): %s" % (len(ANCHOR), s3[:k_start].count("\n") + 1, ANCHOR))

# (change id, label, OLD, NEW, tables, line prefix, column header (rows only), fit)
C = [
    ("V4-13", "header comment: the Version 4 sentence after the Version 3 sentence", ANCHOR, ANCHOR + " " + NEWSENT, {None},
     "<!-- Draft tables of Supplement S3.13", None, None),
    ("V4-3", "Table 9 caption: coral bleaching's background", *on("V4-3", 2), {"9"}, "**Table 9.** ", None, None),
    ("V4-4", "Table 9 caption: the context-and-calendar family", *on("V4-4", 0), {"9"}, "**Table 9.** ", None, None),
    ("V4-12", "S3.18 caption: its source comment", *on("V4-12", 0), {"S3.18"}, "**Table S3.18 (post hoc).** ", None, None),
    ("V4-7", "S3.18 b: the column header line", *on("V4-7", 0), {"S3.18"}, "| Problem | ", None, "header"),
    ("V4-3", "S3.19 note b", *on("V4-3", 0), {"S3.19"}, "ᵇ ", None, "line"),
    ("V4-3", "S3.19 note c", *on("V4-3", 1), {"S3.19"}, "ᶜ Background (B2): ", None, None),
    ("V4-5", "S3.21 Adopted arm: NDVI's cell", *on("V4-5", 0), {"S3.21"}, "| Adopted arm | ", "NDVI", "cell"),
    ("V4-2", "S3.21 E3a: what it checks", *on("V4-2", 0), {"S3.21"}, "| E3a | ", "What it checks", "cell"),
    ("V4-1", "S3.21 E3m: what it checks", *on("V4-1", 0), {"S3.21"}, "| E3m | ", "What it checks", "cell"),
    ("V4-10", "S3.21 E3: what it checks", *on("V4-10", 0), {"S3.21"}, "| E3 | ", "What it checks", "cell"),
    ("V4-6", "S3.21 E5: what it checks", *on("V4-6", 0), {"S3.21"}, "| E5ᵃ | ", "What it checks", "cell"),
    ("V4-11", "S3.21 E8: what it checks", *on("V4-11", 0), {"S3.21"}, "| E8 | ", "What it checks", "cell"),
    ("V4-6", "S3.21 note a", *on("V4-6", 1), {"S3.21"}, "ᵃ E5 is informational: ", None, None),
    ("V4-8", "S3.22 row label", *on("V4-8", 0), {"S3.22"}, "| ", "Quantity", "cell"),
    ("V4-9", "S3.28 caption: the pair's J", *on("V4-9", 0), {"S3.28"}, "**Table S3.28 (post hoc; sensitivity).** ", None, None),
]
withtext = {(c, k) for c, bl in bullets.items() for k in range(len(bl)) if OLDS[c][k] or NEWS[c][k]} | {("V4-13", 0)}
print("order: bullets with a text of tables.md", len(withtext), "; used here", len(used), "; not used:", sorted(withtext - used))
if withtext != used:
    stop("an order text is not used")
# CHANGES_v4.md: its single-line fenced texts
CHL, single, i = ch.split("\n"), [], 0
while i < len(CHL):
    if CHL[i].startswith("```"):
        j = i + 1
        while not CHL[j].startswith("```"):
            j += 1
        if j == i + 2:
            single.append(CHL[i + 1])
        i = j + 1
    else:
        i += 1
texts = [NEWSENT] + [t for c in C[1:] for t in c[2:4]]
notin = [t for t in texts if t not in single]
print("order texts checked against CHANGES_v4.md:", len(texts), "; not a single-line fenced text there:", notin)
if notin or len(texts) != 1 + n_old + n_new:
    stop("CHANGES_v4.md")


# ---------------- 2. version 3 + the order's changes ----------------
def tables_of(L):
    out, cur = [], None
    for t in L:
        m = re.match(r"^\*\*Table (9|S3\.\d+)\b", t)
        if m:
            cur = m.group(1)
        elif t.startswith("## ") or t.startswith("<!--"):
            cur = None
        out.append(cur)
    return out


def cells_pos(s):
    if not (s.startswith("| ") and s.endswith(" |")):
        return None
    out, p = [], 2
    for c in s[2:-2].split(" | "):
        out.append((p, p + len(c), c))
        p += len(c) + 3
    return out


def header_of(L, i):
    k = i
    while not L[k - 1].startswith("|---"):
        if not L[k - 1].startswith("| "):
            return None
        k -= 1
    return L[k - 2][2:-2].split(" | ")


TAB3 = tables_of(L3)
spans = collections.defaultdict(list)   # 0-based line -> [(start, end, NEW, change id, label)]
cols_seen = collections.defaultdict(collections.Counter)
for cid, label, old, new, tabs, prefix, col, fit in C:
    hits = []
    for i, t in enumerate(L3):
        k = t.find(old)
        while k != -1:
            hits.append((i, k))
            k = t.find(old, k + 1)
    if len(hits) != 1 or s3.count(old) != 1:
        stop("%s %s: OLD found %d times in version 3, not once: %r" % (cid, label, len(hits), old[:80]))
    for i, k in hits:
        t = L3[i]
        if TAB3[i] not in tabs or not t.startswith(prefix):
            stop("%s %s: OLD in an unexpected place (line %d, table %s)" % (cid, label, i + 1, TAB3[i]))
        if fit == "line" and t != old:
            stop("%s %s: line %d is not the OLD text alone" % (cid, label, i + 1))
        if fit == "header" and not (t == old and L3[i + 1].startswith("|---") and not L3[i - 1].startswith("|")):
            stop("%s %s: line %d is not a table's header line" % (cid, label, i + 1))
        if col is not None:
            cp, hd = cells_pos(t), header_of(L3, i)
            inside = [j for j, (a, b, c) in enumerate(cp) if a <= k and k + len(old) <= b]
            if len(inside) != 1 or hd is None or len(hd) != len(cp):
                stop("%s %s: line %d, the cell of OLD" % (cid, label, i + 1))
            j = inside[0]
            a, b, c = cp[j]
            if not hd[j].startswith(col) or not (fit == "cell" and c == old):
                stop("%s %s: line %d, column %r, fit %s" % (cid, label, i + 1, hd[j], fit))
            cols_seen[label][hd[j]] += 1
        spans[i].append((k, k + len(old), new, cid, label))
print("columns of the row changes (header: places):", {k: dict(v) for k, v in cols_seen.items()})
E = list(L3)
newspans = {}
for i, sp in spans.items():
    sp.sort()
    for x, y in zip(sp, sp[1:]):
        if x[1] > y[0]:
            stop("two OLD texts overlap on line %d" % (i + 1))
    t, out, p, ns = L3[i], "", 0, []
    for a, b, new, cid, label in sp:
        out += t[p:a]
        ns.append((len(out), len(out) + len(new)))
        out += new
        p = b
    E[i] = out + t[p:]
    newspans[i] = ns
exp = "\n".join(E).encode("utf-8")
print("places replaced:", sum(len(v) for v in spans.values()), "on", len(spans), "lines")
print("version 3 + the order's changes == version 4, byte for byte:", exp == v4b, "; sha256", sha(exp))
if exp != v4b:
    for i, (x, y) in enumerate(zip(E, L4), 1):
        if x != y:
            print("first differing line", i, "\n  expected :", x[:300], "\n  version 4:", y[:300])
            break
    stop("the rebuild differs from version 4")
left = []
for cid, label, old, new, *_ in C[1:]:
    for i, t in enumerate(L4):
        k = t.find(old)
        while k != -1:
            if not any(a <= k and k + len(old) <= b for a, b in newspans.get(i, [])):
                left.append((cid, label, i + 1))
            k = t.find(old, k + 1)
inside_new = sorted({(cid, label) for cid, label, old, new, *_ in C[1:] if old in new})
print("OLD texts left in version 4 outside a NEW text:", left, "; OLD texts that are part of their NEW text:", inside_new)
if left:
    stop("an OLD text is left in version 4")

# ---------------- 3. alignment and attribution ----------------
sm = difflib.SequenceMatcher(None, L3, L4, autojunk=False)
ops, ne3, ne4, moved = [], set(), set(), []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        moved += [(a + 1, b + 1) for a, b in zip(range(i1, i2), range(j1, j2)) if a != b]
        continue
    ops.append((tag, i1 + 1, i2, j1 + 1, j2))
    ne3.update(range(i1 + 1, i2 + 1))
    ne4.update(range(j1 + 1, j2 + 1))
mine = {i + 1 for i in spans}
print("lines: version 3", len(L3) - 1, "+ final LF; version 4", len(L4) - 1, "+ final LF")
print("difflib opcodes other than equal:", len(ops), "; all 'replace' with as many lines on each side, at the same place:",
      all(t == "replace" and i1 == j1 and i2 == j2 for t, i1, i2, j1, j2 in ops))
print("difflib's unequal lines == the lines where a change was applied: version 3", ne3 == mine, "; version 4", ne4 == mine,
      "; unchanged lines that moved:", moved)
if ne3 != mine or ne4 != mine or moved or len(L3) != len(L4) or len(L4) - 1 != 785:
    stop("the alignment does not agree with the rebuild")
pos = [i + 1 for i in range(len(L3)) if L3[i] != L4[i]]
ml = re.search(r"The lines that change \(1-based, (\d+)\): ([\d, ]+)\.", chs)
listed = [int(x) for x in ml.group(2).split(", ")]
print("lines that differ by position:", len(pos), pos)
print("equal to CHANGES_v4.md's list of changed lines (%s):" % ml.group(1), pos == listed)
if pos != listed or int(ml.group(1)) != len(pos):
    stop("CHANGES_v4.md's list of changed lines")
by = collections.OrderedDict((c, collections.OrderedDict()) for c in IDS)
for i in sorted(spans):
    for a, b, new, cid, label in spans[i]:
        by[cid].setdefault(label, []).append(i + 1)
multi = {i + 1: sorted({x[3] for x in sp}) for i, sp in spans.items() if len({x[3] for x in sp}) > 1}
for cid, d in by.items():
    lines = sorted({x for v in d.values() for x in v})
    print("%s: %d places on %d lines: %s" % (cid, sum(len(v) for v in d.values()), len(lines), ", ".join(map(str, lines))))
    for label, v in d.items():
        print("     %-62s %s" % (label, v))
print("lines carrying more than one change id:", multi)

# ---------------- 4. number tokens ----------------
NUMRE = re.compile("[−-]?\\d+(?:[.,]\\d+)*%?|[⁰¹²³⁴-⁹⁻]+")


def toks(s):
    return collections.Counter(NUMRE.findall(s))


bad = []
for i, sp in spans.items():
    t3, t4 = L3[i], L4[i]
    o_sp = [(a, b) for a, b, _, _, _ in sp]
    n_sp = newspans[i]
    out3, out4, strad = [], [], []
    for m in NUMRE.finditer(t3):
        ins_ = [(a, b) for a, b in o_sp if a < m.end() and m.start() < b]
        if not ins_:
            out3.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v3", m.group(0)))
    for m in NUMRE.finditer(t4):
        ins_ = [(a, b) for a, b in n_sp if a < m.end() and m.start() < b]
        if not ins_:
            out4.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v4", m.group(0)))
    e = collections.Counter()
    for a, b, new, cid, label in sp:
        e.update(toks(new))
        e.subtract(toks(t3[a:b]))
    e = {k: v for k, v in e.items() if v}
    d = collections.Counter(toks(t4))
    d.subtract(toks(t3))
    d = {k: v for k, v in d.items() if v}
    if strad or out3 != out4 or d != e:
        bad.append((i + 1, strad, out3 == out4, d, e))
d_all = collections.Counter(toks(s4))
d_all.subtract(toks(s3))
added = sorted((k, v) for k, v in d_all.items() if v > 0)
removed = sorted((k, -v) for k, v in d_all.items() if v < 0)
e_all = collections.Counter()
for i, sp in spans.items():
    for a, b, new, cid, label in sp:
        e_all.update(toks(new))
        e_all.subtract(toks(L3[i][a:b]))
print("number tokens (regex %s): version 3 %d, version 4 %d" % (NUMRE.pattern, sum(toks(s3).values()), sum(toks(s4).values())))
print("   added:", added, "(%d)" % sum(v for _, v in added))
print("   removed:", removed)
add_by = collections.defaultdict(list)
for i, sp in sorted(spans.items()):
    d = collections.Counter(toks(L4[i]))
    d.subtract(toks(L3[i]))
    for k, v in sorted(d.items()):
        if v:
            add_by[i + 1].append("%s x%d" % (k, v) if v != 1 else k)
print("   added, by line:", dict(add_by))
same_lines = [i for i in range(len(L3)) if i not in spans]
print("per changed line: no straddling token, the tokens outside the replaced spans equal and in order, and the tokens",
      "added/removed == those of the line's NEW/OLD texts:", not bad, bad[:3])
print("unchanged lines (%d): equal, so their tokens are equal and in order:" % len(same_lines), all(L3[i] == L4[i] for i in same_lines))
print("whole file: tokens added/removed == those of the order's texts:", {k: v for k, v in d_all.items() if v} == {k: v for k, v in e_all.items() if v})
if bad or removed or {k: v for k, v in d_all.items() if v} != {k: v for k, v in e_all.items() if v}:
    stop("number tokens")

# ---------------- 5. cells.json ----------------
c3b = (OUT / "reconcile" / "cells_v3.json").read_bytes()
for X in ("A", "B"):
    if (OUT / X / "cells_v3.json").read_bytes() != c3b:
        stop("OUT\\%s\\cells_v3.json differs from OUT\\reconcile\\cells_v3.json" % X)
c4b = (OUT / "A" / "cells.json").read_bytes()
if c4b != (OUT / "B" / "cells.json").read_bytes():
    stop("OUT\\A\\cells.json and OUT\\B\\cells.json differ")
print("cells.json version 3 (reconcile copy = A, B cells_v3.json):", len(c3b), "bytes, sha256", sha(c3b))
print("cells.json version 4 (A = B):                              ", len(c4b), "bytes, sha256", sha(c4b), "; byte-identical to version 3:", c4b == c3b)
D3, D4 = json.loads(c3b.decode("utf-8")), json.loads(c4b.decode("utf-8"))
E3, E4 = D3["entries"], D4["entries"]
print("top level: keys", list(D4), "; tables_file", repr(D4["tables_file"]), "; spec", repr(D4["spec"]), "; equal to version 3:",
      list(D3) == list(D4) and D3["tables_file"] == D4["tables_file"] and D3["spec"] == D4["spec"], "; entries", len(E3), "->", len(E4))
if list(D3) != list(D4) or D3["tables_file"] != D4["tables_file"] or D3["spec"] != D4["spec"] or len(E3) != len(E4):
    stop("cells.json top level")
if c4b.decode("utf-8") != json.dumps(D4, ensure_ascii=False, indent=1, allow_nan=False) + "\n":
    stop("version-4 cells.json is not in the spec's json.dumps form")


def cells_of(s):
    cp = cells_pos(s)
    return [(a, c) for a, b, c in cp] if cp else [(0, s)]


def locate(L, ents):
    res, cursor = [], {}
    for e in ents:
        s = L[e["line"] - 1]
        tok, c0 = e["printed"], cursor.get(e["line"], 0)
        cl, found = cells_of(s), None
        k = s.find(tok, c0)
        while k != -1:
            pv = s[k - 1] if k > 0 else " "
            pv2 = s[k - 2] if k > 1 else " "
            nx = s[k + len(tok)] if k + len(tok) < len(s) else " "
            nx2 = s[k + len(tok) + 1] if k + len(tok) + 1 < len(s) else " "
            okb = not (pv.isdigit() or (pv in ".," and pv2.isdigit()) or pv in "−-") and \
                not (nx.isdigit() or (nx in ".," and nx2.isdigit()) or nx == "%")
            if okb and any(cp <= k and k + len(tok) <= cp + len(ct) and ct == e["cell"] for cp, ct in cl):
                found = k
                break
            k = s.find(tok, k + 1)
        res.append(found)
        if found is not None:
            cursor[e["line"]] = found + len(tok)
    return res


P3, P4 = locate(L3, E3), locate(L4, E4)
print("entries whose printed token is found in its cell on its line, in reading order: version 3", sum(x is not None for x in P3),
      "; version 4", sum(x is not None for x in P4), "of", len(E4))
if any(x is None for x in P3) or any(x is None for x in P4):
    stop("an entry is not on its line")
SKEY = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)  # noqa: E731
dk, moved_n, off_place, in_span = collections.Counter(), 0, 0, []
for e3, e4, p3, p4 in zip(E3, E4, P3, P4):
    if list(e3) != list(e4):
        stop("key order")
    for kk in e3:
        if SKEY(e3[kk]) != SKEY(e4[kk]):
            dk[kk] += 1
    i = e3["line"] - 1
    shift = sum(len(new) - (b - a) for a, b, new, _, _ in spans.get(i, []) if b <= p3)
    if p4 != p3 + shift:
        off_place += 1
    if p4 != p3:
        moved_n += 1
    if any(a < p3 + len(e3["printed"]) and p3 < b for a, b, _, _, _ in spans.get(i, [])) or \
            any(a < p4 + len(e4["printed"]) and p4 < b for a, b in newspans.get(i, [])):
        in_span.append((e3["line"], e3["printed"]))
on_changed = collections.Counter(e["line"] for e in E4 if (e["line"] - 1) in spans)
rows_on = collections.Counter((e["table"], e["row"], e["line"]) for e in E4 if (e["line"] - 1) in spans)
print("entry keys that differ, version 3 -> 4:", dict(dk))
print("version-4 entries on changed lines:", sum(on_changed.values()), dict(sorted(on_changed.items())), dict(rows_on))
cell_changed = [e["line"] for e in E4 if (e["line"] - 1) in spans and
                not any(ct == e["cell"] for _, ct in cells_of(L3[e["line"] - 1]))]
print("entries on changed lines whose cell is not a version-3 cell of their line:", cell_changed)
print("entries whose token moved on its line:", moved_n, "; not at its version-3 position plus the length change of the replaced",
      "texts before it:", off_place, "; tokens inside a replaced span (OLD or NEW):", in_span)
if dk or off_place or in_span or cell_changed or c4b != c3b:
    stop("cells.json version 3 -> 4")

# ---------------- 6. V4-13's bullets outside tables.md ----------------
ch3 = (OUT / "spec" / "CHANGES_v3.md").read_text(encoding="utf-8")


def fenced_after(label):
    k = [i for i, l in enumerate(CHL) if l.strip() == label]
    if len(k) != 1 or not CHL[k[0] + 2].startswith("```"):
        stop("CHANGES_v4.md: the block after %r" % label)
    j = k[0] + 3
    while not CHL[j].startswith("```"):
        j += 1
    return "\n".join(CHL[k[0] + 3:j])


before = fenced_after("CHANGES_v3.md text before the correction:")
after = fenced_after("CHANGES_v3.md text after the correction:")
spec4 = (OUT / "spec" / "TABLE_SPEC.md").read_text(encoding="utf-8").split("\n")
h11 = [i + 1 for i, l in enumerate(spec4) if l == "## 11. Version 4 (2026-11-17)"]
print("V4-13: CHANGES_v3.md holds the corrected text (%d lines) that CHANGES_v4.md quotes: %s ; the text before the correction: %s"
      % (after.count("\n") + 1, after in ch3, before in ch3))
print("V4-13: TABLE_SPEC.md heading '## 11. Version 4 (2026-11-17)' at line(s)", h11, "; OUT\\spec\\CHANGES_v4.md exists:", (OUT / "spec" / "CHANGES_v4.md").is_file())
if after not in ch3 or before in ch3 or len(h11) != 1:
    stop("V4-13's bookkeeping")
print("r25: all checks passed")
