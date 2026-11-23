# -*- coding: utf-8 -*-
# One-off patch of build_tables.py for version 3 of the spec (it refuses to run on an already patched file).
# Every changed fixed text is TAKEN FROM OUT\spec\TABLE_SPEC.md (version 3; its SHA-256 is checked), never typed here.
# The change order's OLD and NEW printed texts, as OUT\spec\CHANGES_v3.md quotes them (27 OLD, 28 NEW; SHA-256
# checked), serve only as a check: each new spec text must be the version-2 constant with exactly the ordered
# replacements, and the order itself (OUT\_brief\fix_order_v3.md, wrapped lines joined by one space) must hold every
# quoted text.
# V3-1: the Table 9, S3.19 and S3.29 captions; the two values of {shares_sentence}. V3-2: the S3.18 caption with its
# source comment, the panel b label, the baselines row and the first note line. V3-3: the S3.23-S3.27 caption
# template's count clause; {extra_src}. V3-4: the NDVI note. V3-5: the S3.22 row label. V3-6: treeroute's skill-guard
# cell (S3.18 a, S3.20); the random forest's "Model and SHAP method"; S3.19 note c; the S3.21 rows Adopted arm, E3a,
# E3m, E3, E6 and E10; the Link cell of S3.23-S3.27 printed with P (the spec's printed words) in place of M (the source
# label's words). V3-7: the header comment.
# Writes only build_tables.py (UTF-8, LF) and prints the diff of the script.
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
CHG = os.path.join(OUT, "spec", "CHANGES_v3.md")
ORDER = os.path.join(OUT, "_brief", "fix_order_v3.md")
BT = os.path.join(HERE, "build_tables.py")
SPEC_SHA = "573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31"
CHG_SHA = "2434769ea8af74d55aa8a39a74894f64b3464773312ee27a6d82d2e4fa2bebc1"
ORDER_SHA = "0b611c43dae32557871f489f5fbd67a3bf3680d6bf6371ba78f126f54300d0a5"


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
    need(b"\r" not in raw, "%s has CR bytes" % what)
    return raw.decode("utf-8")


# ------------------------------------------------------------------ the spec (version 3)
spec = read_checked(SPEC, SPEC_SHA, "TABLE_SPEC.md (version 3)")
SL = spec.split("\n")
blocks = []  # (1-based line of the opening fence, [content lines])
cur = None
for i, line in enumerate(SL, 1):
    if line.startswith("```"):
        if cur is None:
            cur = (i, [])
        else:
            blocks.append(cur)
            cur = None
        continue
    if cur is not None:
        cur[1].append(line)
need(cur is None and len(blocks) == 63, "fenced blocks: %d" % len(blocks))


def fenced_line(prefix, what):
    hits = [(b[0] + 1 + k, x) for b in blocks for k, x in enumerate(b[1]) if x.startswith(prefix)]
    ln, x = one(hits, what)
    print("  %-24s spec line %d" % (what, ln))
    return x


def spec_line(rx, what):
    hits = [(i + 1, re.match(rx, x)) for i, x in enumerate(SL)]
    ln, mo = one([(i, mo) for i, mo in hits if mo], what)
    print("  %-24s spec line %d" % (what, ln))
    return mo


# ------------------------------------------------------------------ the order's OLD and NEW texts (CHANGES_v3.md)
CH = read_checked(CHG, CHG_SHA, "CHANGES_v3.md").split("\n")
items = []
sec = None
i = 0
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
            kind = "O" if "OLD printed text" in label else ("N" if "NEW printed text" in label else None)
            need(kind is not None and len(body) == 1, "CHANGES_v3.md block at line %d: %r" % (i + 1, label))
            items.append((sec, kind, body[0], label))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text, label in items:
    seq.setdefault(s_, []).append((kind, text, label))
want = {"V3-1": "NONONONONONON", "V3-2": "ONONONONON", "V3-3": "ONON", "V3-4": "ON", "V3-5": "ON",
        "V3-6": "ONONONONONONONONONON", "V3-7": "ONON"}
got = {s_: "".join(k for k, t, lab in v) for s_, v in seq.items()}
need(got == want, "CHANGES_v3.md printed-text blocks: %r" % got)
need(sum(k == "O" for s_, k, t, lab in items) == 27 and sum(k == "N" for s_, k, t, lab in items) == 28,
     "CHANGES_v3.md: not 27 OLD and 28 NEW texts")


def prs(s_, skip=0):
    v = seq[s_][skip:]
    need(len(v) % 2 == 0 and all(v[q][0] == "O" and v[q + 1][0] == "N" for q in range(0, len(v), 2)), s_)
    return [(v[q][1], v[q + 1][1]) for q in range(0, len(v), 2)]


