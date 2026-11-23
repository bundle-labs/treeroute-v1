# -*- coding: utf-8 -*-
# One-off patch of build_tables.py for version 2 of the spec (it refuses to run on an already patched file).
# Every changed fixed text is TAKEN FROM OUT\spec\TABLE_SPEC.md (version 2; its SHA-256 is checked), never typed here:
# C1 (Table 9 caption; the S3.23-S3.27 caption template and the two values of {shares_sentence}; the S3.29 caption),
# C2 (S3.20 notes a and b), C3 (S3.24 note double dagger), C4 (S3.18 panel b and its notes; the S3.30 note),
# C5 (the S3.22 row label), C6 (E10's "What it checks"; S3.21 note a), C7 (the sign-agreement note), C8 (S3.22 note d),
# C9 (the header comment). Each new text is located through the version-1 text around it and checked against the
# version-1 constant it replaces: only the part the change order names may differ.
# Code changes: {shares_sentence} is filled in build_aw3; the register, the logs and bardl_maxima.txt are read with
# encoding utf-8-sig (G2), so the manual BOM strip of the maxima's first line goes.
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
BT = os.path.join(HERE, "build_tables.py")
SPEC_SHA = "2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02"


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


# ------------------------------------------------------------------ the spec (version 2)
with open(SPEC, "rb") as f:
    raw = f.read()
need(hashlib.sha256(raw).hexdigest() == SPEC_SHA, "the spec is not version 2 (SHA-256)")
spec = raw.decode("utf-8")
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
    print("  %-22s spec line %d" % (what, ln))
    return x


def block_where(pred, what):
    b = one([b for b in blocks if pred(b[1])], what)
    print("  %-22s spec block at line %d (%d lines)" % (what, b[0], len(b[1])))
    return list(b[1])


# ------------------------------------------------------------------ version 1 of the script
with open(BT, "rb") as f:
    src_raw = f.read()
need(b"\r" not in src_raw, "build_tables.py has CR bytes")
src1 = src_raw.decode("utf-8")
ms = importlib.util.spec_from_file_location("bt1", BT)
bt1 = importlib.util.module_from_spec(ms)
ms.loader.exec_module(bt1)
need(not hasattr(bt1, "SHARES_DE"), "build_tables.py is already patched")

new = {}
print("texts taken from the spec:")

# C9: the header comment: one sentence inserted after the first sentence
first_sentence_end = "the nowcast of each problem."
k = bt1.HEADER_COMMENT.index(first_sentence_end) + len(first_sentence_end)
h_pre, h_post = bt1.HEADER_COMMENT[:k], bt1.HEADER_COMMENT[k:]
x = fenced_line(h_pre, "HEADER_COMMENT")
need(x.endswith(h_post) and len(x) > len(bt1.HEADER_COMMENT), "header comment: not an insertion")
ins = x[len(h_pre):len(x) - len(h_post)]
need(ins.startswith(" Version 2 (2026-11-17") and ins.count(".") >= 1, "header comment: inserted text %r" % ins)
new["HEADER_COMMENT"] = x


def caption(name, a, b):
    """New caption: same text as version 1 before a and from b on; only the middle changes."""
    old = getattr(bt1, name)
    i, j = old.index(a) + len(a), old.index(b)
    x = fenced_line(old[:i], name)
    need(x.endswith(old[j:]), "%s: the text after the change differs" % name)
    need(x != old, "%s: unchanged" % name)
    return x, x[i:len(x) - len(old) + j]


# C1: Table 9, the S3.23-S3.27 template, S3.29
new["CAP9"], mid = caption("CAP9", "(the mean of their shares). ", " Percentile 95% intervals")
need(mid.startswith("Own-history share: "), "CAP9 middle %r" % mid)
new["CAP_AW3"], mid = caption("CAP_AW3", "not comparable in scale or rank. ", " <!-- src:")
need(mid == "{shares_sentence}", "CAP_AW3 middle %r" % mid)
new["CAP29"], mid = caption("CAP29", "(c, d; no interval for a top-k list). ", " From the independent re-computation")
need(mid.startswith("Top-3 and top-10 shares are of the B1 run's"), "CAP29 middle %r" % mid)
kb = one([i for i, x in enumerate(SL) if x.startswith("- `{shares_sentence}`")], "shares_sentence bullet")
need("fire and coral" in SL[kb], "shares bullet: first value is not fire and coral's")
m1 = re.match(r"^  `([^`]+)`;$", SL[kb + 1])
m2 = re.match(r"^  `([^`]+)`$", SL[kb + 3])
need(m1 is not None and m2 is not None and SL[kb + 2] == "  else (pm25, ndvi, defo)", "shares bullet layout")
new["SHARES_DEG"], new["SHARES_DE"] = m1.group(1), m2.group(1)
print("  %-22s spec line %d" % ("SHARES_DEG", kb + 2))
print("  %-22s spec line %d" % ("SHARES_DE", kb + 4))
need("(d, e, g)" in new["SHARES_DEG"] and "(d, e, g)" not in new["SHARES_DE"] and "(d, e)" in new["SHARES_DE"],
     "shares values")

