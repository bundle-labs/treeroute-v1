# Skeptic (version 5 check, item 1): is each change V5-1 to V5-5 closed in tables_agreed.md and in the spec?
# Written independently of the spec fixer's and the reconciler's scripts (adapted from k30). Read-only; prints only.
#  - every OLD/NEW pair of the change order (parsed from fix_order_v5.md; wrapped lines joined by one space): OLD in
#    version 4 of the tables, gone from version 5 (outside its NEW), NEW at the expected lines of version 5; in the
#    spec, NEW present in sections 0-8 and OLD present only in the records (sections 9-12) or inside its NEW;
#  - the spec's fixed texts instantiated: the header comment block (line 1), the Table 9 caption block (line 5), the
#    S3.19 note c line (line 83), the S3.21 note a line (line 146), and the constant "What it checks" cells of the
#    S3.21 rows E3m and E5 (lines 135, 138) equal the printed lines and cells;
#  - the spec diff version 4 -> version 5 (difflib): every changed line inside a place that CHANGES_v5.md lists;
#    fenced blocks counted; the blocks whose content changed and their first lines;
#  - V5-5: the header comment sentence, CHANGES_v5.md (its hashes against the files), spec section 12 and the
#    contents line; the older copies of the spec and of the tables intact (hashes as CHANGES_v5.md and the
#    reconciler state them);
#  - paraphrases of the OLD claims left anywhere in tables v5 or in spec sections 0-8.
import difflib, hashlib, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
rd = lambda *p: open(os.path.join(OUT, *p), encoding="utf-8", newline="").read()
T4, T5 = rd("reconcile", "tables_agreed_v4.md"), rd("reconcile", "tables_agreed.md")
S4, S5 = rd("spec", "TABLE_SPEC_v4.md"), rd("spec", "TABLE_SPEC.md")
L4, L5 = T4[:-1].split("\n"), T5[:-1].split("\n")
S4L, S5L = S4[:-1].split("\n"), S5[:-1].split("\n")
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
fsha = lambda *p: hashlib.sha256(open(os.path.join(OUT, *p), "rb").read()).hexdigest()
print("tables v4 %s %d lines | v5 %s %d lines" % (sha(T4), len(L4), sha(T5), len(L5)))
print("spec v4 %s %d lines | v5 %s %d lines" % (sha(S4), len(S4L), sha(S5), len(S5L)))
sec = {n: next((i + 1 for i, x in enumerate(S5L) if x.startswith("## %d." % n)), None) for n in range(0, 13)}
print("spec v5 section heading lines:", sec)


def secname(k):
    s = max([n for n, v in sec.items() if v is not None and v <= k] or [-1])
    return "S%d" % s


order = rd("_brief", "fix_order_v5.md").split("\n")
blocks, ids, cur, curid, hdr = [], [], None, None, None
for ln in order:
    m = re.match(r"## (V5-\d+)\.", ln)
    if m:
        hdr = m.group(1)
    elif ln.startswith("## "):
        hdr = None
    if ln.startswith("- "):
        if cur is not None:
            blocks.append(cur)
            ids.append(curid)
        cur, curid = ln[2:], hdr
    elif ln.startswith("  ") and cur is not None:
        cur += " " + ln[2:]
    else:
        if cur is not None:
            blocks.append(cur)
            ids.append(curid)
        cur = None
if cur is not None:
    blocks.append(cur)
    ids.append(curid)
pairs, ins = [], None
for b, i in zip(blocks, ids):
    if i is None:
        continue
    for m in re.finditer(r"OLD: `([^`]+)`\s+NEW: `([^`]+)`", b):
        pairs.append((i, m.group(1), m.group(2)))
    m = re.search(r"after the Version 4 sentence, add `([^`]+)`", b)
    if m:
        ins = m.group(1)
print("order: %d OLD/NEW pairs %s + the V5-5 sentence (%s)" % (len(pairs), [p[0] for p in pairs], ins is not None))


def where(txt, L):
    return [k + 1 for k, x in enumerate(L) if txt in x]


def old_outside_new(o, n, L):
    res = []
    for k, x in enumerate(L):
        y = x.replace(n, "\0") if n else x
        if o in y:
            res.append(k + 1)
    return res


