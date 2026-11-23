# -*- coding: utf-8 -*-
# One-off patch of build_tables.py and verify_constants.py for version 4 of the spec (it refuses to run unless both
# are the version-3 files, by SHA-256).
# Every changed fixed text is TAKEN FROM OUT\spec\TABLE_SPEC.md (version 4; its SHA-256 is checked), never typed here.
# The change order's OLD and NEW printed texts, as OUT\spec\CHANGES_v4.md quotes them (15 OLD, 15 NEW and the
# sentence that V4-13 adds; SHA-256 checked), serve only as a check: each new spec text must be the version-3
# constant (itself equal to the version-3 spec's text, OUT\spec\TABLE_SPEC_v3.md, SHA-256 checked) with exactly the
# ordered replacements, and the order itself (OUT\_brief\fix_order_v4.md, wrapped lines joined by one space; SHA-256
# checked) must hold every quoted printed text. The fenced blocks used must be the ones CHANGES_v4.md's table lists,
# at its lines, and the spec lines used, with the contents line (S11), must be every line of sections 0 to 10 that
# differs between the two versions.
# build_tables.py: V4-13 the header comment; V4-3 and V4-4 the Table 9 caption; V4-12 the S3.18 caption (its source
# comment); V4-7 the header line of the S3.18 panel b table; V4-3 S3.19 notes b and c; V4-1, V4-2, V4-6, V4-10 and
# V4-11 the "What it checks" cells of S3.21's rows E3m, E3a, E5, E3 and E8; V4-6 S3.21 note a; V4-5 the answer-type
# words of the rule of S3.21's Adopted arm row; V4-8 the S3.22 row label; V4-9 the S3.28 caption.
# verify_constants.py: the S3.22 row label in its list of constant cells (V4-8), and a check of the answer-type words
# against the spec's rule (V4-5).
# Writes only build_tables.py and verify_constants.py (UTF-8, LF) and prints the diff of each.
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
SPEC3 = os.path.join(OUT, "spec", "TABLE_SPEC_v3.md")
CHG = os.path.join(OUT, "spec", "CHANGES_v4.md")
ORDER = os.path.join(OUT, "_brief", "fix_order_v4.md")
BT = os.path.join(HERE, "build_tables.py")
VC = os.path.join(HERE, "verify_constants.py")
SPEC_SHA = "8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885"
SPEC3_SHA = "573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31"
CHG_SHA = "0eac6c8d6489e9ae0c261c3e92a3a8ce30c8bff95c36ad7596f8b72e5e4ebd54"
ORDER_SHA = "93c8878b7093d5a800a554c868816d0ec302cb514324e0c2cc80527666cc8484"
BT3_SHA = "44d1f307a924765a4064833cc59c003e825cd6da876e59b8a144f1b991e431bd"
VC3_SHA = "861ac4a21b11d3c14b549a07296c104c1a8a080f977a042ecc40414b7aca6e71"


def stop(msg):
    print("STOP: " + msg)
    print("Neither script was written.")
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


# ------------------------------------------------------------------ the spec, version 4 and version 3
SL = read_checked(SPEC, SPEC_SHA, "TABLE_SPEC.md (version 4)").split("\n")
SL3 = read_checked(SPEC3, SPEC3_SHA, "TABLE_SPEC_v3.md").split("\n")
blocks, blocks3 = fenced_blocks(SL, "version 4"), fenced_blocks(SL3, "version 3")
need([b[0] for b in blocks] == [b[0] for b in blocks3], "fenced blocks moved between the versions")
need(len(SL3) == 1369 and SL3[-1] == "" and len(SL) == 1424 and SL[-1] == "", "line counts of the two versions")
used_blocks = {}  # block number (1-based) -> line of its opening fence
used_lines = set()  # spec lines (1-based) whose version-4 text is taken


