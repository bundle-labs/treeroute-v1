# Skeptic (version 4 check, item 1): is each change V4-1 to V4-13 closed in tables_agreed.md and in the spec?
#  - every OLD/NEW pair of the change order (parsed from fix_order_v4.md; wrapped lines joined by one space): OLD gone
#    from version 4 of the tables (except inside its NEW), NEW at the expected lines; in the spec, NEW present and OLD
#    present only in the records (sections 10 and 11) or inside its NEW;
#  - V4-5: the rule of the `Adopted arm` row applied to the five gates.json `result` objects gives line 130;
#  - the spec's constant cells of S3.21 (E3a, E3m, E3, E5, E8) and the S3.22 row label equal the printed cells;
#  - the spec diff version 3 -> version 4 (difflib): every changed line inside a place that CHANGES_v4.md lists;
#    fenced blocks counted; the blocks whose content changed and their first lines;
#  - V4-13: the header comment sentence, CHANGES_v3.md lines 53-54, CHANGES_v4.md, spec section 11 and the contents
#    line. Read-only; prints only.
import difflib, hashlib, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SHAP = r"D:\treeroute\analysis\shap_v1"
rd = lambda *p: open(os.path.join(OUT, *p), encoding="utf-8", newline="").read()
T3, T4 = rd("reconcile", "tables_agreed_v3.md"), rd("reconcile", "tables_agreed.md")
S3, S4 = rd("spec", "TABLE_SPEC_v3.md"), rd("spec", "TABLE_SPEC.md")
L3, L4 = T3[:-1].split("\n"), T4[:-1].split("\n")
S3L, S4L = S3[:-1].split("\n"), S4[:-1].split("\n")
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
print("tables v3 %s... %d lines | v4 %s... %d lines" % (sha(T3)[:12], len(L3), sha(T4)[:12], len(L4)))
print("spec v3 %s... %d lines | v4 %s... %d lines" % (sha(S3)[:12], len(S3L), sha(S4)[:12], len(S4L)))
sec = {n: next((i + 1 for i, x in enumerate(S4L) if x.startswith("## %d." % n)), None) for n in range(0, 12)}
print("spec v4 section heading lines:", sec)

order = rd("_brief", "fix_order_v4.md").split("\n")
blocks, ids, cur, curid, hdr = [], [], None, None, None
for ln in order:
    m = re.match(r"## (V4-\d+)\.", ln)
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
    for m in re.finditer(r"OLD: `([^`]+)` NEW: `([^`]+)`", b):
        pairs.append((i, m.group(1), m.group(2)))
    m = re.search(r"after the Version 3 sentence, add `([^`]+)`", b)
    if m:
        ins = m.group(1)
print("order: %d OLD/NEW pairs + the V4-13 sentence (%s)" % (len(pairs), ins is not None))


def where(txt, L):
    return [k + 1 for k, x in enumerate(L) if txt in x]


def old_outside_new(o, n, L):
    """lines where OLD occurs outside an occurrence of NEW"""
    res = []
    for k, x in enumerate(L):
        y = x.replace(n, "\0") if n else x
        if o in y:
            res.append(k + 1)
    return res


def secname(k):
    s = max([n for n, v in sec.items() if v is not None and v <= k] or [-1])
    return "S%d" % s


for i, o, n in pairs:
    n4 = where(n, L4)
    o4 = old_outside_new(o, n, L4)
    o3 = where(o, L3)
    n3 = where(n, L3)
    ns = where(n, S4L)
    os_ = old_outside_new(o, n, S4L)
    print("%-6s tables v3: OLD on %s, NEW on %s | tables v4: NEW on %s, OLD (outside NEW) on %s | spec v4: NEW at %s, OLD (outside NEW) at %s"
          % (i, o3, n3, n4, o4, ["L%d(%s)" % (k, secname(k)) for k in ns][:6], ["L%d(%s)" % (k, secname(k)) for k in os_][:6]))
v3s = "Version 3 (2026-11-17, after the second check): captions, notes, labels, cells and source comments reworded, as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed."
print("V4-13 sentence: v4 line 1 holds Version-3 sentence + ' ' + it + ' Built from': %s | v4 count %d | v3 count %d | spec v4 lines %s" % (
    (v3s + " " + ins + " Built from") in L4[0], T4.count(ins), T3.count(ins), where(ins, S4L)))
print("   v3 line 1 + insertion == v4 line 1:", L3[0].replace(v3s, v3s + " " + ins, 1) == L4[0])

# V4-5: the Adopted arm rule
rule = [x for x in S4L if x.startswith("| `Adopted arm` |")]
print("V4-5: spec rule rows %d; holds 'plain tree answers': %s; holds 'plain answers' outside 'plain tree answers': %s" % (
    len(rule), '"plain tree answers"' in rule[0], '"plain answers"' in rule[0]))
LINK = {"identity": "identity", "log_c": "log(y + c)", "arcsine": "arcsine"}
KIND = {"per_unit": "per-location router", "region": "region router", "neighbour": "neighbour router"}
cells = []
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    R = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))["result"]
    tk = {"plain": "plain tree answers", "corrector": "corrected answers"}[R["table_kind"]]
    cells.append("%s, %s, %s; %s" % (LINK[R["link"]], tk, "error-weighted" if R["weighted"] else "uniformly weighted",
                                       KIND[R["kind"]]))
