# r20 (version 3, step 2b): diff of version 2 (OUT\reconcile\tables_agreed_v2.md) with version 3 (the builders' common
# tables.md, OUT\A\tables.md = OUT\B\tables.md). Read-only; prints; stops on any failure.
#  1. The order's texts are the code spans of the bullets of OUT\_brief\fix_order_v3.md, sections V3-1 to V3-7 (a
#     bullet's wrapped lines joined with one space): each OLD and NEW span ("OLD:", "OLD row label:", "NEW:"), and the
#     anchor of the one inserted sentence ("directly after `...`"). A span that starts with "..." stands for the text
#     after the dots (the order: the text before is unchanged). Each printed text is also a single-line fenced text of
#     OUT\spec\CHANGES_v3.md, except the pair-label words M and P of V3-6, which CHANGES_v3.md shows in a composed
#     example; that example must be M -> P.
#  2. Every OLD text is found in version 2 exactly as often as the order says, each place in the table, on the kind of
#     line and (for table rows) in the column the order names. Version 2 with exactly those replacements (positions
#     taken in version 2; no two on a line overlap) must give the builders' version 3 byte for byte.
#  3. A difflib alignment of the two files must find changed lines exactly where step 2 applied a change (no line
#     added, dropped or moved); every changed line is attributed to its changes of the order. The list is compared with
#     CHANGES_v3.md's list of changed lines.
#  4. Number tokens: on every changed line, no token straddles a replaced span, the tokens outside the replaced spans
#     are the same and in the same order in both versions, and the tokens added and removed are exactly those of the
#     line's NEW and OLD texts; the same over the whole file.
#  5. cells.json: version 3 (A = B) entry by entry against version 2 (OUT\reconcile\cells_v2.json = both builders'
#     cells_v2.json): keys, order and values; every entry's printed token found in its cell on its line in both
#     versions, at its version-2 position plus the length change of the replaced texts before it, and outside every
#     replaced span.
import sys, re, json, difflib, hashlib, collections
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parents[2]
AW3T = ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27")