def fenced_line(prefix, what, v3_value):
    hits = [(q, k, b[0] + 1 + k, x) for q, b in enumerate(blocks) for k, x in enumerate(b[1]) if x.startswith(prefix)]
    q, k, ln, x = one(hits, what)
    need(len(blocks3[q][1]) == len(blocks[q][1]) and blocks3[q][1][k] == v3_value,
         "%s: the script's version-3 text is not the version-3 spec's line %d" % (what, ln))
    need(all(blocks[q][1][j] == blocks3[q][1][j] for j in range(len(blocks[q][1])) if j != k),
         "%s: another line of block %d changed" % (what, q + 1))
    used_blocks[q + 1] = blocks[q][0]
    used_lines.add(ln)
    print("  %-24s spec line %d (block %d)" % (what, ln, q + 1))
    return x


# ------------------------------------------------------------------ the order's OLD and NEW texts (CHANGES_v4.md)
CH = read_checked(CHG, CHG_SHA, "CHANGES_v4.md").split("\n")
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
        if "printed text" in label or "printed cell" in label:
            kind = "O" if "OLD printed" in label else ("N" if "NEW printed" in label else None)
            need(kind is not None and len(body) == 1, "CHANGES_v4.md block at line %d: %r" % (i + 1, label))
            items.append((sec, kind, body[0], label))
        elif label.endswith("spec text:"):
            need(len(body) == 1, "CHANGES_v4.md spec-text block at line %d" % (i + 1))
            spec_texts.append((sec, label.split()[-3], body[0]))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text, label in items:
    seq.setdefault(s_, []).append((kind, text, label))
want = {"V4-1": "ON", "V4-2": "ON", "V4-3": "ONONON", "V4-4": "ON", "V4-5": "ON", "V4-6": "ONON", "V4-7": "ON",
        "V4-8": "ON", "V4-9": "ON", "V4-10": "ON", "V4-11": "ON", "V4-12": "ON", "V4-13": "N"}
got = {s_: "".join(k for k, t, lab in v) for s_, v in seq.items()}
need(got == want, "CHANGES_v4.md printed-text blocks: %r" % got)
need(sum(k == "O" for s_, k, t, lab in items) == 15 and sum(k == "N" for s_, k, t, lab in items) == 16,
     "CHANGES_v4.md: not 15 OLD and 15 NEW texts and the V4-13 sentence")
need([(s_, v) for s_, v, t in spec_texts] == [("V4-5", "v3"), ("V4-5", "v4"), ("S11", "v3"), ("S11", "v4")],
     "CHANGES_v4.md spec-text blocks: %r" % [(s_, v) for s_, v, t in spec_texts])
R3, R4, C3, C4 = [t for s_, v, t in spec_texts]
need("note ᵇ" in seq["V4-3"][0][2] and "note ᶜ" in seq["V4-3"][2][2] and "Table 9 caption" in seq["V4-3"][4][2]
     and "E5's" in seq["V4-6"][0][2] and "Note ᵃ" in seq["V4-6"][2][2], "CHANGES_v4.md: labels of V4-3 and V4-6")


def prs(s_):
    v = seq[s_]
    need(len(v) % 2 == 0 and all(v[q][0] == "O" and v[q + 1][0] == "N" for q in range(0, len(v), 2)), s_)
    return [(v[q][1], v[q + 1][1]) for q in range(0, len(v), 2)]


V41, V42, V43, V44, V45, V46 = prs("V4-1"), prs("V4-2"), prs("V4-3"), prs("V4-4"), prs("V4-5"), prs("V4-6")
V47, V48, V49, V410, V411, V412 = prs("V4-7"), prs("V4-8"), prs("V4-9"), prs("V4-10"), prs("V4-11"), prs("V4-12")
ALL = V41 + V42 + V43 + V44 + V45 + V46 + V47 + V48 + V49 + V410 + V411 + V412
need(len(ALL) == 15, "pair count")
INS_TEXT, INS_LABEL = seq["V4-13"][0][1], seq["V4-13"][0][2]
INS_AFTER = one(re.findall(r"which ends `([^`]+)`", INS_LABEL), "V4-13: the end of the Version 3 sentence")
INS_BEFORE = one(re.findall(r"and before `([^`]+)`", INS_LABEL), "V4-13: the text that follows the new sentence")

