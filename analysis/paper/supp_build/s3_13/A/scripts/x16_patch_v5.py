# -*- coding: utf-8 -*-
# One-off patch of build_tables.py for version 5 of the spec (it refuses to run unless build_tables.py is the
# version-4 file, by SHA-256). verify_constants.py and verify_outputs.py are not changed: they hold none of the texts
# that version 5 changes, and x15_old_texts_in_spec_v5.py found no version-4 text of the changed constants as a fenced
# line or a backticked text of version 5, so their checks already tell the two versions apart
# (x17_negative_control_v5.py confirms it).
# Every changed fixed text is TAKEN FROM OUT\spec\TABLE_SPEC.md (version 5; its SHA-256 is checked), never typed here.
# The change order's OLD and NEW printed texts, as OUT\spec\CHANGES_v5.md quotes them (6 OLD, 6 NEW and the sentence
# that V5-5 adds; SHA-256 checked), serve only as a check: each new spec text must be the version-4 constant (itself
# equal to the version-4 spec's text, OUT\spec\TABLE_SPEC_v4.md, SHA-256 checked) with exactly the ordered
# replacements, and the order itself (OUT\_brief\fix_order_v5.md, wrapped lines joined by one space; SHA-256 checked)
# must hold every quoted printed text. The fenced blocks used must be the ones CHANGES_v5.md's table lists, at its
# lines, and the spec lines used, with the contents line (S12), must be every line of sections 0 to 11 that differs
# between the two versions.
# build_tables.py: V5-5 the header comment; V5-1 and V5-2 the Table 9 caption; V5-2 S3.19 note c; V5-4 and V5-3 the
# "What it checks" cells of S3.21's rows E3m and E5; V5-3 S3.21 note a.
# Writes only build_tables.py (UTF-8, LF) and prints its diff.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import ast
import json
import hashlib
import difflib
import importlib.util

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
SPEC = os.path.join(OUT, "spec", "TABLE_SPEC.md")
SPEC4 = os.path.join(OUT, "spec", "TABLE_SPEC_v4.md")
CHG = os.path.join(OUT, "spec", "CHANGES_v5.md")
ORDER = os.path.join(OUT, "_brief", "fix_order_v5.md")
BT = os.path.join(HERE, "build_tables.py")
SPEC_SHA = "96a973d2bbaf949cafc1b203ed3e05605c0511196de5580f2ba0734c17e23fc2"
SPEC4_SHA = "8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885"
CHG_SHA = "88c90e639c4f7112afb0aff2254490012fe04cb43bf1ceda29ccb3f866288e0e"
ORDER_SHA = "9b4a7dc234ff63e4e9478f7902db56aa6ad092a22d01a17073705f52a503b3bb"
BT4_SHA = "89f53a4849a83cfa19a2f3236ce6d16a062e60353f483ced6d25e6b043d7a45b"


def stop(msg):
    print("STOP: " + msg)
    print("build_tables.py was not written.")
    sys.exit(1)


def need(c, msg):
    if not c:
        stop(msg)


def one(items, what):
    need(len(items) == 1, "%s: %d matches" % (what, len(items)))
    return items[0]


def read_checked(path, sha, what):
    with open(path, "rb") as f:
        raw = f.read()
    need(hashlib.sha256(raw).hexdigest() == sha, "%s: SHA-256 is not the expected one" % what)
    need(b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), "%s has CR bytes or a BOM" % what)
    return raw.decode("utf-8")


def fenced_blocks(lines, what):
    out, cur = [], None
    for i, line in enumerate(lines, 1):
        if line.startswith("```"):
            if cur is None:
                cur = (i, [])
            else:
                out.append(cur)
                cur = None
            continue
        if cur is not None:
            cur[1].append(line)
    need(cur is None and len(out) == 63, "%s: fenced blocks: %d" % (what, len(out)))
    return out


# ------------------------------------------------------------------ the spec, version 5 and version 4
SL = read_checked(SPEC, SPEC_SHA, "TABLE_SPEC.md (version 5)").split("\n")
SL4 = read_checked(SPEC4, SPEC4_SHA, "TABLE_SPEC_v4.md").split("\n")
blocks, blocks4 = fenced_blocks(SL, "version 5"), fenced_blocks(SL4, "version 4")
need([b[0] for b in blocks] == [b[0] for b in blocks4], "fenced blocks moved between the versions")
need(len(SL4) == 1424 and SL4[-1] == "" and len(SL) == 1477 and SL[-1] == "", "line counts of the two versions")
used_blocks = {}  # block number (1-based) -> line of its opening fence
used_lines = set()  # spec lines (1-based) whose version-5 text is taken