def stop(msg):
    raise SystemExit("stop: " + msg)


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------- 1. the order's texts ----------------
order = (OUT / "_brief" / "fix_order_v3.md").read_text(encoding="utf-8").split("\n")
bullets, cur, inb = collections.OrderedDict(), None, False
for l in order:
    m = re.match(r"^## (V3-\d)\. ", l)
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
SP = {c: [re.findall(r"`([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
WANT = {"V3-1": [2, 2, 2, 2, 5, 3, 2, 0], "V3-2": [2, 2, 2, 2, 2], "V3-3": [2, 3], "V3-4": [2], "V3-5": [2],
        "V3-6": [3, 2, 2, 3, 2, 2, 2, 2, 2, 5], "V3-7": [2, 2, 3, 3, 1]}
got = {c: [len(x) for x in v] for c, v in SP.items()}
print("order: sections", list(bullets), "; code spans per bullet:", got)
if got != WANT:
    stop("the order's bullets are not as expected")
OLDS = {c: [re.findall(r"\bOLD(?: row label)?: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
NEWS = {c: [re.findall(r"\bNEW: `([^`]*)`", b) for b in bl] for c, bl in bullets.items()}
n_old = sum(len(x) for v in OLDS.values() for x in v)
n_new = sum(len(x) for v in NEWS.values() for x in v)
ch = (OUT / "spec" / "CHANGES_v3.md").read_text(encoding="utf-8")
chs = re.sub(r"\s+", " ", ch)
mm = re.search(r"\((\d+) OLD, (\d+) NEW,", chs)
print("order: OLD texts", n_old, "; NEW texts", n_new, "; CHANGES_v3.md says", mm.group(1), "OLD and", mm.group(2), "NEW")
if (n_old, n_new) != (int(mm.group(1)), int(mm.group(2))):
    stop("the number of OLD and NEW texts")
used = set()


def on(c, k):
    """the OLD and NEW texts of bullet k (0-based) of section c, a '...' head removed"""
    o, n = OLDS[c][k], NEWS[c][k]
    if len(o) != 1 or len(n) != 1:
        stop("%s bullet %d: not one OLD and one NEW" % (c, k + 1))
    used.add((c, k))
    o, n = o[0], n[0]
    if o.startswith("...") or n.startswith("..."):
        if not (o.startswith("...") and n.startswith("...")):
            stop("%s bullet %d: only one of OLD and NEW starts with '...'" % (c, k + 1))
        o, n = o[3:], n[3:]
    return o, n


ins = re.findall(r"directly after `([^`]*)`", bullets["V3-1"][0])
if len(ins) != 1 or OLDS["V3-1"][0] or len(NEWS["V3-1"][0]) != 1:
    stop("V3-1, first bullet: the inserted sentence")
used.add(("V3-1", 0))
ANCHOR, NEWSENT = ins[0], NEWS["V3-1"][0][0]
# (change id, label, OLD, NEW, places in version 2, tables, line prefix, column header (rows only), fit in the cell)
C = [
    ("V3-7", "header comment: version sentences", *on("V3-7", 0), 1, {None}, "<!-- Draft tables of Supplement S3.13", None, None),
    ("V3-7", "header comment: data numbers", *on("V3-7", 1), 1, {None}, "<!-- Draft tables of Supplement S3.13", None, None),
    ("V3-1", "Table 9 caption: new importance sentence", ANCHOR, ANCHOR + " " + NEWSENT, 1, {"9"}, "**Table 9.** ", None, None),
    ("V3-1", "Table 9 caption: RBO consensus", *on("V3-1", 1), 1, {"9"}, "**Table 9.** ", None, None),
    ("V3-1", "Table 9 caption: own-history share", *on("V3-1", 2), 1, {"9"}, "**Table 9.** ", None, None),
    ("V3-1", "S3.19 caption: J", *on("V3-1", 3), 1, {"S3.19"}, "**Table S3.19 (post hoc).** ", None, None),
    ("V3-1", "S3.23, S3.24, S3.26 captions: shares sentence (d, e)", *on("V3-1", 4), 3, {"S3.23", "S3.24", "S3.26"}, "**Table S3.2", None, None),
    ("V3-1", "S3.25, S3.27 captions: shares sentence (d, e, g)", *on("V3-1", 5), 2, {"S3.25", "S3.27"}, "**Table S3.2", None, None),
    ("V3-1", "S3.29 caption", *on("V3-1", 6), 1, {"S3.29"}, "**Table S3.29 (post hoc; sensitivity).** ", None, None),
    ("V3-2", "S3.18 caption", *on("V3-2", 0), 1, {"S3.18"}, "**Table S3.18 (post hoc).** ", None, None),
    ("V3-2", "S3.18 panel b label", *on("V3-2", 1), 1, {"S3.18"}, "**b. ", None, None),
    ("V3-2", "S3.18 b baselines row", *on("V3-2", 2), 1, {"S3.18"}, "| All five | ", None, None),
    ("V3-2", "S3.18 first note line", *on("V3-2", 3), 1, {"S3.18"}, "Panel b lists ", None, None),
    ("V3-2", "S3.18 caption's source comment", *on("V3-2", 4), 1, {"S3.18"}, "**Table S3.18 (post hoc).** ", None, None),
    ("V3-3", "S3.23-S3.27 captions: count clause", *on("V3-3", 0), 5, set(AW3T), "**Table S3.2", None, None),
    ("V3-3", "S3.24 source comment ({extra_src})", *on("V3-3", 1), 1, {"S3.24"}, "**Table S3.24 (post hoc).** ", None, None),
    ("V3-4", "S3.24 note double dagger, second sentence", *on("V3-4", 0), 1, {"S3.24"}, "‡ BARDL reads three variables ", None, None),
    ("V3-5", "S3.22 row label", *on("V3-5", 0), 1, {"S3.22"}, "| ", "Quantity", "cell"),
    ("V3-6", "treeroute v1 skill-guard cell (S3.18 a, S3.20)", *on("V3-6", 0), 10, {"S3.18", "S3.20"}, "| ", "Skill guard", "cell"),
    ("V3-6", "S3.21 first row label", *on("V3-6", 1), 1, {"S3.21"}, "| ", "Gate", "cell"),
    ("V3-6", "random forest's method (S3.18 a)", *on("V3-6", 2), 5, {"S3.18"}, "| ", "Model and SHAP method", "head"),
    ("V3-6", "S3.19 note c", *on("V3-6", 3), 1, {"S3.19"}, "ᶜ Background (B2): ", None, None),
    ("V3-6", "S3.21 E10, what it checks", *on("V3-6", 4), 1, {"S3.21"}, "| E10 | ", "What it checks", "tail"),
    ("V3-6", "S3.25 Link cells (M -> P)", *on("V3-6", 5), 8, {"S3.25"}, "| ", "Link", "in"),
    ("V3-6", "S3.21 E3a, what it checks", *on("V3-6", 6), 1, {"S3.21"}, "| E3a | ", "What it checks", "cell"),
    ("V3-6", "S3.21 E3m, what it checks", *on("V3-6", 7), 1, {"S3.21"}, "| E3m | ", "What it checks", "cell"),
    ("V3-6", "S3.21 E3, what it checks", *on("V3-6", 8), 1, {"S3.21"}, "| E3 | ", "What it checks", "cell"),
    ("V3-6", "S3.21 E6, what it checks", *on("V3-6", 9), 1, {"S3.21"}, "| E6 | ", "What it checks", "cell"),
]
withtext = {(c, k) for c, bl in bullets.items() for k in range(len(bl)) if OLDS[c][k] or NEWS[c][k]}
print("order: bullets with an OLD or NEW text", len(withtext), "; used here", len(used), "; not used:", sorted(withtext - used))
if withtext != used:
    stop("an order text is not used")
M, P = on("V3-6", 5)
# CHANGES_v3.md: its single-line fenced texts
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
texts = [NEWSENT] + [t for c in C if c[1] not in ("Table 9 caption: new importance sentence", "S3.25 Link cells (M -> P)") for t in c[2:4]]
notin = [t for t in texts if t not in single]
exo = [s for s in single if s.endswith("; raw model, declined by its guard: Ridge")]
exn = [s for s in single if s.endswith("; raw model, declined by its skill guard: Ridge")]
link_ok = len(exo) == 1 and len(exn) == 1 and exo[0].count(M) == 1 and exo[0].replace(M, P) == exn[0]
print("order texts checked against CHANGES_v3.md:", len(texts), "; not a single-line fenced text there:", notin,
      "; CHANGES_v3.md's Link example is OLD -> NEW with M -> P:", link_ok)
if notin or not link_ok:
    stop("CHANGES_v3.md")

# ---------------- 2. version 2 + the order's changes ----------------
v2b = (OUT / "reconcile" / "tables_agreed_v2.md").read_bytes()
v3b = (OUT / "A" / "tables.md").read_bytes()
if v3b != (OUT / "B" / "tables.md").read_bytes():
    stop("OUT\\A\\tables.md and OUT\\B\\tables.md differ")
for X in ("A", "B"):
    if (OUT / X / "tables_v2.md").read_bytes() != v2b:
        stop("OUT\\%s\\tables_v2.md differs from tables_agreed_v2.md" % X)
print("version 2 (tables_agreed_v2.md = A, B tables_v2.md):", len(v2b), "bytes,", v2b.count(b"\n"), "LF, sha256", sha(v2b))
print("version 3 (A = B tables.md):                        ", len(v3b), "bytes,", v3b.count(b"\n"), "LF, sha256", sha(v3b))
s2, s3 = v2b.decode("utf-8"), v3b.decode("utf-8")
L2, L3 = s2.split("\n"), s3.split("\n")


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


TAB2 = tables_of(L2)
spans = collections.defaultdict(list)   # 0-based line -> [(start, end, NEW, change id, label)]
cols_seen = collections.defaultdict(collections.Counter)
for cid, label, old, new, n, tabs, prefix, col, fit in C:
    hits = []
    for i, t in enumerate(L2):
        k = t.find(old)
        while k != -1:
            hits.append((i, k))
            k = t.find(old, k + 1)
    if len(hits) != n or s2.count(old) != n:
        stop("%s %s: OLD found %d times in version 2, not %d: %r" % (cid, label, len(hits), n, old[:80]))
    for i, k in hits:
        t = L2[i]
        if TAB2[i] not in tabs or not t.startswith(prefix):
            stop("%s %s: OLD in an unexpected place (line %d, table %s)" % (cid, label, i + 1, TAB2[i]))
        if col is not None:
            cp, hd = cells_pos(t), header_of(L2, i)
            inside = [j for j, (a, b, c) in enumerate(cp) if a <= k and k + len(old) <= b]
            if len(inside) != 1 or hd is None or len(hd) != len(cp):
                stop("%s %s: line %d, the cell of OLD" % (cid, label, i + 1))
            j = inside[0]
            a, b, c = cp[j]
            okfit = {"cell": c == old, "head": c.startswith(old) and k == a, "tail": c.endswith(old) and k + len(old) == b, "in": True}[fit]
            if not hd[j].startswith(col) or not okfit:
                stop("%s %s: line %d, column %r, fit %s" % (cid, label, i + 1, hd[j], fit))
            cols_seen[label][hd[j]] += 1
        spans[i].append((k, k + len(old), new, cid, label))
print("columns of the row changes (header: places):", {k: dict(v) for k, v in cols_seen.items()})
E = list(L2)
newspans = {}
for i, sp in spans.items():
    sp.sort()
    for x, y in zip(sp, sp[1:]):
        if x[1] > y[0]:
            stop("two OLD texts overlap on line %d" % (i + 1))
    t, out, p, ns = L2[i], "", 0, []
    for a, b, new, cid, label in sp:
        out += t[p:a]
        ns.append((len(out), len(out) + len(new)))
        out += new
        p = b
    E[i] = out + t[p:]
    newspans[i] = ns
exp = "\n".join(E).encode("utf-8")
print("places replaced:", sum(len(v) for v in spans.values()), "on", len(spans), "lines")
print("version 2 + the order's changes == version 3, byte for byte:", exp == v3b, "; sha256", sha(exp))
if exp != v3b:
    for i, (x, y) in enumerate(zip(E, L3), 1):
        if x != y:
            print("first differing line", i, "\n  expected :", x[:300], "\n  version 3:", y[:300])
            break
    stop("the rebuild differs from version 3")

# ---------------- 3. alignment and attribution ----------------
sm = difflib.SequenceMatcher(None, L2, L3, autojunk=False)
ops, ne2, ne3, moved = [], set(), set(), []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        moved += [(a + 1, b + 1) for a, b in zip(range(i1, i2), range(j1, j2)) if a != b]
        continue
    ops.append((tag, i1 + 1, i2, j1 + 1, j2))
    ne2.update(range(i1 + 1, i2 + 1))
    ne3.update(range(j1 + 1, j2 + 1))
mine = {i + 1 for i in spans}
print("lines: version 2", len(L2) - 1, "+ final LF; version 3", len(L3) - 1, "+ final LF")
print("difflib opcodes other than equal:", len(ops), "; all 'replace' with as many lines on each side, at the same place:",
      all(t == "replace" and i1 == j1 and i2 == j2 for t, i1, i2, j1, j2 in ops))
print("difflib's unequal lines == the lines where a change was applied: version 2", ne2 == mine, "; version 3", ne3 == mine,
      "; unchanged lines that moved:", moved)
if ne2 != mine or ne3 != mine or moved or len(L2) != len(L3):
    stop("the alignment does not agree with the rebuild")
pos = [i + 1 for i in range(len(L2)) if L2[i] != L3[i]]
ml = re.search(r"The lines that change \(1-based, (\d+)\): ([\d, ]+)\.", chs)
listed = [int(x) for x in ml.group(2).split(", ")]
print("lines that differ by position:", len(pos), pos)
print("equal to CHANGES_v3.md's list of changed lines (%s):" % ml.group(1), pos == listed)
if pos != listed or int(ml.group(1)) != len(pos):
    stop("CHANGES_v3.md's list of changed lines")
by = collections.OrderedDict((c, collections.OrderedDict()) for c in ["V3-1", "V3-2", "V3-3", "V3-4", "V3-5", "V3-6", "V3-7"])
for i in sorted(spans):
    for a, b, new, cid, label in spans[i]:
        by[cid].setdefault(label, []).append(i + 1)
multi = {i + 1: sorted({x[3] for x in sp}) for i, sp in spans.items() if len({x[3] for x in sp}) > 1}
for cid, d in by.items():
    lines = sorted({x for v in d.values() for x in v})
    print("%s: %d places on %d lines: %s" % (cid, sum(len(v) for v in d.values()), len(lines), ", ".join(map(str, lines))))
    for label, v in d.items():
        print("     %-55s %s" % (label, v))
print("lines carrying more than one change id:", multi)

# ---------------- 4. number tokens ----------------
NUMRE = re.compile("[−-]?\\d+(?:[.,]\\d+)*%?|[⁰¹²³⁴-⁹⁻]+")


def toks(s):
    return collections.Counter(NUMRE.findall(s))


bad = []
for i, sp in spans.items():
    t2, t3 = L2[i], L3[i]
    o_sp = [(a, b) for a, b, _, _, _ in sp]
    n_sp = newspans[i]
    out2, out3, strad = [], [], []
    for m in NUMRE.finditer(t2):
        ins_ = [(a, b) for a, b in o_sp if a < m.end() and m.start() < b]
        if not ins_:
            out2.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v2", m.group(0)))
    for m in NUMRE.finditer(t3):
        ins_ = [(a, b) for a, b in n_sp if a < m.end() and m.start() < b]
        if not ins_:
            out3.append(m.group(0))
        elif not all(a <= m.start() and m.end() <= b for a, b in ins_):
            strad.append(("v3", m.group(0)))
    e = collections.Counter()
    for a, b, new, cid, label in sp:
        e.update(toks(new))
        e.subtract(toks(t2[a:b]))
    e = {k: v for k, v in e.items() if v}
    d = collections.Counter(toks(t3))
    d.subtract(toks(t2))
    d = {k: v for k, v in d.items() if v}
    if strad or out2 != out3 or d != e:
        bad.append((i + 1, strad, out2 == out3, d, e))
d_all = collections.Counter(toks(s3))
d_all.subtract(toks(s2))
added = sorted((k, v) for k, v in d_all.items() if v > 0)
removed = sorted((k, -v) for k, v in d_all.items() if v < 0)
e_all = collections.Counter()
for i, sp in spans.items():
    for a, b, new, cid, label in sp:
        e_all.update(toks(new))
        e_all.subtract(toks(L2[i][a:b]))
print("number tokens (regex %s): version 2 %d, version 3 %d" % (NUMRE.pattern, sum(toks(s2).values()), sum(toks(s3).values())))
print("   added:", added, "(%d)" % sum(v for _, v in added))
print("   removed:", removed)
add_by = collections.defaultdict(list)
for i, sp in sorted(spans.items()):
    d = collections.Counter(toks(L3[i]))
    d.subtract(toks(L2[i]))
    for k, v in sorted(d.items()):
        if v:
            add_by[i + 1].append("%s x%d" % (k, v) if v != 1 else k)
print("   added, by line:", dict(add_by))
print("per changed line: no straddling token, the tokens outside the replaced spans equal and in order, and the tokens",
      "added/removed == those of the line's NEW/OLD texts:", not bad, bad[:3])
print("whole file: tokens added/removed == those of the order's texts:", {k: v for k, v in d_all.items() if v} == {k: v for k, v in e_all.items() if v})
if bad or removed or {k: v for k, v in d_all.items() if v} != {k: v for k, v in e_all.items() if v}:
    stop("number tokens")

# ---------------- 5. cells.json ----------------
c2b = (OUT / "reconcile" / "cells_v2.json").read_bytes()
for X in ("A", "B"):
    if (OUT / X / "cells_v2.json").read_bytes() != c2b:
        stop("OUT\\%s\\cells_v2.json differs from OUT\\reconcile\\cells_v2.json" % X)
c3b = (OUT / "A" / "cells.json").read_bytes()
if c3b != (OUT / "B" / "cells.json").read_bytes():
    stop("OUT\\A\\cells.json and OUT\\B\\cells.json differ")
print("cells.json version 2 (reconcile copy = A, B cells_v2.json):", len(c2b), "bytes, sha256", sha(c2b))
print("cells.json version 3 (A = B):                              ", len(c3b), "bytes, sha256", sha(c3b))
D2, D3 = json.loads(c2b.decode("utf-8")), json.loads(c3b.decode("utf-8"))
E2, E3 = D2["entries"], D3["entries"]
print("top level: keys", list(D3), "; tables_file", repr(D3["tables_file"]), "; spec", repr(D3["spec"]), "; equal to version 2:",
      list(D2) == list(D3) and D2["tables_file"] == D3["tables_file"] and D2["spec"] == D3["spec"], "; entries", len(E2), "->", len(E3))
if list(D2) != list(D3) or D2["tables_file"] != D3["tables_file"] or D2["spec"] != D3["spec"] or len(E2) != len(E3):
    stop("cells.json top level")
for D_, b_ in ((D3, c3b),):
    if b_.decode("utf-8") != json.dumps(D_, ensure_ascii=False, indent=1, allow_nan=False) + "\n":
        stop("version-3 cells.json is not in the spec's json.dumps form")


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


P2, P3 = locate(L2, E2), locate(L3, E3)
print("entries whose printed token is found in its cell on its line, in reading order: version 2", sum(x is not None for x in P2),
      "; version 3", sum(x is not None for x in P3), "of", len(E3))
if any(x is None for x in P2) or any(x is None for x in P3):
    stop("an entry is not on its line")
SKEY = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)  # noqa: E731
dk, wh, moved_n, off_place, in_span = collections.Counter(), collections.defaultdict(collections.Counter), 0, 0, []
for e2, e3, p2, p3 in zip(E2, E3, P2, P3):
    if list(e2) != list(e3):
        stop("key order")
    for kk in e2:
        if SKEY(e2[kk]) != SKEY(e3[kk]):
            dk[kk] += 1
            wh[kk][(e2["table"], e2["panel"], e2["row"], "line %d" % e2["line"])] += 1
    i = e2["line"] - 1
    shift = sum(len(new) - (b - a) for a, b, new, _, _ in spans.get(i, []) if b <= p2)
    if p3 != p2 + shift:
        off_place += 1
    if p3 != p2:
        moved_n += 1
    if any(a < p2 + len(e2["printed"]) and p2 < b for a, b, _, _, _ in spans.get(i, [])) or \
            any(a < p3 + len(e3["printed"]) and p3 < b for a, b in newspans.get(i, [])):
        in_span.append((e2["line"], e2["printed"]))
print("entry keys that differ, version 2 -> 3:", dict(dk))
for kk, cnt in wh.items():
    print("     ", kk, dict(sorted(cnt.items())))
c344 = [e for e in E3 if e["line"] == 344]
print("line 344 entries:", len(c344), "; their version-3 cell is the whole version-3 line 344:", all(e["cell"] == L3[343] for e in c344),
      "; version-2 cell the whole version-2 line 344:", all(e["cell"] == L2[343] for e in E2 if e["line"] == 344))
on_changed = collections.Counter(e["line"] for e in E3 if (e["line"] - 1) in spans)
print("version-3 entries on changed lines:", sum(on_changed.values()), dict(sorted(on_changed.items())))
print("entries whose token moved on its line:", moved_n, "; not at its version-2 position plus the length change of the replaced",
      "texts before it:", off_place, "; tokens inside a replaced span (OLD or NEW):", in_span)
same = all(SKEY(e2[kk]) == SKEY(e3[kk]) for e2, e3 in zip(E2, E3) for kk in e2 if kk != "cell")
cell_only344 = set(wh.get("cell", {}).keys()) <= {k for k in wh.get("cell", {}) if k[3] == "line 344"}
print("every key but cell equal on every entry:", same, "; cell differs only on line 344:", cell_only344 and dk.get("cell", 0) == len(c344))
if not same or not cell_only344 or dk.get("cell", 0) != len(c344) or off_place or in_span:
    stop("cells.json version 2 -> 3")
print("r20: all checks passed")