# the order holds every quoted printed text (wrapped lines joined by one space)
order = read_checked(ORDER, ORDER_SHA, "fix_order_v4.md")
flat_order = " ".join(x.strip() for x in order.split("\n"))
for s_, kind, text, label in items:
    need(text in flat_order, "%s %s text not in the order: %r" % (s_, kind, text[:80]))


def apply(text, pairs, what):
    for o, n in pairs:
        need(text.count(o) == 1, "%s: OLD found %d times: %r" % (what, text.count(o), o[:70]))
        text = text.replace(o, n)
    return text


# ------------------------------------------------------------------ version 3 of the scripts
with open(BT, "rb") as f:
    bt_raw = f.read()
need(hashlib.sha256(bt_raw).hexdigest() == BT3_SHA, "build_tables.py is not version 3 (SHA-256)")
src3 = bt_raw.decode("utf-8")
with open(VC, "rb") as f:
    vc_raw = f.read()
need(hashlib.sha256(vc_raw).hexdigest() == VC3_SHA, "verify_constants.py is not version 3 (SHA-256)")
vc3 = vc_raw.decode("utf-8")
need(b"\r" not in bt_raw and b"\r" not in vc_raw, "a script has CR bytes")
ms = importlib.util.spec_from_file_location("bt3", BT)
bt3 = importlib.util.module_from_spec(ms)
ms.loader.exec_module(bt3)
need("Version 4" not in bt3.HEADER_COMMENT, "build_tables.py is already version 4")

new = {}
print("texts taken from the spec (each checked against the version-3 constant and the order's OLD/NEW texts):")

# V4-13: the header comment (the sentence inserted directly after the Version 3 sentence)
h3 = bt3.HEADER_COMMENT
fe = "the nowcast of each problem."
x = fenced_line(h3[:h3.index(fe) + len(fe)], "HEADER_COMMENT", h3)
anchor = INS_AFTER + " " + INS_BEFORE
need(h3.count(anchor) == 1, "HEADER_COMMENT: the V4-13 anchor found %d times" % h3.count(anchor))
v3s = h3[h3.index("Version 3 ("):h3.index(anchor) + len(INS_AFTER)]
need(h3.count("Version 3 (") == 1 and ". " not in v3s, "HEADER_COMMENT: the anchor does not end the Version 3 sentence")
need(x == h3.replace(anchor, INS_AFTER + " " + INS_TEXT + " " + INS_BEFORE), "HEADER_COMMENT: not the ordered insertion")
new["HEADER_COMMENT"] = x

# V4-3 and V4-4: the Table 9 caption
x = fenced_line(bt3.CAP9[:24], "CAP9", bt3.CAP9)
need(x == apply(bt3.CAP9, [V43[2], V44[0]], "CAP9"), "CAP9: not the ordered change")
new["CAP9"] = x

# V4-12: the S3.18 caption (its source comment)
x = fenced_line(bt3.CAP18[:24], "CAP18", bt3.CAP18)
need(x == apply(bt3.CAP18, V412, "CAP18"), "CAP18: not the ordered change")
new["CAP18"] = x

# V4-7: the S3.18 panel b table (block 15), found by position: the block right after the unchanged panel b label;
# its first line starts differently now
ib = one([q for q, b in enumerate(blocks) if b[1] == [bt3.LAB18B]], "S3.18 panel b label block")
need(blocks3[ib][1] == [bt3.LAB18B] and blocks3[ib + 1][1] == bt3.TAB18B and blocks3[ib + 2][1] == bt3.NOTES18,
     "S3.18 b: the script's version-3 label, table and notes are not the version-3 spec's blocks")
t18 = blocks[ib + 1][1]
need(len(t18) == len(bt3.TAB18B) and t18[1:] == bt3.TAB18B[1:] and t18[0] == apply(bt3.TAB18B[0], V47, "TAB18B[0]"),
     "TAB18B: not (the header line reworded, the rest unchanged)")