def fenced_line(prefix, what, v4_value):
    hits = [(q, k, b[0] + 1 + k, x) for q, b in enumerate(blocks) for k, x in enumerate(b[1]) if x.startswith(prefix)]
    q, k, ln, x = one(hits, what)
    need(len(blocks4[q][1]) == len(blocks[q][1]) and blocks4[q][1][k] == v4_value,
         "%s: the script's version-4 text is not the version-4 spec's line %d" % (what, ln))
    need(all(blocks[q][1][j] == blocks4[q][1][j] for j in range(len(blocks[q][1])) if j != k),
         "%s: another line of block %d changed" % (what, q + 1))
    used_blocks[q + 1] = blocks[q][0]
    used_lines.add(ln)
    print("  %-24s spec line %d (block %d)" % (what, ln, q + 1))
    return x


# ------------------------------------------------------------------ the order's OLD and NEW texts (CHANGES_v5.md)
CH = read_checked(CHG, CHG_SHA, "CHANGES_v5.md").split("\n")
items, spec_texts, sec, i = [], [], None, 0
while i < len(CH):
    line = CH[i]
    if line.startswith("## "):
        sec = line[3:].split(".")[0]
    if line.startswith("```"):
        j = i + 1
        body = []
        while not CH[j].startswith("```"):
            body.append(CH[j])
            j += 1
        k = i - 1
        while k >= 0 and CH[k].strip() == "":
            k -= 1
        para = []
        while k >= 0 and CH[k].strip() != "" and not CH[k].startswith("```"):
            para.insert(0, CH[k].strip())
            k -= 1
        label = " ".join(para)
        if "printed text" in label:
            kind = "O" if "OLD printed" in label else ("N" if "NEW printed" in label else None)
            need(kind is not None and len(body) == 1, "CHANGES_v5.md block at line %d: %r" % (i + 1, label))
            items.append((sec, kind, body[0], label))
        elif label.endswith("spec text:"):
            need(len(body) == 1, "CHANGES_v5.md spec-text block at line %d" % (i + 1))
            spec_texts.append((sec, label.split()[-3], body[0]))
        else:
            stop("CHANGES_v5.md block at line %d has an unknown label: %r" % (i + 1, label))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text, label in items:
    seq.setdefault(s_, []).append((kind, text, label))
want = {"V5-1": "ON", "V5-2": "ONON", "V5-3": "ONON", "V5-4": "ON", "V5-5": "N"}
got = {s_: "".join(k for k, t, lab in v) for s_, v in seq.items()}
need(got == want, "CHANGES_v5.md printed-text blocks: %r" % got)
need(sum(k == "O" for s_, k, t, lab in items) == 6 and sum(k == "N" for s_, k, t, lab in items) == 7,
     "CHANGES_v5.md: not 6 OLD and 6 NEW texts and the V5-5 sentence")
need([(s_, v) for s_, v, t in spec_texts] == [("S12", "v4"), ("S12", "v5")],
     "CHANGES_v5.md spec-text blocks: %r" % [(s_, v) for s_, v, t in spec_texts])
C4, C5 = [t for s_, v, t in spec_texts]
need("Table 9 caption" in seq["V5-2"][0][2] and "note ᶜ" in seq["V5-2"][2][2]
     and "E5's" in seq["V5-3"][0][2] and "Note ᵃ" in seq["V5-3"][2][2], "CHANGES_v5.md: labels of V5-2 and V5-3")


def prs(s_):
    v = seq[s_]
    need(len(v) % 2 == 0 and all(v[q][0] == "O" and v[q + 1][0] == "N" for q in range(0, len(v), 2)), s_)
    return [(v[q][1], v[q + 1][1]) for q in range(0, len(v), 2)]


V51, V52, V53, V54 = prs("V5-1"), prs("V5-2"), prs("V5-3"), prs("V5-4")
ALL = V51 + V52 + V53 + V54
need(len(ALL) == 6, "pair count")
INS_TEXT, INS_LABEL = seq["V5-5"][0][1], seq["V5-5"][0][2]
INS_AFTER = one(re.findall(r"which ends `([^`]+)`", INS_LABEL), "V5-5: the end of the Version 4 sentence")
INS_BEFORE = one(re.findall(r"and before `([^`]+)`", INS_LABEL), "V5-5: the text that follows the new sentence")