# C4: Table S3.18 panel b (block found by its unchanged header line) and the note block right after it
ib = one([j for j, b in enumerate(blocks) if b[1] and b[1][0] == bt1.TAB18B[0]], "S3.18 panel b block")
print("  %-22s spec block at line %d (%d lines)" % ("TAB18B", blocks[ib][0], len(blocks[ib][1])))
print("  %-22s spec block at line %d (%d lines)" % ("NOTES18", blocks[ib + 1][0], len(blocks[ib + 1][1])))
t18, n18 = list(blocks[ib][1]), list(blocks[ib + 1][1])
o18 = bt1.TAB18B
need(len(o18) == 11 and "| CRW Outlook |" in o18[9] and o18[10].startswith("| All five | "), "v1 panel b layout")
need(len(t18) == 10 and t18[:9] == o18[:9] and t18[9].startswith("| All five | ") and t18[9] != o18[10],
     "panel b: not (CRW row dropped, baselines row reworded)")
need(len(n18) == 3 and n18[1:] == bt1.NOTES18, "S3.18 notes: not one line added before the two v1 lines")
new["TAB18B"], new["NOTES18"] = t18, n18

# C2: S3.20 notes (found by the unchanged notes c and d)
b20 = block_where(lambda L: len(L) == 4 and L[2] == bt1.NOTE20C and L[3] == bt1.NOTE20D, "S3.20 notes")
need(b20[0] != bt1.NOTE20A, "NOTE20A unchanged")
new["NOTE20A"] = b20[0]
toks = re.split(r"\{([a-z0-9_]+)\}", b20[1])
texts, names = toks[0::2], toks[1::2]
parts = [texts[0]]
need(len(names) == 8, "note b placeholders %r" % names)
for q in range(4):
    p = names[2 * q][len("bit_"):]
    need(names[2 * q] == "bit_" + p and names[2 * q + 1] == "rows_" + p, "note b placeholder order")
    parts.append((p, texts[2 * q + 1], texts[2 * q + 2]))
need(parts[1:] == bt1.NOTE20B_PARTS[1:] and parts[0] != bt1.NOTE20B_PARTS[0], "note b: more than its first part changed")
new["NOTE20B_PARTS"] = parts

# C6: S3.21 note a (found by the unchanged D8 line); E10's "What it checks" (the spec's row of 4.5)
b21 = block_where(lambda L: len(L) == 2 and L[1] == bt1.NOTES21[1], "S3.21 notes")
need(b21[0] != bt1.NOTES21[0], "S3.21 note a unchanged")
new["NOTES21"] = b21
e10_rows = [(i + 1, re.match(r"^\| `E10` \| `([^`]+)` \| ", x)) for i, x in enumerate(SL)]
ln, mo = one([(i, mo) for i, mo in e10_rows if mo], "E10 row")
print("  %-22s spec line %d" % ("E10 what", ln))
e10_old = one([w for key, g, w in bt1.GATE_ROWS if key == "E10"], "v1 E10 row")
need(mo.group(1).startswith(e10_old + ", "), "E10: not an extension of the v1 text")
new["E10"] = mo.group(1)

# C5: the S3.22 row label (the spec's row of 4.6 whose cell is AW4 cross_link_models)
lab_rows = [(i + 1, re.match(r"^\| `([^`]+)` \| AW4 `cross_link_models` as a model list \|$", x)) for i, x in enumerate(SL)]
ln, mo = one([(i, mo) for i, mo in lab_rows if mo], "S3.22 cross-link row")
print("  %-22s spec line %d" % ("S3.22 label", ln))
new["CROSS"] = mo.group(1)

# C8: S3.22 notes (found by the four unchanged lines)
b22 = block_where(lambda L: len(L) == 5 and [L[0], L[1], L[2], L[4]] == [bt1.NOTES22[i] for i in (0, 1, 2, 4)],
                  "S3.22 notes")
need(b22[3] != bt1.NOTES22[3], "S3.22 note d unchanged")
new["NOTES22"] = b22

# C7: the sign-agreement note (found by the unchanged dagger line)
b23 = block_where(lambda L: len(L) == 2 and L[1] == bt1.NOTES_AW3_ALL1[1], "AW3 sign notes")
need(b23[0] != bt1.NOTES_AW3_ALL1[0], "sign note unchanged")
new["NOTES_AW3_ALL1"] = b23

# C3: the ndvi note (found by its unchanged first part)
x = fenced_line(bt1.NOTE_NDVI_PARTS[0], "NOTE_NDVI template")
toks = re.split(r"\{([a-z0-9_]+)\}", x)
need(all(t != "" for t in toks[0::2]), "ndvi note: two placeholders in a row")
need(toks[1::2] == [t for t in bt1.NOTE_NDVI_PARTS if t in bt1.NOTE_NDVI_SLOTS], "ndvi note: placeholders differ")
need(len(toks) == len(bt1.NOTE_NDVI_PARTS), "ndvi note: part count")
diff_at = [i for i in range(len(toks)) if toks[i] != bt1.NOTE_NDVI_PARTS[i]]
need(len(diff_at) == 1 and bt1.NOTE_NDVI_PARTS[diff_at[0] - 1] == "j_feat", "ndvi note: changed parts %r" % diff_at)
new["NOTE_NDVI_PARTS"] = toks