need(blocks[ib + 2][1] == bt3.NOTES18, "S3.18 notes changed")
used_blocks[ib + 2] = blocks[ib + 1][0]
used_lines.add(blocks[ib + 1][0] + 1)
print("  %-24s spec block at line %d (block %d, %d lines; header line %d)" % ("TAB18B", blocks[ib + 1][0], ib + 2,
                                                                             len(t18), blocks[ib + 1][0] + 1))
new["TAB18B"] = list(t18)

# V4-3: S3.19 notes b and c (block 19, found by its unchanged note a)
q19 = one([q for q, b in enumerate(blocks) if len(b[1]) == 4 and b[1][0] == bt3.NOTES19[0]], "S3.19 notes")
need(blocks3[q19][1] == bt3.NOTES19, "NOTES19: the script's version-3 lines are not the version-3 spec's block")
n19 = blocks[q19][1]
need([n19[q] for q in (0, 3)] == [bt3.NOTES19[q] for q in (0, 3)]
     and n19[1] == apply(bt3.NOTES19[1], [V43[0]], "NOTES19 note b")
     and n19[2] == apply(bt3.NOTES19[2], [V43[1]], "NOTES19 note c"),
     "NOTES19: not (notes b and c reworded, the rest unchanged)")
used_blocks[q19 + 1] = blocks[q19][0]
used_lines.update([blocks[q19][0] + 2, blocks[q19][0] + 3])
print("  %-24s spec block at line %d (block %d; notes b and c at lines %d and %d)" % (
    "NOTES19", blocks[q19][0], q19 + 1, blocks[q19][0] + 2, blocks[q19][0] + 3))
new["NOTES19"] = list(n19)


# V4-1, V4-2, V4-6, V4-10, V4-11: the S3.21 rows (the row table of 4.5: gate cell, "What it checks", problem cell)
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


g4, g3 = gate_table(SL, "S3.21 row table (v4)"), gate_table(SL3, "S3.21 row table (v3)")
need([r[0] for r in g4] == [r[0] for r in g3] and len(g4) == len(bt3.GATE_ROWS), "S3.21 row tables")
gate_rows, changed_keys, used = [], [], []
for (ln, g, w, rule), (ln3, g_3, w_3, rule3), (key, gs, ws) in zip(g4, g3, bt3.GATE_ROWS):
    need((g_3, w_3) == (gs, ws), "S3.21 row %s: the script's version-3 cells are not the version-3 spec's" % key)
    pw = [pr for pr in ALL if pr[0] in ws]
    need(g == gs, "S3.21 row %s: the gate cell changed" % key)
    need(w == apply(ws, pw, "S3.21 " + key), "S3.21 row %s: the spec's cell is not the ordered change" % key)
    need(key == "kept" or rule == rule3, "S3.21 row %s: its problem-cell rule changed" % key)
    if pw:
        changed_keys.append(key)
        used_lines.add(ln)
    used += pw
    gate_rows.append((key, g, w))
need(changed_keys == ["E3a", "E3m", "E3", "E5", "E8"], "S3.21 changed rows %r" % changed_keys)
need(sorted(used) == sorted([V42[0], V41[0], V410[0], V46[0], V411[0]]),
     "S3.21: the order's five S3.21 texts are not each used once")
print("  %-24s spec lines %d-%d (changed: %s)" % ("GATE_ROWS", g4[0][0], g4[-1][0], ", ".join(
    "%s line %d" % (r[1], r[0]) for r, k in zip(g4, bt3.GATE_ROWS) if k[0] in changed_keys)))
new["GATE_ROWS"] = gate_rows

# V4-5: the answer-type words of the rule of the Adopted arm row (the rule is the row's third cell)
ln_k, g_k, w_k, rule_k = g4[0]
rule_k3 = g3[0][3]
need(g_k == "Adopted arm" and bt3.GATE_ROWS[0][0] == "kept", "the first S3.21 row is not the Adopted arm row")
need(rule_k3.count(R3) == 1 and rule_k == rule_k3.replace(R3, R4),
     "Adopted arm rule: not the version-3 rule with CHANGES_v4.md's answer-type part replaced")
