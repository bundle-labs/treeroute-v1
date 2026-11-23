# r30 (version 5, step 2b): diff of version 4 (OUT\reconcile\tables_agreed_v4.md) with version 5 (the builders' common
# tables.md, OUT\A\tables.md = OUT\B\tables.md). Read-only; prints; stops on any failure. Built from r25 (version 3 to
# version 4) with only the order, the change list and the version names changed.
#  1. The order's texts are the code spans of the bullets of OUT\_brief\fix_order_v5.md, sections V5-1 to V5-5 (a
#     bullet's wrapped lines joined with one space): each OLD and NEW span ("OLD:", "NEW:") and the sentence that V5-5
#     adds ("add `...`"). V5-5 puts it "after the Version 4 sentence": in version 4's header comment, the one sentence
#     that starts "Version 4 (" and ends with the text that CHANGES_v5.md quotes as that sentence's end, followed by the
#     text that CHANGES_v5.md quotes as the next (the sentence is replaced by itself + " " + the added sentence). Each
#     printed text is also a single-line fenced text of OUT\spec\CHANGES_v5.md.
#  2. Every OLD text is found in version 4 exactly once, in the table, on the kind of line and (for table rows) in the
#     column that the order names. Version 4 with exactly those replacements (positions taken in version 4; no two on
#     a line overlap) must give the builders' version 5 byte for byte, and no OLD text may be left in version 5 outside
#     a NEW text.
#  3. A difflib alignment of the two files must find changed lines exactly where step 2 applied a change (no line
#     added, dropped or moved); every changed line is attributed to its changes of the order. The list is compared with
#     CHANGES_v5.md's list of changed lines.
#  4. Number tokens: on every changed line, no token straddles a replaced span, the tokens outside the replaced spans
#     are the same and in the same order in both versions, and the tokens added and removed are exactly those of the
#     line's NEW and OLD texts; the same over the whole file (every other line is equal, so its tokens are too).
#  5. cells.json: version 5 (A = B) against version 4 (OUT\reconcile\cells_v4.json = both builders' cells_v4.json):
#     bytes, keys, order and values; every entry's printed token found in its cell on its line in both versions, at
#     its version-4 position plus the length change of the replaced texts before it, and outside every replaced span.
#  6. V5-5's second bullet, which changes no line of tables.md, read-only: TABLE_SPEC.md has the heading
#     "## 12. Version 5 (2026-11-17)" once, its contents line holds the v5 text that CHANGES_v5.md quotes (and the v4
#     spec the v4 text), and OUT\spec\CHANGES_v5.md exists. For information only (no stop): the sections of
#     TABLE_SPEC.md (version 5) in which each OLD and NEW text and the added sentence are stated.
import sys, re, json, difflib, hashlib, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]