# C4: the S3.30 notes (found by the unchanged identity line)
b30 = block_where(lambda L: len(L) == 2 and L[1] == bt1.NOTES30[1], "S3.30 notes")
need(b30[0] != bt1.NOTES30[0], "S3.30 note unchanged")
new["NOTES30"] = b30


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


tree = ast.parse(src1)
spans = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        nm = node.targets[0].id
        need(nm not in spans, "%s assigned twice" % nm)
        spans[nm] = (node.lineno, node.end_lineno)
lines = src1.split("\n")
REPL = ["HEADER_COMMENT", "CAP9", "TAB18B", "NOTES18", "NOTE20A", "NOTE20B_PARTS", "NOTES21", "NOTES22", "CAP_AW3",
        "NOTES_AW3_ALL1", "NOTE_NDVI_PARTS", "CAP29", "NOTES30"]
edits = [(spans[nm][0], spans[nm][1], stmt(nm, new[nm])) for nm in REPL]
g0, g1 = spans["G_CLAUSE"]
edits.append((g1 + 1, g1, ["# {shares_sentence} of the S3.23-S3.27 caption (version 2, C1): with panel g (fire, coral),"
                           " and without it"] + stmt("SHARES_DEG", new["SHARES_DEG"]) + stmt("SHARES_DE", new["SHARES_DE"])))
edits.sort(key=lambda e: -e[0])
for a, b, repl in edits:
    lines[a - 1:b] = repl
src2 = "\n".join(lines)


def sub1(src, old, rep, what):
    need(src.count(old) == 1, "%s: anchor found %d times" % (what, src.count(old)))
    return src.replace(old, rep)


src2 = sub1(src2, "    (\"E10\", \"E10\", " + lit(e10_old) + "),", "    (\"E10\", \"E10\", " + lit(new["E10"]) + "),",
            "E10 row")
mo = one(list(re.finditer(r'"cross": ("[^"\\]*")', src2)), "S3.22 cross label in the script")
old_label = json.loads(mo.group(1))
need(old_label != new["CROSS"] and new["CROSS"].lower().endswith(old_label.lower()), "S3.22 label %r" % old_label)
src2 = sub1(src2, '"cross": ' + mo.group(1), '"cross": ' + lit(new["CROSS"]), "S3.22 label")
src2 = sub1(src2, "    cap = cap.replace(\"{g_clause}\", G_CLAUSE if p in (\"fire\", \"coral\") else \"\")\n",
            "    cap = cap.replace(\"{g_clause}\", G_CLAUSE if p in (\"fire\", \"coral\") else \"\")\n"
            "    cap = cap.replace(\"{shares_sentence}\", SHARES_DEG if p in (\"fire\", \"coral\") else SHARES_DE)\n",
            "shares_sentence fill")
for short in ("S_REG", "S_MAX", "s_log(p)"):
    src2 = sub1(src2, "with open(real(%s), \"r\", encoding=\"utf-8\") as f:" % short,
                "with open(real(%s), \"r\", encoding=\"utf-8-sig\") as f:" % short, "G2 " + short)
src2 = sub1(src2, "    first = lines[0].lstrip(\"\\ufeff\")\n", "    first = lines[0]\n", "G2 BOM strip")
src2 = sub1(src2, "# with a message and writes neither file.\n",
            "# with a message and writes neither file.\n"
            "# Version 2 (2026-11-17): the texts changed by spec version 2 (C1-C9, taken from the spec by x07_patch_v2.py)\n"
            "# and its source text formats (G2: the register, the logs and bardl_maxima.txt read as utf-8-sig).\n",
            "script header")
compile(src2, BT, "exec")

# check: the patched module's constants are the spec's texts
tmp = {"__name__": "bt2", "__file__": BT}
exec(compile(ast.parse(src2), BT, "exec"), tmp)  # defines only; main() runs under __main__ only
for nm in REPL + ["SHARES_DEG", "SHARES_DE"]:
    need(tmp[nm] == new[nm], "%s differs after the patch" % nm)
need([w for key, g, w in tmp["GATE_ROWS"] if key == "E10"] == [new["E10"]], "E10 after the patch")

with open(BT, "w", encoding="utf-8", newline="\n") as f:
    f.write(src2)
print("build_tables.py written: %d -> %d lines" % (src1.count("\n"), src2.count("\n")))
print("diff (v1 -> v2):")
for d in difflib.unified_diff(src1.split("\n"), src2.split("\n"), "build_tables.py v1", "build_tables.py v2",
                              n=0, lineterm=""):
    print(d)