# the order holds every quoted printed text (wrapped lines joined by one space)
order = read_checked(ORDER, ORDER_SHA, "fix_order_v5.md")
flat_order = " ".join(x.strip() for x in order.split("\n"))
for s_, kind, text, label in items:
    need(text in flat_order, "%s %s text not in the order: %r" % (s_, kind, text[:80]))


def apply(text, pairs, what):
    for o, n in pairs:
        need(text.count(o) == 1, "%s: OLD found %d times: %r" % (what, text.count(o), o[:70]))
        text = text.replace(o, n)
    return text


# ------------------------------------------------------------------ version 4 of the script
with open(BT, "rb") as f:
    bt_raw = f.read()
need(hashlib.sha256(bt_raw).hexdigest() == BT4_SHA, "build_tables.py is not version 4 (SHA-256)")
need(b"\r" not in bt_raw, "build_tables.py has CR bytes")
src4 = bt_raw.decode("utf-8")
ms = importlib.util.spec_from_file_location("bt4", BT)
bt4 = importlib.util.module_from_spec(ms)
ms.loader.exec_module(bt4)
need("Version 5" not in bt4.HEADER_COMMENT, "build_tables.py is already version 5")

new = {}
print("texts taken from the spec (each checked against the version-4 constant and the order's OLD/NEW texts):")

# V5-5: the header comment (the sentence inserted directly after the Version 4 sentence)
h4 = bt4.HEADER_COMMENT
fe = "the nowcast of each problem."
x = fenced_line(h4[:h4.index(fe) + len(fe)], "HEADER_COMMENT", h4)
anchor = INS_AFTER + " " + INS_BEFORE
need(h4.count(anchor) == 1, "HEADER_COMMENT: the V5-5 anchor found %d times" % h4.count(anchor))
v4s = h4[h4.index("Version 4 ("):h4.index(anchor) + len(INS_AFTER)]
need(h4.count("Version 4 (") == 1 and ". " not in v4s, "HEADER_COMMENT: the anchor does not end the Version 4 sentence")
need(x == h4.replace(anchor, INS_AFTER + " " + INS_TEXT + " " + INS_BEFORE), "HEADER_COMMENT: not the ordered insertion")
new["HEADER_COMMENT"] = x

# V5-1 and V5-2: the Table 9 caption (coral bleaching's background, then the context-and-calendar gloss)
x = fenced_line(bt4.CAP9[:24], "CAP9", bt4.CAP9)
need(x == apply(bt4.CAP9, [V52[0], V51[0]], "CAP9"), "CAP9: not the ordered change")
new["CAP9"] = x

# V5-2: S3.19 note c (block 19, found by its unchanged note a)
q19 = one([q for q, b in enumerate(blocks) if len(b[1]) == 4 and b[1][0] == bt4.NOTES19[0]], "S3.19 notes")
need(blocks4[q19][1] == bt4.NOTES19, "NOTES19: the script's version-4 lines are not the version-4 spec's block")
n19 = blocks[q19][1]
need([n19[q] for q in (0, 1, 3)] == [bt4.NOTES19[q] for q in (0, 1, 3)]
     and n19[2] == apply(bt4.NOTES19[2], [V52[1]], "NOTES19 note c"),
     "NOTES19: not (note c reworded, the rest unchanged)")
used_blocks[q19 + 1] = blocks[q19][0]
used_lines.add(blocks[q19][0] + 3)
print("  %-24s spec block at line %d (block %d; note c at line %d)" % ("NOTES19", blocks[q19][0], q19 + 1,
                                                                      blocks[q19][0] + 3))
new["NOTES19"] = list(n19)


# V5-4 and V5-3: the S3.21 rows (the row table of 4.5: gate cell, "What it checks", problem cell)
def gate_table(lines, what):
    hi = one([q for q, x in enumerate(lines) if x == "| Gate cell | What it checks | Problem cell |"], what)
    need(lines[hi + 1] == "|---|---|---|", what + ": separator")
    rows, q = [], hi + 2
    while lines[q].startswith("| "):
        mo = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| (.+) \|$", lines[q])
        need(mo is not None, "%s: line %d" % (what, q + 1))
        rows.append((q + 1, mo.group(1), mo.group(2), mo.group(3)))
        q += 1
    return rows