def stop(msg):
    raise SystemExit("stop: " + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- 1. the order's texts ----------------
order = (OUT / "_brief" / "fix_order_v5.md").read_text(encoding="utf-8").split("\n")
bullets, cur, inb = collections.OrderedDict(), None, False
for l in order:
    m = re.match(r"^## (V5-\d+)\. ", l)
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
IDS = ["V5-%d" % k for k in range(1, 6)]
if list(bullets) != IDS:
    stop("the order's sections are not V5-1 to V5-5: %s" % list(bullets))
SP = {c: [re.findall(r"`([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
WANT = {"V5-1": [2], "V5-2": [2, 2], "V5-3": [2, 2], "V5-4": [2], "V5-5": [1, 1]}
got = {c: [len(x) for x in v] for c, v in SP.items()}
print("order: sections", list(bullets), "; code spans per bullet:", got)
if got != WANT:
    stop("the order's bullets are not as expected")
OLDS = {c: [re.findall(r"\bOLD: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
NEWS = {c: [re.findall(r"\bNEW: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
n_old = sum(len(x) for v in OLDS.values() for x in v)
n_new = sum(len(x) for v in NEWS.values() for x in v)
ch = (OUT / "spec" / "CHANGES_v5.md").read_text(encoding="utf-8")
chs = re.sub(r"\s+", " ", ch)
mm = re.search(r"\((\d+) OLD, (\d+) NEW and the sentence that V5-5 adds;", chs)
print("order: OLD texts", n_old, "; NEW texts", n_new, "; CHANGES_v5.md says", mm.group(1) if mm else None, "OLD and",
      mm.group(2) if mm else None, "NEW, and the sentence that V5-5 adds")
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


b55 = bullets["V5-5"][0]
adds = re.findall(r"\badd `([^`]*)`", b55)
if len(adds) != 1 or "after the Version 4 sentence" not in b55 or OLDS["V5-5"][0] or NEWS["V5-5"][0]:
    stop("V5-5, first bullet: the added sentence")
used.add(("V5-5", 0))
NEWSENT = adds[0]
ma = re.search(r"added directly after the Version 4 sentence \(which ends `([^`]*)`\) and before `([^`]*)`", chs)
if not ma:
    stop("CHANGES_v5.md: the place of the V5-5 sentence")
END4, AFTER4 = ma.group(1), ma.group(2)
print("V5-5: added sentence (order):", NEWSENT)
print("V5-5: the Version 4 sentence ends (CHANGES_v5.md): %r ; followed by: %r" % (END4, AFTER4))
if OLDS["V5-5"][1] or NEWS["V5-5"][1]:
    stop("V5-5 bullet 2 has an OLD or NEW text")
print("V5-5 bullet 2 (no text of tables.md):", bullets["V5-5"][1])

# version 4 and version 5
v4b = (OUT / "reconcile" / "tables_agreed_v4.md").read_bytes()
v5b = (OUT / "A" / "tables.md").read_bytes()
if v5b != (OUT / "B" / "tables.md").read_bytes():
    stop("OUT\\A\\tables.md and OUT\\B\\tables.md differ")
for X in ("A", "B"):
    if (OUT / X / "tables_v4.md").read_bytes() != v4b:
        stop("OUT\\%s\\tables_v4.md differs from tables_agreed_v4.md" % X)
mv4 = re.search(r"\b([0-9a-f]{64})\b, 785 lines, a byte copy of both builders' tables\.md", chs)
print("version 4 (tables_agreed_v4.md = A, B tables_v4.md):", len(v4b), "bytes,", v4b.count(b"\n"), "LF, sha256", sha(v4b),
      "; the SHA-256 that CHANGES_v5.md gives:", bool(mv4) and mv4.group(1) == sha(v4b))
print("version 5 (A = B tables.md):                        ", len(v5b), "bytes,", v5b.count(b"\n"), "LF, sha256", sha(v5b))
if not (mv4 and mv4.group(1) == sha(v4b)):
    stop("version 4 is not the file CHANGES_v5.md names")
s4, s5 = v4b.decode("utf-8"), v5b.decode("utf-8")
L4, L5 = s4.split("\n"), s5.split("\n")

# the anchor of V5-5: the Version 4 sentence of version 4's header comment
k_end = s4.find(END4)
if k_end == -1 or s4.count(END4) != 1 or not s4.startswith(" " + AFTER4, k_end + len(END4)):
    stop("V5-5: the end of the Version 4 sentence is not once in version 4, followed by the quoted text")
k_start = s4.rfind("Version 4 (", 0, k_end)
if k_start < 2 or s4[k_start - 2:k_start] != ". " or ". " in s4[k_start:k_end] or "\n" in s4[k_start:k_end]:
    stop("V5-5: the Version 4 sentence")
ANCHOR = s4[k_start:k_end + len(END4)]
print("V5-5: the Version 4 sentence of version 4 (%d characters, line %d): %s" % (len(ANCHOR), s4[:k_start].count("\n") + 1, ANCHOR))

# (change id, label, OLD, NEW, tables, line prefix, column header (rows only), fit)
C = [
    ("V5-5", "header comment: the Version 5 sentence after the Version 4 sentence", ANCHOR, ANCHOR + " " + NEWSENT, {None},
     "<!-- Draft tables of Supplement S3.13", None, None),
    ("V5-2", "Table 9 caption: coral bleaching's background", *on("V5-2", 0), {"9"}, "**Table 9.** ", None, None),
    ("V5-1", "Table 9 caption: the context-and-calendar family", *on("V5-1", 0), {"9"}, "**Table 9.** ", None, None),
    ("V5-2", "S3.19 note c", *on("V5-2", 1), {"S3.19"}, "ᶜ Background (B2): ", None, None),
    ("V5-4", "S3.21 E3m: what it checks", *on("V5-4", 0), {"S3.21"}, "| E3m | ", "What it checks", "cell"),
    ("V5-3", "S3.21 E5: what it checks", *on("V5-3", 0), {"S3.21"}, "| E5ᵃ | ", "What it checks", "cell"),
    ("V5-3", "S3.21 note a", *on("V5-3", 1), {"S3.21"}, "ᵃ E5 is informational: ", None, None),
]
withtext = {(c, k) for c, bl in bullets.items() for k in range(len(bl)) if OLDS[c][k] or NEWS[c][k]} | {("V5-5", 0)}
print("order: bullets with a text of tables.md", len(withtext), "; used here", len(used), "; not used:", sorted(withtext - used))
if withtext != used:
    stop("an order text is not used")
# CHANGES_v5.md: its single-line fenced texts
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
print("order texts checked against CHANGES_v5.md:", len(texts), "; not a single-line fenced text there:", notin,
      "; CHANGES_v5.md's single-line fenced texts:", len(single))
if notin or len(texts) != 1 + n_old + n_new:
    stop("CHANGES_v5.md")


# ---------------- 2. version 4 + the order's changes ----------------
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


TAB4 = tables_of(L4)
spans = collections.defaultdict(list)   # 0-based line -> [(start, end, NEW, change id, label)]
cols_seen = collections.defaultdict(collections.Counter)
for cid, label, old, new, tabs, prefix, col, fit in C:
    hits = []
    for i, t in enumerate(L4):
        k = t.find(old)
        while k != -1:
            hits.append((i, k))
            k = t.find(old, k + 1)
    if len(hits) != 1 or s4.count(old) != 1:
        stop("%s %s: OLD found %d times in version 4, not once: %r" % (cid, label, len(hits), old[:80]))
    for i, k in hits:
        t = L4[i]
        if TAB4[i] not in tabs or not t.startswith(prefix):
            stop("%s %s: OLD in an unexpected place (line %d, table %s)" % (cid, label, i + 1, TAB4[i]))
        if fit == "line" and t != old:
            stop("%s %s: line %d is not the OLD text alone" % (cid, label, i + 1))
        if fit == "header" and not (t == old and L4[i + 1].startswith("|---") and not L4[i - 1].startswith("|")):
            stop("%s %s: line %d is not a table's header line" % (cid, label, i + 1))
        if col is not None:
            cp, hd = cells_pos(t), header_of(L4, i)
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
E = list(L4)
newspans = {}
for i, sp in spans.items():
    sp.sort()
    for x, y in zip(sp, sp[1:]):
        if x[1] > y[0]:
            stop("two OLD texts overlap on line %d" % (i + 1))
    t, out, p, ns = L4[i], "", 0, []
    for a, b, new, cid, label in sp:
        out += t[p:a]
        ns.append((len(out), len(out) + len(new)))
        out += new
        p = b
    E[i] = out + t[p:]
    newspans[i] = ns
exp = "\n".join(E).encode("utf-8")
print("places replaced:", sum(len(v) for v in spans.values()), "on", len(spans), "lines")
print("version 4 + the order's changes == version 5, byte for byte:", exp == v5b, "; sha256", sha(exp))
if exp != v5b:
    for i, (x, y) in enumerate(zip(E, L5), 1):
        if x != y:
            print("first differing line", i, "\n  expected :", x[:300], "\n  version 5:", y[:300])
            break
    stop("the rebuild differs from version 5")
left = []
for cid, label, old, new, *_ in C[1:]:
    for i, t in enumerate(L5):
        k = t.find(old)
        while k != -1:
            if not any(a <= k and k + len(old) <= b for a, b in newspans.get(i, [])):
                left.append((cid, label, i + 1))
            k = t.find(old, k + 1)
inside_new = sorted({(cid, label) for cid, label, old, new, *_ in C[1:] if old in new})
print("OLD texts left in version 5 outside a NEW text:", left, "; OLD texts that are part of their NEW text:", inside_new)
if left:
    stop("an OLD text is left in version 5")

# ---------------- 3. alignment and attribution ----------------
sm = difflib.SequenceMatcher(None, L4, L5, autojunk=False)
ops, ne4, ne5, moved = [], set(), set(), []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        moved += [(a + 1, b + 1) for a, b in zip(range(i1, i2), range(j1, j2)) if a != b]
        continue
    ops.append((tag, i1 + 1, i2, j1 + 1, j2))
    ne4.update(range(i1 + 1, i2 + 1))
    ne5.update(range(j1 + 1, j2 + 1))
mine = {i + 1 for i in spans}
print("lines: version 4", len(L4) - 1, "+ final LF; version 5", len(L5) - 1, "+ final LF")
print("difflib opcodes other than equal:", len(ops), "; all 'replace' with as many lines on each side, at the same place:",
      all(t == "replace" and i1 == j1 and i2 == j2 for t, i1, i2, j1, j2 in ops))
print("difflib's unequal lines == the lines where a change was applied: version 4", ne4 == mine, "; version 5", ne5 == mine,
      "; unchanged lines that moved:", moved)
if ne4 != mine or ne5 != mine or moved or len(L4) != len(L5) or len(L5) - 1 != 785:
    stop("the alignment does not agree with the rebuild")
pos = [i + 1 for i in range(len(L4)) if L4[i] != L5[i]]
ml = re.search(r"The lines that change \(1-based, (\d+)\): ([\d, ]+)\.", chs)
listed = [int(x) for x in ml.group(2).split(", ")]
print("lines that differ by position:", len(pos), pos)
print("equal to CHANGES_v5.md's list of changed lines (%s):" % ml.group(1), pos == listed)
if pos != listed or int(ml.group(1)) != len(pos):
    stop("CHANGES_v5.md's list of changed lines")
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
    t4, t5 = L4[i], L5[i]
    o_sp = [(a, b) for a, b, _, _, _ in sp]
    n_sp = newspans[i]
    out4, out5, strad = [], [], []
    for m in NUMRE.finditer(t4):
        ins_ = [(a, b) for a, b in o_sp if a < m.end() and m.start() < b]
        if not ins_:
            out4.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v4", m.group(0)))
    for m in NUMRE.finditer(t5):
        ins_ = [(a, b) for a, b in n_sp if a < m.end() and m.start() < b]
        if not ins_:
            out5.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v5", m.group(0)))
    e = collections.Counter()
    for a, b, new, cid, label in sp:
        e.update(toks(new))
        e.subtract(toks(t4[a:b]))
    e = {k: v for k, v in e.items() if v}
    d = collections.Counter(toks(t5))
    d.subtract(toks(t4))
    d = {k: v for k, v in d.items() if v}
    if strad or out4 != out5 or d != e:
        bad.append((i + 1, strad, out4 == out5, d, e))
d_all = collections.Counter(toks(s5))
d_all.subtract(toks(s4))
added = sorted((k, v) for k, v in d_all.items() if v > 0)
removed = sorted((k, -v) for k, v in d_all.items() if v < 0)
e_all = collections.Counter()
for i, sp in spans.items():
    for a, b, new, cid, label in sp:
        e_all.update(toks(new))
        e_all.subtract(toks(L4[i][a:b]))
print("number tokens (regex %s): version 4 %d, version 5 %d" % (NUMRE.pattern, sum(toks(s4).values()), sum(toks(s5).values())))
print("   added:", added, "(%d)" % sum(v for _, v in added))
print("   removed:", removed)
add_by = collections.defaultdict(list)
for i, sp in sorted(spans.items()):
    d = collections.Counter(toks(L5[i]))
    d.subtract(toks(L4[i]))
    for k, v in sorted(d.items()):
        if v:
            add_by[i + 1].append("%s x%d" % (k, v) if v != 1 else k)
print("   added, by line:", dict(add_by))
same_lines = [i for i in range(len(L4)) if i not in spans]
print("per changed line: no straddling token, the tokens outside the replaced spans equal and in order, and the tokens",
      "added/removed == those of the line's NEW/OLD texts:", not bad, bad[:3])
print("unchanged lines (%d): equal, so their tokens are equal and in order:" % len(same_lines), all(L4[i] == L5[i] for i in same_lines))
print("whole file: tokens added/removed == those of the order's texts:", {k: v for k, v in d_all.items() if v} == {k: v for k, v in e_all.items() if v})
if bad or removed or {k: v for k, v in d_all.items() if v} != {k: v for k, v in e_all.items() if v}:
    stop("number tokens")

# ---------------- 5. cells.json ----------------
c4b = (OUT / "reconcile" / "cells_v4.json").read_bytes()
for X in ("A", "B"):
    if (OUT / X / "cells_v4.json").read_bytes() != c4b:
        stop("OUT\\%s\\cells_v4.json differs from OUT\\reconcile\\cells_v4.json" % X)
c5b = (OUT / "A" / "cells.json").read_bytes()
if c5b != (OUT / "B" / "cells.json").read_bytes():
    stop("OUT\\A\\cells.json and OUT\\B\\cells.json differ")
print("cells.json version 4 (reconcile copy = A, B cells_v4.json):", len(c4b), "bytes, sha256", sha(c4b))
print("cells.json version 5 (A = B):                              ", len(c5b), "bytes, sha256", sha(c5b), "; byte-identical to version 4:", c5b == c4b)
D4, D5 = json.loads(c4b.decode("utf-8")), json.loads(c5b.decode("utf-8"))
E4, E5 = D4["entries"], D5["entries"]
print("top level: keys", list(D5), "; tables_file", repr(D5["tables_file"]), "; spec", repr(D5["spec"]), "; equal to version 4:",
      list(D4) == list(D5) and D4["tables_file"] == D5["tables_file"] and D4["spec"] == D5["spec"], "; entries", len(E4), "->", len(E5))
if list(D4) != list(D5) or D4["tables_file"] != D5["tables_file"] or D4["spec"] != D5["spec"] or len(E4) != len(E5):
    stop("cells.json top level")
if c5b.decode("utf-8") != json.dumps(D5, ensure_ascii=False, indent=1, allow_nan=False) + "\n":
    stop("version-5 cells.json is not in the spec's json.dumps form")


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


P4, P5 = locate(L4, E4), locate(L5, E5)
print("entries whose printed token is found in its cell on its line, in reading order: version 4", sum(x is not None for x in P4),
      "; version 5", sum(x is not None for x in P5), "of", len(E5))
if any(x is None for x in P4) or any(x is None for x in P5):
    stop("an entry is not on its line")
SKEY = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)  # noqa: E731
dk, moved_n, off_place, in_span = collections.Counter(), 0, 0, []
for e4, e5, p4, p5 in zip(E4, E5, P4, P5):
    if list(e4) != list(e5):
        stop("key order")
    for kk in e4:
        if SKEY(e4[kk]) != SKEY(e5[kk]):
            dk[kk] += 1
    i = e4["line"] - 1
    shift = sum(len(new) - (b - a) for a, b, new, _, _ in spans.get(i, []) if b <= p4)
    if p5 != p4 + shift:
        off_place += 1
    if p5 != p4:
        moved_n += 1
    if any(a < p4 + len(e4["printed"]) and p4 < b for a, b, _, _, _ in spans.get(i, [])) or \
            any(a < p5 + len(e5["printed"]) and p5 < b for a, b in newspans.get(i, [])):
        in_span.append((e4["line"], e4["printed"]))
on_changed = collections.Counter(e["line"] for e in E5 if (e["line"] - 1) in spans)
rows_on = collections.Counter((e["table"], e["row"], e["column"], e["cell"]) for e in E5 if (e["line"] - 1) in spans)
print("entry keys that differ, version 4 -> 5:", dict(dk))
print("version-5 entries on changed lines:", sum(on_changed.values()), dict(sorted(on_changed.items())), dict(rows_on))
cell_changed = [e["line"] for e in E5 if (e["line"] - 1) in spans and
                not any(ct == e["cell"] for _, ct in cells_of(L4[e["line"] - 1]))]
print("entries on changed lines whose cell is not a version-4 cell of their line:", cell_changed)
print("entries whose token moved on its line:", moved_n, "; not at its version-4 position plus the length change of the replaced",
      "texts before it:", off_place, "; tokens inside a replaced span (OLD or NEW):", in_span)
if dk or off_place or in_span or cell_changed or c5b != c4b:
    stop("cells.json version 4 -> 5")


# ---------------- 6. V5-5's second bullet, outside tables.md ----------------
def fenced_after(label):
    k = [i for i, l in enumerate(CHL) if l.strip() == label]
    if len(k) != 1 or not CHL[k[0] + 2].startswith("```"):
        stop("CHANGES_v5.md: the block after %r" % label)
    j = k[0] + 3
    while not CHL[j].startswith("```"):
        j += 1
    return "\n".join(CHL[k[0] + 3:j])


spec5 = (OUT / "spec" / "TABLE_SPEC.md").read_text(encoding="utf-8").split("\n")
spec4 = (OUT / "spec" / "TABLE_SPEC_v4.md").read_text(encoding="utf-8").split("\n")
c4t, c5t = fenced_after("v4 spec text:"), fenced_after("v5 spec text:")
h12 = [i + 1 for i, l in enumerate(spec5) if l == "## 12. Version 5 (2026-11-17)"]
in5 = [i + 1 for i, l in enumerate(spec5) if c5t in l]
in4 = [i + 1 for i, l in enumerate(spec4) if c4t in l]
print("V5-5: TABLE_SPEC.md heading '## 12. Version 5 (2026-11-17)' at line(s)", h12, "; the contents text that CHANGES_v5.md quotes",
      "for v5 at TABLE_SPEC.md line(s)", in5, "and for v4 at TABLE_SPEC_v4.md line(s)", in4,
      "; OUT\\spec\\CHANGES_v5.md exists:", (OUT / "spec" / "CHANGES_v5.md").is_file())
if len(h12) != 1 or len(in5) != 1 or len(in4) != 1 or in5 != in4:
    stop("V5-5's bookkeeping")
# information: the sections of the version-5 spec that state each text (a section starts at "## <n>. ")
sec, cur = [], None
for l in spec5:
    m = re.match(r"^## (\d+)\. ", l)
    if m:
        cur = int(m.group(1))
    sec.append(cur)
info = []
for cid, label, old, new, *_ in C[1:]:
    so = sorted({sec[i] for i, l in enumerate(spec5) if old in l}, key=lambda x: (x is None, x))
    sn = sorted({sec[i] for i, l in enumerate(spec5) if new in l}, key=lambda x: (x is None, x))
    info.append((cid, label, so, sn))
    print("spec v5 sections stating %s %s: OLD %s ; NEW %s" % (cid, label, so, sn))
sn = sorted({sec[i] for i, l in enumerate(spec5) if NEWSENT in l}, key=lambda x: (x is None, x))
print("spec v5 sections stating V5-5's added sentence:", sn)
rules_ok = all(not [x for x in so if x is not None and x <= 8] and [x for x in sn_ if x is not None and x <= 8] for _, _, so, sn_ in info) \
    and bool([x for x in sn if x is not None and x <= 8])
print("information: sections 0 to 8 of the version-5 spec state every NEW text and the added sentence, and no OLD text:", rules_ok)
print("r30: all checks passed")