INS_TEXT, INS_LABEL = seq["V3-1"][0][1], seq["V3-1"][0][2]
INS_ANCHOR = one(re.findall(r"directly after `([^`]+)`", INS_LABEL), "Table 9 insertion anchor")
V31, V32, V33, V34 = prs("V3-1", 1), prs("V3-2"), prs("V3-3"), prs("V3-4")
V35, V36, V37 = prs("V3-5"), prs("V3-6"), prs("V3-7")
need([len(x) for x in (V31, V32, V33, V34, V35, V36, V37)] == [6, 5, 2, 1, 1, 10, 2], "pair counts")

# the order holds every quoted text (wrapped lines joined by one space), except CHANGES_v3.md's example of a
# composed Link cell, for which the order gives the pair-label words M and P (checked below)
order = read_checked(ORDER, ORDER_SHA, "fix_order_v3.md")
flat_order = " ".join(x.strip() for x in order.split("\n"))
for s_, kind, text, label in items:
    if s_ == "V3-6" and text in V36[9]:
        continue
    need(text in flat_order, "%s %s text not in the order: %r" % (s_, kind, text[:80]))
need(INS_ANCHOR in flat_order, "insertion anchor not in the order")


def apply(text, pairs, what):
    for o, n in pairs:
        need(text.count(o) == 1, "%s: OLD found %d times: %r" % (what, text.count(o), o[:70]))
        text = text.replace(o, n)
    return text


# ------------------------------------------------------------------ version 2 of the script
with open(BT, "rb") as f:
    src_raw = f.read()
need(b"\r" not in src_raw, "build_tables.py has CR bytes")
src2 = src_raw.decode("utf-8")
ms = importlib.util.spec_from_file_location("bt2", BT)
bt2 = importlib.util.module_from_spec(ms)
ms.loader.exec_module(bt2)
need(hasattr(bt2, "SHARES_DE") and "Version 3" not in bt2.HEADER_COMMENT, "build_tables.py is not version 2")

new = {}
print("texts taken from the spec (each checked against the version-2 constant and the order's OLD/NEW texts):")

# V3-7: the header comment
fe = "the nowcast of each problem."
x = fenced_line(bt2.HEADER_COMMENT[:bt2.HEADER_COMMENT.index(fe) + len(fe)], "HEADER_COMMENT")
need(x == apply(bt2.HEADER_COMMENT, V37, "HEADER_COMMENT"), "HEADER_COMMENT: not the ordered change")
new["HEADER_COMMENT"] = x

# V3-1: Table 9 (insertion after its anchor, RBO, own-history share), S3.19, S3.29
x = fenced_line(bt2.CAP9[:24], "CAP9")
exp = apply(bt2.CAP9, [(INS_ANCHOR + " ", INS_ANCHOR + " " + INS_TEXT + " "), V31[0], V31[1]], "CAP9")
need(x == exp, "CAP9: not the ordered change")
new["CAP9"] = x
x = fenced_line(bt2.CAP19[:24], "CAP19")
need(x == apply(bt2.CAP19, [V31[2]], "CAP19"), "CAP19: not the ordered change")
new["CAP19"] = x
x = fenced_line(bt2.CAP29[:24], "CAP29")
need(x == apply(bt2.CAP29, [V31[5]], "CAP29"), "CAP29: not the ordered change")
new["CAP29"] = x
kb = one([i for i, x in enumerate(SL) if x.startswith("- `{shares_sentence}`")], "shares_sentence bullet")
need("fire and coral" in SL[kb], "shares bullet: first value is not fire and coral's")
m1 = re.match(r"^  `([^`]+)`;$", SL[kb + 1])
m2 = re.match(r"^  `([^`]+)`$", SL[kb + 3])
need(m1 is not None and m2 is not None and SL[kb + 2] == "  else (pm25, ndvi, defo)", "shares bullet layout")
print("  %-24s spec line %d" % ("SHARES_DEG", kb + 2))
print("  %-24s spec line %d" % ("SHARES_DE", kb + 4))
need(m1.group(1) == apply(bt2.SHARES_DEG, [V31[4]], "SHARES_DEG"), "SHARES_DEG: not the ordered change")
need(m2.group(1) == apply(bt2.SHARES_DE, [V31[3]], "SHARES_DE"), "SHARES_DE: not the ordered change")
new["SHARES_DEG"], new["SHARES_DE"] = m1.group(1), m2.group(1)