g5, g4 = gate_table(SL, "S3.21 row table (v5)"), gate_table(SL4, "S3.21 row table (v4)")
need([r[0] for r in g5] == [r[0] for r in g4] and len(g5) == len(bt4.GATE_ROWS), "S3.21 row tables")
gate_rows, changed_keys, used = [], [], []
for (ln, g, w, rule), (ln4, g_4, w_4, rule4), (key, gs, ws) in zip(g5, g4, bt4.GATE_ROWS):
    need((g_4, w_4) == (gs, ws), "S3.21 row %s: the script's version-4 cells are not the version-4 spec's" % key)
    pw = [pr for pr in ALL if pr[0] in ws]
    need(g == gs, "S3.21 row %s: the gate cell changed" % key)
    need(w == apply(ws, pw, "S3.21 " + key), "S3.21 row %s: the spec's cell is not the ordered change" % key)
    need(rule == rule4, "S3.21 row %s: its problem-cell rule changed" % key)
    if pw:
        changed_keys.append(key)
        used_lines.add(ln)
    used += pw
    gate_rows.append((key, g, w))
need(changed_keys == ["E3m", "E5"], "S3.21 changed rows %r" % changed_keys)
need(sorted(used) == sorted([V54[0], V53[0]]), "S3.21: the order's two S3.21 cell texts are not each used once")
print("  %-24s spec lines %d-%d (changed: %s)" % ("GATE_ROWS", g5[0][0], g5[-1][0], ", ".join(
    "%s line %d" % (r[1], r[0]) for r, k in zip(g5, bt4.GATE_ROWS) if k[0] in changed_keys)))
new["GATE_ROWS"] = gate_rows

# V5-3: S3.21 note a (block 26, found by the unchanged start of its first line)
q21 = one([q for q, b in enumerate(blocks) if len(b[1]) == 2 and b[1][0].startswith(bt4.NOTES21[0][:24])],
          "S3.21 notes")
need(blocks4[q21][1] == bt4.NOTES21, "NOTES21: the script's version-4 lines are not the version-4 spec's block")
n21 = blocks[q21][1]
need(n21[1] == bt4.NOTES21[1] and n21[0] == apply(bt4.NOTES21[0], [V53[1]], "NOTES21 note a"),
     "NOTES21: not (note a reworded, the rest unchanged)")
used_blocks[q21 + 1] = blocks[q21][0]
used_lines.add(blocks[q21][0] + 1)
print("  %-24s spec block at line %d (block %d; note a at line %d)" % ("NOTES21", blocks[q21][0], q21 + 1,
                                                                      blocks[q21][0] + 1))
new["NOTES21"] = list(n21)

# S12: the contents line (nothing printed)
ln_c = one([n + 1 for n in range(1423) if SL4[n].count(C4) == 1 and SL[n] == SL4[n].replace(C4, C5)],
           "the contents line (S12)")
print("  %-24s spec line %d (not printed)" % ("contents line (S12)", ln_c))

# coverage: the blocks used are CHANGES_v5.md's table; the lines used and the contents line are every line of
# sections 0 to 11 that differs; every other block is unchanged; section 12 follows the last line of section 11
fb = {}
for x in CH:
    mo = re.match(r"^\| (\d+) \| (\d+) \| ", x)
    if mo:
        fb[int(mo.group(1))] = int(mo.group(2))
need(fb == used_blocks, "blocks used %r, CHANGES_v5.md's table %r" % (sorted(used_blocks.items()), sorted(fb.items())))
for q in range(63):
    need(q + 1 in used_blocks or blocks[q][1] == blocks4[q][1], "block %d changed but is not used" % (q + 1))
diff_lines = [n + 1 for n in range(1423) if SL[n] != SL4[n]]
need(diff_lines == sorted(used_lines | {ln_c}), "changed spec lines %r; used %r" % (diff_lines, sorted(used_lines)))
need(SL[1423] == "" and SL[1424] == "---" and SL[1426].startswith("## 12. Version 5"), "section 12 not where expected")
print("blocks used (CHANGES_v5.md's table): %s" % ", ".join("%d (L%d)" % kv for kv in sorted(used_blocks.items())))
print("changed spec lines of sections 0 to 11 (all used or the contents line): %s" % ", ".join(map(str, diff_lines)))


# ------------------------------------------------------------------ the new source
def lit(s):
    need(isinstance(s, str) and not any(c in s for c in "\n\r\t"), "bad text %r" % (s,))
    out = json.dumps(s, ensure_ascii=False)
    need(ast.literal_eval(out) == s, "literal round trip")
    return out


def stmt(name, v):
    if isinstance(v, str):
        return [name + " = " + lit(v)]
    out = [name + " = ["]
    for it in v:
        if isinstance(it, tuple):
            out.append("    (" + ", ".join(lit(y) for y in it) + "),")
        else:
            out.append("    " + lit(it) + ",")
    out.append("]")
    return out