for i, o, n in pairs:
    print("%-5s OLD %r" % (i, o[:70]))
    print("      tables v4: OLD on %s, NEW on %s | tables v5: NEW on %s, OLD (outside NEW) on %s" % (
        where(o, L4), where(n, L4), where(n, L5), old_outside_new(o, n, L5)))
    print("      spec v4: OLD at %s | spec v5: NEW at %s, OLD (outside NEW) at %s" % (
        ["L%d(%s)" % (k, secname(k)) for k in where(o, S4L)][:6],
        ["L%d(%s)" % (k, secname(k)) for k in where(n, S5L)][:6],
        ["L%d(%s)" % (k, secname(k)) for k in old_outside_new(o, n, S5L)][:6]))
v4s = re.search(r"Version 4 \(2026-11-17, after the third check\).*?CHANGES_v4\.md lists; no number changed\.", L4[0]).group(0)
print("V5-5: the Version 4 sentence occurs %d time(s) in v4 line 1 (%d chars)" % (L4[0].count(v4s), len(v4s)))
print("      v5 line 1 == v4 line 1 with ' ' + sentence after it: %s | sentence followed by ' Built from': %s | count in v5 %d, in v4 %d | spec v5 lines %s" % (
    L4[0].replace(v4s, v4s + " " + ins, 1) == L5[0], (ins + " Built from the stored values") in L5[0], T5.count(ins), T4.count(ins),
    ["L%d(%s)" % (k, secname(k)) for k in where(ins, S5L)]))