# V3-2: Table S3.18 caption; panel b label (block 14, a new first line: the block right before the panel b table,
# found by its unchanged header line); the baselines row (block 15); the notes (block 16, right after it)
x = fenced_line(bt2.CAP18[:24], "CAP18")
need(x == apply(bt2.CAP18, [V32[0], V32[1]], "CAP18"), "CAP18: not the ordered change")
new["CAP18"] = x
ib = one([j for j, b in enumerate(blocks) if b[1] and b[1][0] == bt2.TAB18B[0]], "S3.18 panel b block")
print("  %-24s spec block at line %d (%d lines)" % ("LAB18B", blocks[ib - 1][0], len(blocks[ib - 1][1])))
print("  %-24s spec block at line %d (%d lines)" % ("TAB18B", blocks[ib][0], len(blocks[ib][1])))
print("  %-24s spec block at line %d (%d lines)" % ("NOTES18", blocks[ib + 1][0], len(blocks[ib + 1][1])))
l18, t18, n18 = list(blocks[ib - 1][1]), list(blocks[ib][1]), list(blocks[ib + 1][1])
need(len(l18) == 1 and l18[0] == apply(bt2.LAB18B, [V32[2]], "LAB18B"), "LAB18B: not the ordered change")
need(len(t18) == 10 and t18[:9] == bt2.TAB18B[:9] and t18[9] == apply(bt2.TAB18B[9], [V32[3]], "TAB18B row"),
     "TAB18B: not (the baselines row reworded, the rest unchanged)")
need(len(n18) == 3 and n18[1:] == bt2.NOTES18[1:] and n18[0] == apply(bt2.NOTES18[0], [V32[4]], "NOTES18 line 1"),
     "NOTES18: not (the first line reworded, the rest unchanged)")
new["LAB18B"], new["TAB18B"], new["NOTES18"] = l18[0], t18, n18

# V3-6: S3.19 note c (the notes block found by its unchanged note a)
b19 = one([b for b in blocks if len(b[1]) == 4 and b[1][0] == bt2.NOTES19[0]], "S3.19 notes")
print("  %-24s spec block at line %d (%d lines)" % ("NOTES19", b19[0], len(b19[1])))
n19 = list(b19[1])
need([n19[q] for q in (0, 1, 3)] == [bt2.NOTES19[q] for q in (0, 1, 3)]
     and n19[2] == apply(bt2.NOTES19[2], [V36[3]], "NOTES19 note c"), "NOTES19: not (note c reworded, the rest unchanged)")
new["NOTES19"] = n19

# V3-3: the S3.23-S3.27 caption template and {extra_src}
x = fenced_line(bt2.CAP_AW3[:24], "CAP_AW3")
need(x == apply(bt2.CAP_AW3, [V33[0]], "CAP_AW3"), "CAP_AW3: not the ordered change")
need(re.findall(r"\{[a-z_]+\}", x) == re.findall(r"\{[a-z_]+\}", bt2.CAP_AW3), "CAP_AW3: placeholders differ")
new["CAP_AW3"] = x
mo = spec_line(r"^- `\{extra_src\}`: ndvi `([^`]+)`;$", "EXTRA_SRC_NDVI")
need(mo.group(1) == apply(bt2.EXTRA_SRC_NDVI, [V33[1]], "EXTRA_SRC_NDVI"), "EXTRA_SRC_NDVI: not the ordered change")
new["EXTRA_SRC_NDVI"] = mo.group(1)

# V3-4: the NDVI note (placeholders, their values and order unchanged; one text part changes)
tmpl2 = "".join(("{" + t + "}") if t in bt2.NOTE_NDVI_SLOTS else t for t in bt2.NOTE_NDVI_PARTS)
x = fenced_line(bt2.NOTE_NDVI_PARTS[0][:24], "NOTE_NDVI template")
need(x == apply(tmpl2, V34, "NOTE_NDVI"), "NOTE_NDVI: not the ordered change")
toks = re.split(r"\{([a-z0-9_]+)\}", x)
need(len(toks) == len(bt2.NOTE_NDVI_PARTS) and toks[1::2] == bt2.NOTE_NDVI_PARTS[1::2], "ndvi note: placeholders differ")
need(all(t != "" for t in toks[0::2]), "ndvi note: two placeholders in a row")
diff_at = [q for q in range(len(toks)) if toks[q] != bt2.NOTE_NDVI_PARTS[q]]
need(len(diff_at) == 1 and bt2.NOTE_NDVI_PARTS[diff_at[0] - 1] == "j_feat", "ndvi note: changed parts %r" % diff_at)
new["NOTE_NDVI_PARTS"] = toks