RX_TK = r'\("([^"]+)" if R `table_kind` == plain, "([^"]+)" if corrector\)'
rw4 = one(re.findall(RX_TK, rule_k), "answer-type words of the spec's rule (v4)")
rw3 = one(re.findall(RX_TK, rule_k3), "answer-type words of the spec's rule (v3)")
need(rw4[1] == rw3[1] and rw4[0] != rw3[0], "answer type: not exactly the plain arm's words changed")
need(V45[0][0].count(rw3[0]) == 1 and V45[0][0].replace(rw3[0], rw4[0]) == V45[0][1],
     "the order's NDVI cell is not the version-3 cell with the rule's new words")
tree3 = ast.parse(src3)
fn3 = one([n for n in tree3.body if isinstance(n, ast.FunctionDef) and n.name == "build_s321"], "build_s321")
tk3 = one([n for n in ast.walk(fn3) if isinstance(n, ast.Assign) and len(n.targets) == 1
           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "tk"], "tk in build_s321")
need(ast.literal_eval(tk3.value) == {"plain": rw3[0], "corrector": rw3[1]},
     "the script's answer-type words are not the version-3 rule's")
used_lines.add(ln_k)
print("  %-24s spec line %d: %r for a plain arm (was %r); %r unchanged" % ("answer type (V4-5)", ln_k, rw4[0], rw3[0],
                                                                         rw4[1]))

# V4-6: S3.21 note a (block 26, found by the unchanged start of its first line)
q21 = one([q for q, b in enumerate(blocks) if len(b[1]) == 2 and b[1][0].startswith(bt3.NOTES21[0][:24])],
          "S3.21 notes")
need(blocks3[q21][1] == bt3.NOTES21, "NOTES21: the script's version-3 lines are not the version-3 spec's block")
n21 = blocks[q21][1]
need(n21[1] == bt3.NOTES21[1] and n21[0] == apply(bt3.NOTES21[0], [V46[1]], "NOTES21 note a"),
     "NOTES21: not (note a reworded, the rest unchanged)")
used_blocks[q21 + 1] = blocks[q21][0]
used_lines.add(blocks[q21][0] + 1)
print("  %-24s spec block at line %d (block %d; note a at line %d)" % ("NOTES21", blocks[q21][0], q21 + 1,
                                                                      blocks[q21][0] + 1))
new["NOTES21"] = list(n21)

# V4-9: the S3.28 caption
x = fenced_line(bt3.CAP28[:24], "CAP28", bt3.CAP28)
need(x == apply(bt3.CAP28, V49, "CAP28"), "CAP28: not the ordered change")
new["CAP28"] = x

# V4-8: the S3.22 row label (the row table of 4.6, the row whose cell is AW4 cross_link_models)
RX_22 = r"^\| `([^`]+)` \| AW4 `cross_link_models` as a model list \|$"
h22 = one([(n + 1, re.match(RX_22, x).group(1)) for n, x in enumerate(SL) if re.match(RX_22, x)], "S3.22 label (v4)")
h22_3 = one([(n + 1, re.match(RX_22, x).group(1)) for n, x in enumerate(SL3) if re.match(RX_22, x)], "S3.22 label (v3)")
need(h22[0] == h22_3[0], "S3.22 label: the line moved")
cross4, cross3 = h22[1], h22_3[1]
mo_cross = one(list(re.finditer(r'"cross": ("[^"\\]*")', src3)), "S3.22 cross label in the script")
need(json.loads(mo_cross.group(1)) == cross3, "S3.22 label: the script's is not the version-3 spec's")
need(cross4 == apply(cross3, V48, "S3.22 label"), "S3.22 label: not the ordered change")
used_lines.add(h22[0])
print("  %-24s spec line %d" % ("S3.22 label", h22[0]))

