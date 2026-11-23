# Skeptic (version 3 check, item 1): is each change V3-1 to V3-7 closed in tables_agreed.md and in the spec?
#  - every OLD/NEW pair of the change order: OLD gone from version 3 of the tables, NEW at the expected lines; in the
#    spec, NEW present and OLD present only where a record or the source-word rule keeps it;
#  - the spec diff version 2 -> version 3 (difflib): every changed line inside a place that CHANGES_v3.md lists;
#    fenced blocks counted; the first lines of blocks 14 and 16;
#  - the prose items of V3-1 and V3-7 (4.1, 4.7, 4.9, decision 12, section 5, section 10) and CHANGES_v2.md.
# Read-only; prints only.
import difflib, hashlib, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
rd = lambda *p: open(os.path.join(OUT, *p), encoding="utf-8", newline="").read()
T2 = rd("reconcile", "tables_agreed_v2.md")
T3 = rd("reconcile", "tables_agreed.md")
S2 = rd("spec", "TABLE_SPEC_v2.md")
S3 = rd("spec", "TABLE_SPEC.md")
L3, S2L, S3L = T3.split("\n"), S2.split("\n"), S3.split("\n")
print("spec v2 sha256 %s..., lines %d | spec v3 sha256 %s..., lines %d" % (
    hashlib.sha256(S2.encode()).hexdigest()[:12], len(S2L) - 1, hashlib.sha256(S3.encode()).hexdigest()[:12], len(S3L) - 1))
sec10 = next(i for i, x in enumerate(S3L) if x.startswith("## 10. Version 3")) + 1
sec9 = next(i for i, x in enumerate(S3L) if x.startswith("## 9. Version 2")) + 1
print("spec v3: section 9 at line %d, section 10 at line %d; contents line: %r" % (sec9, sec10, S3L[14][-60:]))

order = rd("_brief", "fix_order_v3.md").split("\n")
blocks, cur, hdr, ids = [], None, None, []
for ln in order:
    m = re.match(r"## (V3-\d)\.", ln)
    if m:
        hdr = m.group(1)
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
pairs = []
for b, i in zip(blocks, ids):
    m = re.search(r"OLD(?: row label)?: `([^`]+)`.*?NEW: `([^`]+)`", b)
    if m:
        o, n = m.group(1), m.group(2)
        if o.startswith("...") and n.startswith("..."):
            o, n = o[3:], n[3:]
        pairs.append((i, o, n))
    m = re.search(r"a new sentence directly after `([^`]+)`\.? NEW: `([^`]+)`", b)
    if m:
        pairs.append((i, None, m.group(2)))
        anchor = m.group(1)


def where(txt, L):
    return [k + 1 for k, x in enumerate(L) if txt in x]


for i, o, n in pairs:
    n_t = where(n, L3)
    o_t = where(o, L3) if o and o not in n else []
    n_s = where(n, S3L)
    o_s = [k for k in where(o, S3L) if k < sec9] if o and o not in n else []
    print("%s | tables v3: NEW on %s%s | OLD left on %s | spec v3: NEW at %s | OLD before section 9 at %s :: %s" % (
        i, n_t[:12], " (+%d)" % (len(n_t) - 12) if len(n_t) > 12 else "", o_t, n_s[:8], o_s, n[:60]))
ins_line = where(anchor + " " + [n for i, o, n in pairs if o is None][0], L3)
print("V3-1 Table 9: the new sentence directly after the anchor (joined by one space) on line", ins_line)

# spec diff v2 -> v3
listed = set([15, 284, 309, 345, 346, 417, 480, 502, 511, 520, 533, 539, 551, 580, 637, 674, 678, 679, 680, 684, 688,
              724, 759, 764, 767, 768, 769, 770, 776, 777, 806, 891, 988, 1025, 1026, 1114, 1115, 1116, 1203, 1204, 1205,
              1218, 1219] + list(range(453, 460)) + list(range(1314, 1369)))
sm = difflib.SequenceMatcher(a=S2L, b=S3L, autojunk=False)
outside = []
nh = 0
for t, a1, a2, b1, b2 in sm.get_opcodes():
    if t == "equal":
        continue
    nh += 1
    rng = list(range(b1 + 1, b2 + 1))
    if not rng:
        outside.append(("deleted v2 lines %d-%d" % (a1 + 1, a2), S2L[a1][:60]))
    for k in rng:
        if k not in listed:
            outside.append((k, S3L[k - 1][:80]))
print("spec diff hunks: %d | changed v3 lines outside the listed places: %d %s" % (nh, len(outside), outside[:6]))
fence = lambda L: [k + 1 for k, x in enumerate(L) if x.startswith("```")]
f2, f3 = fence(S2L), fence(S3L)
print("fenced blocks: v2 %d, v3 %d" % (len(f2) // 2, len(f3) // 2))
for bno in (14, 16):
    k2, k3 = f2[2 * (bno - 1)], f3[2 * (bno - 1)]
    print("   block %d: v2 L%d first line %r | v3 L%d first line %r" % (bno, k2, S2L[k2][:60], k3, S3L[k3][:60]))
chg_blocks = []
for b in range(len(f3) // 2):
    c2 = "\n".join(S2L[f2[2 * b]:f2[2 * b + 1] - 1])
    c3 = "\n".join(S3L[f3[2 * b]:f3[2 * b + 1] - 1])
    if c2 != c3:
        chg_blocks.append(b + 1)
print("   blocks whose content changed:", chg_blocks)

# the prose of V3-1 and V3-7
for name, a, b in [("4.1 paragraph", 447, 459), ("4.7 paragraph", 772, 777), ("4.9 paragraph", 1021, 1026),
                   ("decision 12", 1203, 1205), ("section 5", 1111, 1116), ("check 3.3", 340, 346)]:
    txt = " ".join(S3L[a - 1:b])
    print("%s (v3 L%d-%d): region-weight words %s | cites PROTOCOL section 8 %s" % (
        name, a, b, bool(re.search(r"region", txt)), "PROTOCOL section 8" in txt))
CH2 = rd("spec", "CHANGES_v2.md").split("\n")
print("CHANGES_v2.md: '786' left:", where("786", CH2), "| '(corrected in version 3)' at:", where("(corrected in version 3)", CH2))
print("CHANGES_v3.md exists:", os.path.exists(os.path.join(OUT, "spec", "CHANGES_v3.md")))
print("tables v3: 'kept arm' / 'Kept arm' left:", where("kept arm", L3), where("Kept arm", L3),
      "| 'declined by its guard' left:", where("declined by its guard", L3), "| 'Guard-passing' left:", where("Guard-passing", L3),
      "| 'freeze' left:", where("freeze", L3), "| 'derive' left:", where("derive", L3),
      "| 'guard tolerance' left:", where("guard tolerance", L3), "| 'collation moves' left:", where("collation moves", L3),
      "| 'defined on fewer' left:", where("defined on fewer", L3), "| \"the board's\" left:", where("the board's", L3))