# V3-6: the S3.21 rows (the row table of 4.5: gate cell and "What it checks", in the order of GATE_ROWS)
hi = one([q for q, x in enumerate(SL) if x == "| Gate cell | What it checks | Problem cell |"], "S3.21 row table")
need(SL[hi + 1] == "|---|---|---|", "S3.21 row table separator")
srows = []
q = hi + 2
while SL[q].startswith("| "):
    mo = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| (.+) \|$", SL[q])
    need(mo is not None, "S3.21 row table line %d" % (q + 1))
    srows.append((mo.group(1), mo.group(2)))
    q += 1
print("  %-24s spec lines %d-%d" % ("GATE_ROWS", hi + 3, q))
need(len(srows) == len(bt2.GATE_ROWS), "S3.21: %d spec rows, %d in the script" % (len(srows), len(bt2.GATE_ROWS)))
gate_rows, changed_keys, used = [], [], []
for (g, w), (key, g2, w2) in zip(srows, bt2.GATE_ROWS):
    pg = [pr for pr in V36 if pr[0] in g2]
    pw = [pr for pr in V36 if pr[0] in w2]
    need(g == apply(g2, pg, "gate cell " + key) and w == apply(w2, pw, "gate what " + key),
         "S3.21 row %s: the spec's cells are not the ordered change" % key)
    if pg or pw:
        changed_keys.append(key)
    used += pg + pw
    gate_rows.append((key, g, w))
need(changed_keys == ["kept", "E3a", "E3m", "E3", "E6", "E10"], "S3.21 changed rows %r" % changed_keys)
need(len(used) == 6 and len(set(used)) == 6, "S3.21: the order's six S3.21 texts are not each used once")
new["GATE_ROWS"] = gate_rows

# V3-6: the random forest's "Model and SHAP method" (the constants table of 4.2)
hm = one([q for q, x in enumerate(SL) if x == "| Model | Text |"], "constants table of 4.2")
smeth = {}
q = hm + 2
while SL[q].startswith("| "):
    mo = re.match(r"^\| (\w+) \| `([^`]+)` \|$", SL[q])
    need(mo is not None, "constants table line %d" % (q + 1))
    smeth[mo.group(1)] = mo.group(2)
    q += 1
print("  %-24s spec lines %d-%d" % ("SHAP_METHOD", hm + 3, q))
need(list(smeth) == bt2.MODELS, "constants table models")
meth_changed = []
for m in bt2.MODELS:
    pm = [pr for pr in V36 if pr[0] in bt2.SHAP_METHOD[m]]
    need(smeth[m] == apply(bt2.SHAP_METHOD[m], pm, "SHAP_METHOD " + m), "SHAP_METHOD %s: not the ordered change" % m)
    if pm:
        meth_changed.append(m)
need(meth_changed == ["rival_rf"], "SHAP_METHOD changed %r" % meth_changed)

# V3-6: treeroute's skill-guard cell of S3.18 a (4.2) and of S3.20 (4.4)
g42 = spec_line(r"^\| Skill guard at the nowcast \| treeroute: `([^`]+)`; a rival: ", "guard cell S3.18 a").group(1)
g44 = spec_line(r"^\| Skill guard \| treeroute: `([^`]+)`; a rival: ", "guard cell S3.20").group(1)
need(g42 == g44 == apply(V36[0][0], [V36[0]], "guard cell"), "treeroute guard cell: not the ordered change")

# V3-5: the S3.22 row label (the row table of 4.6, the row whose cell is AW4 cross_link_models)
cross = spec_line(r"^\| `([^`]+)` \| AW4 `cross_link_models` as a model list \|$", "S3.22 label").group(1)

# V3-6: the Link cell rule of 4.7 (M: the source label's words; P: the printed words) and its example
rl = spec_line(r"^\| Link \| - \| from the pair's `pair_label` ", "Link cell rule").string
M = one(re.findall(r'\bM = "([^"]*)"', rl), "M of the Link rule")
P = one(re.findall(r'\bP = "([^"]*)"', rl), "P of the Link rule")
ex_label, ex_print = one(re.findall(r"So `([^`]+)` prints `([^`]+)`", rl), "Link rule example")
need(("OLD: `%s` NEW: `%s`" % (M, P)) in flat_order, "M and P are not the order's OLD and NEW pair-label texts")
need(V36[9][0].count(M) == 1 and V36[9][0].replace(M, P) == V36[9][1], "the order's Link example is not M -> P")


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


tree = ast.parse(src2)
spans = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        nm = node.targets[0].id
        need(nm not in spans, "%s assigned twice" % nm)
        spans[nm] = (node.lineno, node.end_lineno)