# S11: the contents line (nothing printed)
ln_c = one([n + 1 for n in range(1368) if SL3[n].count(C3) == 1 and SL[n] == SL3[n].replace(C3, C4)],
           "the contents line (S11)")
print("  %-24s spec line %d (not printed)" % ("contents line (S11)", ln_c))

# coverage: the blocks used are CHANGES_v4.md's table; the lines used and the contents line are every line of
# sections 0 to 10 that differs; every other block is unchanged
fb = {}
for x in CH:
    mo = re.match(r"^\| (\d+) \| (\d+) \| ", x)
    if mo:
        fb[int(mo.group(1))] = int(mo.group(2))
need(fb == used_blocks, "blocks used %r, CHANGES_v4.md's table %r" % (sorted(used_blocks.items()), sorted(fb.items())))
for q in range(63):
    need(q + 1 in used_blocks or blocks[q][1] == blocks3[q][1], "block %d changed but is not used" % (q + 1))
diff_lines = [n + 1 for n in range(1368) if SL[n] != SL3[n]]
need(diff_lines == sorted(used_lines | {ln_c}), "changed spec lines %r; used %r" % (diff_lines, sorted(used_lines)))
need(SL[1368] == "" and SL[1369] == "---" and SL[1371].startswith("## 11. Version 4"), "section 11 not where expected")
print("blocks used (CHANGES_v4.md's table): %s" % ", ".join("%d (L%d)" % kv for kv in sorted(used_blocks.items())))
print("changed spec lines of sections 0 to 10 (all used or the contents line): %s" % ", ".join(map(str, diff_lines)))


# ------------------------------------------------------------------ the new sources
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


spans = {}
for node in tree3.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        nm = node.targets[0].id
        need(nm not in spans, "%s assigned twice" % nm)
        spans[nm] = (node.lineno, node.end_lineno)
REPL = ["HEADER_COMMENT", "CAP9", "CAP18", "TAB18B", "NOTES19", "GATE_ROWS", "NOTES21", "CAP28"]
for nm in REPL:
    need("\n".join(stmt(nm, getattr(bt3, nm))) == "\n".join(src3.split("\n")[spans[nm][0] - 1:spans[nm][1]]),
         "%s: the version-3 statement is not in the patch's layout" % nm)
lines = src3.split("\n")
for a, b, repl in sorted([(spans[nm][0], spans[nm][1], stmt(nm, new[nm])) for nm in REPL], key=lambda e: -e[0]):
    lines[a - 1:b] = repl
src4 = "\n".join(lines)
src4 = sub1(src4, '                tk = {"plain": %s, "corrector": %s}\n' % (lit(rw3[0]), lit(rw3[1])),
            "                # answer-type words: the rule of the Adopted arm row (spec 4.5; version 4, V4-5)\n"
            '                tk = {"plain": %s, "corrector": %s}\n' % (lit(rw4[0]), lit(rw4[1])), "answer-type words")
src4 = sub1(src4, '"cross": ' + mo_cross.group(1), '"cross": ' + lit(cross4), "S3.22 label")
src4 = sub1(src4, "# of the source label's M (V3-6).\n",
            "# of the source label's M (V3-6).\n"
            "# Version 4 (2026-11-17): the texts changed by spec version 4 (V4-1 to V4-13, taken from the spec by\n"
            "# x11_patch_v4.py), among them the answer-type words of the rule of the S3.21 Adopted arm row (V4-5).\n",
            "script header")
compile(src4, BT, "exec")

# checks of the patched module
tmp = {"__name__": "bt4", "__file__": BT}
exec(compile(ast.parse(src4), BT, "exec"), tmp)  # defines only; main() runs under __main__ only
for nm in REPL:
    need(tmp[nm] == new[nm], "%s differs after the patch" % nm)
others = [n for n in spans if n not in REPL and isinstance(getattr(bt3, n), (str, list, dict, tuple, set))]
for nm in others:
    need(tmp[nm] == getattr(bt3, nm), "%s changed, but it is not in the order" % nm)