exp130 = "| Adopted arm | link, answer type and weighting; router type | " + " | ".join(cells) + " |"
print("   rule applied to the five results == v4 line 130:", exp130 == L4[129], "| cells:", cells)

# constant cells of S3.21 and the S3.22 label: spec vs printed
spec_rows = {}
for x in S4L:
    m = re.match(r"\| `(E3a|E3m|E3|E5ᵃ|E8|E5a|E10|E6)` \| `([^`]+)` \|", x)
    if m:
        spec_rows[m.group(1)] = m.group(2)
for g, ln in [("E3a", 134), ("E3m", 135), ("E3", 136), ("E5ᵃ", 138), ("E8", 143)]:
    c = L4[ln - 1].split(" | ")[1]
    print("   S3.21 %-4s spec constant == printed cell (line %d): %s" % (g, ln, spec_rows.get(g) == c))
m = re.search(r"^\| `(Rivals that explain[^`]*)` \|", S4, re.M)
print("   S3.22 row label in spec == printed (line 155):", bool(m) and L4[154].startswith("| " + m.group(1) + " |"))

# spec diff v3 -> v4
listed = {15, 309, 417, 480, 524, 579, 580, 674, 678, 679, 680, 682, 687, 693, 724, 931} | set(range(1369, 1424))
sm = difflib.SequenceMatcher(a=S3L, b=S4L, autojunk=False)
outside, nh, kinds = [], 0, []
for t, a1, a2, b1, b2 in sm.get_opcodes():
    if t == "equal":
        continue
    nh += 1
    kinds.append((t, a1 + 1, a2, b1 + 1, b2))
    if t == "delete":
        outside.append(("deleted v3 lines %d-%d" % (a1 + 1, a2), S3L[a1][:60]))
    for k in range(b1 + 1, b2 + 1):
        if k not in listed:
            outside.append((k, S4L[k - 1][:80]))
print("spec diff hunks: %d %s" % (nh, kinds))
print("   changed v4 lines outside the listed places: %d %s" % (len(outside), outside[:6]))
print("   lines 1-1368 of v4 equal v3 except the listed lines:",
      all(S3L[k] == S4L[k] or (k + 1) in listed for k in range(1368)), "| v4 lines 1369-1423 appended after v3's last line:",
      S4L[:1368] != S3L and len(S4L) == 1423)
fence = lambda L: [k + 1 for k, x in enumerate(L) if x.startswith("```")]
f3, f4 = fence(S3L), fence(S4L)
print("fenced blocks: v3 %d (fence lines %d), v4 %d (fence lines %d); same fence lines: %s" % (
    len(f3) // 2, len(f3), len(f4) // 2, len(f4), f3 == f4[:len(f3)]))
chg = []
for b in range(len(f3) // 2):
    c3 = S3L[f3[2 * b]:f3[2 * b + 1] - 1]
    c4 = S4L[f4[2 * b]:f4[2 * b + 1] - 1]
    if c3 != c4:
        chg.append(b + 1)
        print("   block %2d (L%d) changed | first line same start (24 chars): %s | v3 %r | v4 %r" % (
            b + 1, f4[2 * b], c3[0][:24] == c4[0][:24], c3[0][:40], c4[0][:40]))
print("   blocks whose content changed:", chg)

# V4-13 bookkeeping
CH3 = rd("spec", "CHANGES_v3.md")
C3L = CH3[:-1].split("\n")
print("CHANGES_v3.md: %d bytes, %d lines; L53: %r; L54: %r" % (len(CH3.encode("utf-8")), len(C3L), C3L[52], C3L[53]))
print("   '(corrected in version 4)' at lines:", where("(corrected in version 4)", C3L),
      "| old text '354-360 and 369-375' left at:", where("354-360 and 369-375", C3L))
undo = CH3.replace("  354, 358-360, 369 and 373-375 (corrected in version 4) of S3.25) keep their `cell`, a cell that does not change.\n  The `spec` key stays `OUT\\spec\\TABLE_SPEC.md`.",
                   "  354-360 and 369-375 of S3.25) keep their `cell`, a cell that does not change. The `spec` key stays\n  `OUT\\spec\\TABLE_SPEC.md`.")
print("   undoing the correction gives %d bytes, %d lines" % (len(undo.encode("utf-8")), len(undo[:-1].split("\n"))))
ln354 = [k for k in range(340, 380) if "declined by its skill guard: Ridge" in L4[k - 1]]
print("   tables v4: lines 340-379 holding 'declined by its skill guard: Ridge':", ln354)
print("CHANGES_v4.md exists:", os.path.exists(os.path.join(OUT, "spec", "CHANGES_v4.md")),
      "| spec section 11 heading line:", sec.get(11), repr(S4L[sec[11] - 1]) if sec.get(11) else None)
print("contents line (L15) ends:", repr(S4L[14][-75:]))