# fenced blocks of the spec, and their instantiation in tables v5
fence = lambda L: [k + 1 for k, x in enumerate(L) if x.startswith("```")]
f4, f5 = fence(S4L), fence(S5L)
blk = lambda L, f, b: L[f[2 * b]:f[2 * b + 1] - 1]
print("fenced blocks: v4 %d, v5 %d; fence lines equal: %s" % (len(f4) // 2, len(f5) // 2, f4 == f5))
chg = []
for b in range(len(f5) // 2):
    c4, c5 = blk(S4L, f4, b), blk(S5L, f5, b)
    if c4 != c5:
        chg.append(b + 1)
        print("   block %2d (fence L%d) changed: %d -> %d lines; first line same 24-char start: %s; changed lines in block: %s" % (
            b + 1, f5[2 * b], len(c4), len(c5), c4[0][:24] == c5[0][:24], [j + 1 for j, (x, y) in enumerate(zip(c4, c5)) if x != y]))
print("   blocks whose content changed:", chg)
b4, b8, b19, b26 = (blk(S5L, f5, b - 1) for b in (4, 8, 19, 26))
print("   block 4 == tables v5 line 1: %s | block 8 == line 5: %s | block 19 line 3 == line 83: %s | block 26 line 1 == line 146: %s" % (
    b4 == [L5[0]], b8 == [L5[4]], b19[2] == L5[82], b26[0] == L5[145]))
print("   block 19 lines 1-4 == tables v5 lines 81-84: %s | block 26 == lines 146-147: %s" % (b19 == L5[80:84], b26 == L5[145:147]))
spec_rows = {}
for x in S5L:
    m = re.match(r"\| `(E3m|E5ᵃ)` \| `([^`]+)` \| (.*) \|$", x)
    if m:
        spec_rows[m.group(1)] = (m.group(2), m.group(3))
for g, ln in [("E3m", 135), ("E5ᵃ", 138)]:
    cs = L5[ln - 1][2:-2].split(" | ")
    print("   S3.21 %-4s spec 'What it checks' == printed cell (line %d): %s | gate cell %r | problem cells %s" % (
        g, ln, spec_rows.get(g, ("",))[0] == cs[1], cs[0], cs[2:]))
print("   E5 spec problem cell rule: %r" % spec_rows.get("E5ᵃ", ("", ""))[1])

# spec diff v4 -> v5
listed = {15, 309, 417, 580, 679, 682, 693} | set(range(1424, 1477))
sm = difflib.SequenceMatcher(a=S4L, b=S5L, autojunk=False)
outside, kinds = [], []
for t, a1, a2, b1, b2 in sm.get_opcodes():
    if t == "equal":
        continue
    kinds.append((t, a1 + 1, a2, b1 + 1, b2))
    if t == "delete":
        outside.append(("deleted v4 lines %d-%d" % (a1 + 1, a2), S4L[a1][:60]))
    for k in range(b1 + 1, b2 + 1):
        if k not in listed:
            outside.append((k, S5L[k - 1][:80]))
print("spec diff opcodes:", kinds)
print("   changed v5 lines outside the listed places: %d %s" % (len(outside), outside[:6]))
same_numbering = all(S4L[k] == S5L[k] or (k + 1) in listed for k in range(len(S4L)))
print("   v5 lines 1-%d equal v4 lines 1-%d except the listed lines: %s | v5 adds lines %d-%d: %s" % (
    len(S4L), len(S4L), same_numbering, len(S4L) + 1, len(S5L), len(S5L) - len(S4L)))
print("   changed lines of sections 0-11:", [k + 1 for k in range(len(S4L)) if S4L[k] != S5L[k]])
print("   v5 L1424-1427:", [S5L[k][:60] for k in range(1423, 1427)], "| v4 last line:", repr(S4L[-1][:60]))
print("   section 12 heading:", sec.get(12), repr(S5L[sec[12] - 1]) if sec.get(12) else None, "| count of '## 12.':",
      sum(1 for x in S5L if x.startswith("## 12.")))
print("   contents line (L15) ends:", repr(S5L[14][-80:]))

# CHANGES_v5.md: exists, its stated hashes
CH = rd("spec", "CHANGES_v5.md")
print("CHANGES_v5.md: %d bytes, %d lines, sha %s" % (len(CH.encode("utf-8")), len(CH[:-1].split("\n")), sha(CH)))
for label, h in [("spec v5", sha(S5)), ("spec v4", sha(S4)), ("tables v4", sha(T4))]:
    print("   full %s hash %s... stated in CHANGES_v5.md: %s" % (label, h[:12], h in CH))
for name, pre, suf in [("TABLE_SPEC_v1.md", "979be5ed", "7cf9fb"), ("TABLE_SPEC_v2.md", "2046c58a", "ad30f02"),
                       ("TABLE_SPEC_v3.md", "573cc04e", "ead8da31")]:
    h = fsha("spec", name)
    print("   %s %s...%s; matches CHANGES_v5.md's %s...%s: %s" % (name, h[:8], h[-8:], pre, suf, h.startswith(pre) and h.endswith(suf)))
for name, pre, suf in [("tables_agreed_v1.md", "5f414a11", "beae03"), ("tables_agreed_v2.md", "a7710171", "6570c9"),
                       ("tables_agreed_v3.md", "86f7eb2a", "5919d7"), ("tables_agreed_v4.md", "f3d55546", "a688d9"),
                       ("cells_v2.json", "735b7278", "54980e"), ("cells_v3.json", "3c2ac02d", "f7fa10"),
                       ("cells_v4.json", "3c2ac02d", "f7fa10"), ("cells.json", "3c2ac02d", "f7fa10"),
                       ("tables_agreed.md", "d05a6856", "b467c")]:
    h = fsha("reconcile", name)
    print("   reconcile %-20s %s...%s; as stated (%s...%s): %s" % (name, h[:8], h[-6:], pre, suf, h.startswith(pre) and h.endswith(suf)))
for who in ["A", "B"]:
    print("   %s: tables.md == tables_agreed.md: %s | cells.json == reconcile cells.json: %s | tables_v4.md == tables_agreed_v4.md: %s" % (
        who, fsha(who, "tables.md") == fsha("reconcile", "tables_agreed.md"), fsha(who, "cells.json") == fsha("reconcile", "cells.json"),
        fsha(who, "tables_v4.md") == fsha("reconcile", "tables_agreed_v4.md") if os.path.exists(os.path.join(OUT, who, "tables_v4.md")) else None))

# paraphrases of the OLD claims
pat = re.compile(r"(?i)other locations|other sites|other site's|other sites'|\(the router context\)|tree-bank fingerprint|"
                 r"every tree array|bank's fingerprint|has the content, size|visits at other")
print("OLD-claim phrases in tables v5:", [(k + 1, m.group(0)) for k, x in enumerate(L5) for m in pat.finditer(x)])
lim = sec[9] - 1
print("OLD-claim phrases in spec v5 sections 0-8:", [(k + 1, m.group(0)) for k, x in enumerate(S5L[:lim]) for m in pat.finditer(x)])
print("OLD-claim phrases in spec v5 sections 9-12 (records):", [(k + 1, secname(k + 1), m.group(0)) for k, x in enumerate(S5L[lim:], lim)
                                                              for m in pat.finditer(x)][:20])