print("other module-level texts and lists unchanged: %d" % len(others))
tree4 = ast.parse(src4)
fn4 = one([n for n in tree4.body if isinstance(n, ast.FunctionDef) and n.name == "build_s321"], "build_s321 (v4)")
tk4 = one([n for n in ast.walk(fn4) if isinstance(n, ast.Assign) and len(n.targets) == 1
           and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "tk"], "tk (v4)")
need(ast.literal_eval(tk4.value) == {"plain": rw4[0], "corrector": rw4[1]}, "answer-type words after the patch")
fn22 = one([n for n in tree4.body if isinstance(n, ast.FunctionDef) and n.name == "build_s322"], "build_s322 (v4)")
first = one([ast.literal_eval(n.value) for n in ast.walk(fn22) if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "first"], "first (v4)")
need(first["cross"] == cross4, "S3.22 label after the patch")
for o, n in ALL:
    for fo, fn_ in ((o, n), (json.dumps(o, ensure_ascii=False)[1:-1], json.dumps(n, ensure_ascii=False)[1:-1])):
        need(src4.count(fo) == src4.count(fn_) * fn_.count(fo), "OLD text left in the script: %r" % o[:60])
need(lit(rw3[0]) not in src4, "the version-3 answer-type words are left in the script")

# verify_constants.py: the S3.22 label of its list of constant cells (V4-8); the check of the answer-type words (V4-5)
VC_BLOCK = r'''# version 4 (V4-5): the answer-type words of build_s321 (its dict tk) against the rule of the Adopted arm row in the
# spec's row table of 4.5, ("..." if R `table_kind` == plain, "..." if corrector); no check read these words before
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_s321"]
tks = [ast.literal_eval(n.value) for n in (ast.walk(fn[0]) if len(fn) == 1 else [])
       if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
       and n.targets[0].id == "tk"]
ra = [x for x in SL if x.startswith("| `Adopted arm` | ")]
rw = re.findall(r'\("([^"]+)" if R `table_kind` == plain, "([^"]+)" if corrector\)', ra[0]) if len(ra) == 1 else []
if len(tks) != 1 or len(rw) != 1:
    problems.append("Adopted arm row of 4.5: the script's answer-type words or the spec's rule not found once")
elif tks[0] != {"plain": rw[0][0], "corrector": rw[0][1]}:
    problems.append("answer-type words: the script has %r, the spec's rule of 4.5 %r" % (tks[0], rw[0]))
'''
vc4 = sub1(vc3, lit(cross3), lit(cross4), "verify_constants.py: the S3.22 label of the list")
vc4 = sub1(vc4, 'print("problems: %d" % len(problems))\n', VC_BLOCK + 'print("problems: %d" % len(problems))\n',
           "verify_constants.py: the end of the checks")
vc4 = sub1(vc4, "# and P, and its example composed by pair_link_text).\n",
           "# and P, and its example composed by pair_link_text).\n"
           "# Version 4 (2026-11-17): the list of constant cells holds the version-4 S3.22 row label (V4-8); one check added\n"
           "# for what version 4 changed: the answer-type words of the rule of S3.21's Adopted arm row (V4-5), which no check\n"
           "# read before.\n", "verify_constants.py header")
compile(vc4, VC, "exec")
need(vc4.count(lit(cross4)) == 1 and lit(cross3) not in vc4, "verify_constants.py: S3.22 label after the patch")

with open(BT, "w", encoding="utf-8", newline="\n") as f:
    f.write(src4)
with open(VC, "w", encoding="utf-8", newline="\n") as f:
    f.write(vc4)
for name, a, b in (("build_tables.py", src3, src4), ("verify_constants.py", vc3, vc4)):
    print("%s written: %d -> %d lines; sha256 %s" % (name, a.count("\n"), b.count("\n"),
                                                     hashlib.sha256(b.encode("utf-8")).hexdigest()))
    print("diff (v3 -> v4):")
    for d in difflib.unified_diff(a.split("\n"), b.split("\n"), name + " v3", name + " v4", n=0, lineterm=""):
        print(d)