lines = src2.split("\n")
REPL = ["HEADER_COMMENT", "CAP9", "CAP18", "LAB18B", "TAB18B", "NOTES18", "CAP19", "NOTES19", "GATE_ROWS", "CAP_AW3",
        "SHARES_DEG", "SHARES_DE", "EXTRA_SRC_NDVI", "NOTE_NDVI_PARTS", "CAP29"]
edits = sorted([(spans[nm][0], spans[nm][1], stmt(nm, new[nm])) for nm in REPL], key=lambda e: -e[0])
for a, b, repl in edits:
    lines[a - 1:b] = repl
src3 = "\n".join(lines)


def sub1(src, old, rep, what, count=1):
    need(src.count(old) == count, "%s: anchor found %d times" % (what, src.count(old)))
    return src.replace(old, rep)


src3 = sub1(src3, '    "rival_rf": %s,\n' % lit(bt2.SHAP_METHOD["rival_rf"]), '    "rival_rf": %s,\n' % lit(smeth["rival_rf"]),
            "SHAP_METHOD rival_rf")
src3 = sub1(src3, lit(V36[0][0]), lit(g42), "treeroute guard cells (S3.18 a, S3.20)", count=2)
mo = one(list(re.finditer(r'"cross": ("[^"\\]*")', src3)), "S3.22 cross label in the script")
need(cross == apply(json.loads(mo.group(1)), V35, "S3.22 label"), "S3.22 label: not the ordered change")
src3 = sub1(src3, '"cross": ' + mo.group(1), '"cross": ' + lit(cross), "S3.22 label")
src3 = sub1(src3, "    M = %s\n" % lit(M),
            "    M = %s  # the source label's words (check 3.3)\n"
            "    P = %s  # the printed words (spec 4.7; version 3, V3-6)\n" % (lit(M), lit(P)), "pair_link_text M")
src3 = sub1(src3, '        return before + M + ", ".join(M_INL[x] for x in names)\n',
            '        return before + P + ", ".join(M_INL[x] for x in names)\n', "pair_link_text return")
src3 = sub1(src3, "# {shares_sentence} of the S3.23-S3.27 caption (version 2, C1):",
            "# {shares_sentence} of the S3.23-S3.27 caption (version 2, C1; version 3, V3-1):", "shares comment")
src3 = sub1(src3, "# and its source text formats (G2: the register, the logs and bardl_maxima.txt read as utf-8-sig).\n",
            "# and its source text formats (G2: the register, the logs and bardl_maxima.txt read as utf-8-sig).\n"
            "# Version 3 (2026-11-17): the texts changed by spec version 3 (V3-1 to V3-7, taken from the spec by\n"
            "# x09_patch_v3.py), and the Link cell of the S3.23-S3.27 pair panels printed with the spec's P in place\n"
            "# of the source label's M (V3-6).\n", "script header")
compile(src3, BT, "exec")

# checks of the patched module
tmp = {"__name__": "bt3", "__file__": BT}
exec(compile(ast.parse(src3), BT, "exec"), tmp)  # defines only; main() runs under __main__ only
for nm in REPL:
    need(tmp[nm] == new[nm], "%s differs after the patch" % nm)
need(tmp["SHAP_METHOD"]["rival_rf"] == smeth["rival_rf"] and dict(tmp["SHAP_METHOD"]) == smeth, "SHAP_METHOD after the patch")
need(tmp["pair_link_text"](ex_label) == ex_print, "pair_link_text does not give the spec's example")
need(tmp["pair_link_text"]("same-link") == "same-link", "pair_link_text changes a label without M")
need(src3.count(lit(g42)) == 2 and lit(V36[0][0]) not in src3, "guard cells after the patch")
need(src3.count('"cross": ' + lit(cross)) == 1, "S3.22 label after the patch")
left = [o for s_ in ("V3-1", "V3-2", "V3-3", "V3-4", "V3-5", "V3-6", "V3-7") for o, n in prs(s_, 1 if s_ == "V3-1" else 0)
        if o != V36[9][0] and (o in src3 or json.dumps(o, ensure_ascii=False)[1:-1] in src3)]
need(not left, "OLD texts left in the script: %r" % [o[:60] for o in left])

with open(BT, "w", encoding="utf-8", newline="\n") as f:
    f.write(src3)
print("build_tables.py written: %d -> %d lines" % (src2.count("\n"), src3.count("\n")))
print("diff (v2 -> v3):")
for d in difflib.unified_diff(src2.split("\n"), src3.split("\n"), "build_tables.py v2", "build_tables.py v3",
                              n=0, lineterm=""):
    print(d)