def sub1(src, old, rep, what, count=1):
    need(src.count(old) == count, "%s: anchor found %d times" % (what, src.count(old)))
    return src.replace(old, rep)


tree4 = ast.parse(src4)
spans = {}
for node in tree4.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        nm = node.targets[0].id
        need(nm not in spans, "%s assigned twice" % nm)
        spans[nm] = (node.lineno, node.end_lineno)
REPL = ["HEADER_COMMENT", "CAP9", "NOTES19", "GATE_ROWS", "NOTES21"]
for nm in REPL:
    need("\n".join(stmt(nm, getattr(bt4, nm))) == "\n".join(src4.split("\n")[spans[nm][0] - 1:spans[nm][1]]),
         "%s: the version-4 statement is not in the patch's layout" % nm)
lines = src4.split("\n")
for a, b, repl, nm in sorted([(spans[nm][0], spans[nm][1], stmt(nm, new[nm]), nm) for nm in REPL],
                              key=lambda e: -e[0]):
    need(len(repl) == b - a + 1, "%s: the statement changed its number of lines" % nm)
    lines[a - 1:b] = repl
src5 = "\n".join(lines)
HDR_OLD = "# x11_patch_v4.py), among them the answer-type words of the rule of the S3.21 Adopted arm row (V4-5).\n"
HDR_ADD = ("# Version 5 (2026-11-17): the texts changed by spec version 5 (V5-1 to V5-5, taken from the spec by\n"
           "# x16_patch_v5.py): the header comment, the Table 9 caption, S3.19 note c, S3.21 E3m and E5 and note a.\n")
src5 = sub1(src5, HDR_OLD, HDR_OLD + HDR_ADD, "script header")
compile(src5, BT, "exec")

# checks of the patched module
tmp = {"__name__": "bt5", "__file__": BT}
exec(compile(ast.parse(src5), BT, "exec"), tmp)  # defines only; main() runs under __main__ only
for nm in REPL:
    need(tmp[nm] == new[nm], "%s differs after the patch" % nm)
others = [n for n in spans if n not in REPL and isinstance(getattr(bt4, n), (str, list, dict, tuple, set))]
for nm in others:
    need(tmp[nm] == getattr(bt4, nm), "%s changed, but it is not in the order" % nm)
print("other module-level texts and lists unchanged: %d" % len(others))
for o, n in ALL:
    for fo, fn_ in ((o, n), (json.dumps(o, ensure_ascii=False)[1:-1], json.dumps(n, ensure_ascii=False)[1:-1])):
        need(src5.count(fo) == src5.count(fn_) * fn_.count(fo), "OLD text left in the script: %r" % o[:60])
need(src5.count(INS_TEXT) == 1 and tmp["HEADER_COMMENT"].count(INS_TEXT) == 1, "the V5-5 sentence after the patch")
# every source line outside the five statements is unchanged: with the two added header lines removed, the
# version-5 source differs from version 4 only on the lines of the changed list items and strings
L4s, L5s = src4.split("\n"), src5.split("\n")
ih = one([q for q in range(len(L5s) - 1) if L5s[q] + "\n" + L5s[q + 1] + "\n" == HDR_ADD], "added header lines")
L5r = L5s[:ih] + L5s[ih + 2:]
need(len(L5r) == len(L4s), "line count after removing the added header lines")
expect = {spans["HEADER_COMMENT"][0], spans["CAP9"][0], spans["NOTES19"][0] + 3,
          spans["GATE_ROWS"][0] + 1 + [k for k, g, w in bt4.GATE_ROWS].index("E3m"),
          spans["GATE_ROWS"][0] + 1 + [k for k, g, w in bt4.GATE_ROWS].index("E5"), spans["NOTES21"][0] + 1}
got_lines = {q + 1 for q in range(len(L4s)) if L4s[q] != L5r[q]}
need(got_lines == expect, "changed source lines %r, expected %r" % (sorted(got_lines), sorted(expect)))
print("source lines changed (version-4 numbering): %s; plus 2 header lines added after line %d" % (
    ", ".join(map(str, sorted(got_lines))), ih))

with open(BT, "w", encoding="utf-8", newline="\n") as f:
    f.write(src5)
print("build_tables.py written: %d -> %d lines; sha256 %s" % (src4.count("\n"), src5.count("\n"),
                                                              hashlib.sha256(src5.encode("utf-8")).hexdigest()))
print("diff (v4 -> v5):")
for d in difflib.unified_diff(src4.split("\n"), src5.split("\n"), "build_tables.py v4", "build_tables.py v5", n=0,
                              lineterm=""):
    print(d)
