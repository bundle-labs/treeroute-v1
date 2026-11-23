# Comparison only (builder B): version 4 of OUT\B\tables.md and cells.json against version 3 (OUT\B\tables_v3.md and
# cells_v3.json, byte copies made before the rebuild). Writes nothing.
# Since the version-5 rebuild, tables.md and cells.json hold version 5, so version 4 is read from its byte copies
# OUT\B\tables_v4.md and cells_v4.json (V4_MD and V4_CJ below); the checks are unchanged.
#
# 1. Lists every changed line of tables.md. No line is added or dropped, so v3 line k is v4 line k.
# 2. Builds the expected version 4 from version 3 by the change order's OLD and NEW printed texts, as quoted in
#    OUT\spec\CHANGES_v4.md (each also found in OUT\_brief\fix_order_v4.md, its wrapped lines joined by one space), and
#    requires it equal to version 4; every place of version 3 that holds an OLD text is one of the places changed.
# 3. Number tokens: on a changed line the tokens removed are tokens of the order's OLD texts applied to that line and
#    the tokens added are tokens of its NEW texts (the anchors of the V4-13 sentence excluded); in a table row every
#    cell keeps its number tokens; the other lines are unchanged.
# 4. cells.json: every entry equals its v3 entry in every key but `cell`, and `cell` differs only where the cell text
#    itself changed (the same cell of a changed line), so every printed token is the v3 token of the same cell.
# Run as: py -3.9 -I -B <this file>
import sys
import os
import re
import json
import hashlib
import collections

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
OUT_DIR = os.path.dirname(OUT_B)
CHANGES = os.path.join(OUT_DIR, "spec", "CHANGES_v4.md")
ORDER = os.path.join(OUT_DIR, "_brief", "fix_order_v4.md")

fails = []


def bad(msg):
    fails.append(msg)


def need(cond, msg):
    if not cond:
        bad(msg)
    return bool(cond)


def rb(name):
    with open(os.path.join(OUT_B, name), "rb") as f:
        return f.read()


V4_MD, V4_CJ = "tables_v4.md", "cells_v4.json"  # the version-4 outputs (byte copies made before the version-5 rebuild)
raw = {n: rb(n) for n in ("tables_v3.md", V4_MD, "cells_v3.json", V4_CJ)}
SHA = {n: hashlib.sha256(b).hexdigest() for n, b in raw.items()}
for n, b in raw.items():
    print("%-14s sha256 %s  %d bytes" % (n, SHA[n], len(b)))
for n in ("tables_v3.md", V4_MD):
    need(raw[n].endswith(b"\n") and not raw[n].endswith(b"\n\n") and b"\r" not in raw[n], n + ": line ends")
L3 = raw["tables_v3.md"].decode("utf-8")[:-1].split("\n")
L4 = raw[V4_MD].decode("utf-8")[:-1].split("\n")
print("lines: v3 %d, v4 %d" % (len(L3), len(L4)))
need(len(L3) == len(L4) == 785, "the line counts are not 785 and 785")
N = min(len(L3), len(L4))

# ---------------------------------------------------------------------------------------------------------------------
# The order's printed texts, from CHANGES_v4.md (fenced blocks whose label line says "printed text" or, for the rule's
# cell of V4-5, "printed cell")

with open(CHANGES, "r", encoding="utf-8") as f:
    ch_text = f.read()
ch_lines = ch_text.split("\n")
blocks, section, inside, cur, label = [], None, False, None, None
for i, ln in enumerate(ch_lines):
    if not inside and ln.startswith("## "):
        section = ln[3:].split(".")[0]
    if ln == "```":
        if inside:
            blocks.append((section, label, cur))
            inside = False
        else:
            j = i - 1
            while j >= 0 and ch_lines[j] == "":
                j -= 1
            label, cur, inside = ch_lines[j], [], True
    elif inside:
        cur.append(ln)
need(not inside, "CHANGES_v4.md: an unclosed fence")
PRINTED = collections.OrderedDict()
for sec, lab, body in blocks:
    if "printed text" in lab or "printed cell" in lab:
        PRINTED.setdefault(sec, []).append((lab, body))
want_counts = collections.OrderedDict([("V4-1", 2), ("V4-2", 2), ("V4-3", 6), ("V4-4", 2), ("V4-5", 2), ("V4-6", 4),
                                       ("V4-7", 2), ("V4-8", 2), ("V4-9", 2), ("V4-10", 2), ("V4-11", 2), ("V4-12", 2),
                                       ("V4-13", 1)])
need(list(PRINTED.keys()) == list(want_counts.keys()), "CHANGES_v4.md: printed blocks in sections %r" % list(PRINTED))
for sec, n in want_counts.items():
    need(len(PRINTED.get(sec, [])) == n, "CHANGES_v4.md %s: %d printed blocks, expected %d" % (sec, len(PRINTED.get(sec, [])), n))
n_old = sum(1 for v in PRINTED.values() for lab, body in v if "OLD printed" in lab)
n_new = sum(1 for v in PRINTED.values() for lab, body in v if "NEW printed" in lab)
print("CHANGES_v4.md: %d fenced blocks, %d printed texts (%d OLD, %d NEW)" % (len(blocks), n_old + n_new, n_old, n_new))
need((n_old, n_new) == (15, 16), "CHANGES_v4.md: not 15 OLD and 16 NEW printed texts (the 16th: V4-13's sentence)")


def pt(sec, idx, must):
    lab, body = PRINTED[sec][idx]
    need(must in lab, "CHANGES_v4.md %s printed block %d has label %r, expected %r" % (sec, idx, lab, must))
    need(len(body) == 1, "CHANGES_v4.md %s printed block %d has %d lines" % (sec, idx, len(body)))
    return body[0]


T = collections.OrderedDict([
    ("e3m_old", pt("V4-1", 0, "OLD printed text")), ("e3m_new", pt("V4-1", 1, "NEW printed text")),
    ("e3a_old", pt("V4-2", 0, "OLD printed text")), ("e3a_new", pt("V4-2", 1, "NEW printed text")),
    ("noteb_old", pt("V4-3", 0, "S3.19 note ᵇ, OLD printed text")), ("noteb_new", pt("V4-3", 1, "NEW printed text")),
    ("notec_old", pt("V4-3", 2, "S3.19 note ᶜ, the end of the note's first sentence, OLD printed text")),
    ("notec_new", pt("V4-3", 3, "NEW printed text")),
    ("t9_coral_old", pt("V4-3", 4, "Table 9 caption, OLD printed text")), ("t9_coral_new", pt("V4-3", 5, "NEW printed text")),
    ("t9_ctx_old", pt("V4-4", 0, "OLD printed text")), ("t9_ctx_new", pt("V4-4", 1, "NEW printed text")),
    ("arm_old", pt("V4-5", 0, "OLD printed cell, made by the rule (NDVI)")),
    ("arm_new", pt("V4-5", 1, "NEW printed cell, made by the rule (NDVI)")),
    ("e5_old", pt("V4-6", 0, "E5's \"What it checks\", OLD printed text")), ("e5_new", pt("V4-6", 1, "NEW printed text")),
    ("notea_old", pt("V4-6", 2, "Note ᵃ, OLD printed text")), ("notea_new", pt("V4-6", 3, "NEW printed text")),
    ("hdr_b_old", pt("V4-7", 0, "OLD printed text")), ("hdr_b_new", pt("V4-7", 1, "NEW printed text")),
    ("cross_old", pt("V4-8", 0, "OLD printed text")), ("cross_new", pt("V4-8", 1, "NEW printed text")),
    ("j_old", pt("V4-9", 0, "OLD printed text")), ("j_new", pt("V4-9", 1, "NEW printed text")),
    ("e3_old", pt("V4-10", 0, "OLD printed text")), ("e3_new", pt("V4-10", 1, "NEW printed text")),
    ("e8_old", pt("V4-11", 0, "OLD printed text")), ("e8_new", pt("V4-11", 1, "NEW printed text")),
    ("src_old", pt("V4-12", 0, "OLD printed text")), ("src_new", pt("V4-12", 1, "NEW printed text")),
    ("hdr_new", pt("V4-13", 0, "NEW printed text")),
])

# each text is also in the change order itself (its backticked spans, the order's wrapped lines joined by one space)
with open(ORDER, "r", encoding="utf-8") as f:
    order_flat = re.sub(r"\n[ ]*", " ", f.read())
n_found = 0
for k, v in T.items():
    if need(("`" + v + "`") in order_flat, "fix_order_v4.md does not hold the text %s" % k):
        n_found += 1
print("order texts found in fix_order_v4.md: %d of %d" % (n_found, len(T)))
# V4-13's place: directly after the Version 3 sentence (CHANGES_v4.md names its end) and before "Built from ..."
ch_flat = re.sub(r"\n[ ]*", " ", ch_text)
m_anchor = re.search(r"\(which ends `([^`]+)`\) and before `([^`]+)`, NEW printed text:", ch_flat)
END3, BEFORE = (m_anchor.group(1), m_anchor.group(2)) if need(m_anchor is not None, "CHANGES_v4.md's V4-13 anchors") else ("?", "?")
need("after the Version 3 sentence, add `" + T["hdr_new"] + "`" in order_flat, "the order's V4-13 sentence and its place")
i_v3, i_end = L3[0].find("Version 3 ("), L3[0].find(END3 + " " + BEFORE)
need(i_v3 >= 0 and i_end > i_v3 and ". " not in L3[0][i_v3:i_end + len(END3) - 1] and "Version 4" not in L3[0],
     "line 1 of version 3: the Version 3 sentence does not end with the anchor")

# ---------------------------------------------------------------------------------------------------------------------
# The expected version 4: version 3 with the order's changes applied (no line added or dropped)

TABLE_AT = []
cur_t = None
for ln in L3:
    mt = re.match(r"^\*\*Table (9|S3\.\d+)[ .]", ln)
    if mt:
        cur_t = mt.group(1)
    TABLE_AT.append(cur_t)

EXP = list(L3)
APPLIED = collections.defaultdict(list)  # line index -> list of (item, old, new, order OLD text, order NEW text)


def rep(item, key_old, key_new, n_lines, where=lambda i, ln: True, wrap=("", "")):
    old, new = T[key_old], T[key_new]
    o, w = wrap[0] + old + wrap[1], wrap[0] + new + wrap[1]
    hits = [i for i, ln in enumerate(EXP) if o in ln and where(i, ln)]
    need(len(hits) == n_lines, "%s %r: in %d lines, expected %d" % (item, old[:50], len(hits), n_lines))
    # every place of version 3 that holds the OLD text is one of the places changed
    need(sum(ln.count(old) for ln in L3) == len(hits), "%s %r: the OLD text is elsewhere in version 3 too" % (item, old[:50]))
    for i in hits:
        need(EXP[i].count(o) == 1, "%s: more than once on line %d" % (item, i + 1))
        EXP[i] = EXP[i].replace(o, w)
        APPLIED[i].append((item, o, w, old, new))
    return hits


def starts(prefix):
    return lambda i, ln: ln.startswith(prefix)


def whole(text):
    return lambda i, ln: ln == text


# V4-13: the new sentence after the Version 3 sentence of line 1 (the anchors are not order texts)
a_old, a_new = END3 + " " + BEFORE, END3 + " " + T["hdr_new"] + " " + BEFORE
if need(EXP[0].count(a_old) == 1 and sum(ln.count(a_old) for ln in L3) == 1, "V4-13: the anchor on line 1 only"):
    EXP[0] = EXP[0].replace(a_old, a_new)
    APPLIED[0].append(("V4-13", a_old, a_new, "", T["hdr_new"]))
rep("V4-3", "t9_coral_old", "t9_coral_new", 1, where=starts("**Table 9.**"))
rep("V4-4", "t9_ctx_old", "t9_ctx_new", 1, where=starts("**Table 9.**"))
rep("V4-12", "src_old", "src_new", 1, where=starts("**Table S3.18 (post hoc).**"))
rep("V4-7", "hdr_b_old", "hdr_b_new", 1, where=whole(T["hdr_b_old"]))
rep("V4-3", "noteb_old", "noteb_new", 1, where=whole(T["noteb_old"]))
rep("V4-3", "notec_old", "notec_new", 1, where=starts("ᶜ Background (B2):"))
arm_hits = rep("V4-5", "arm_old", "arm_new", 1, where=starts("| Adopted arm | "), wrap=("| ", " | "))
rep("V4-2", "e3a_old", "e3a_new", 1, where=starts("| E3a | "), wrap=("| ", " | "))
rep("V4-1", "e3m_old", "e3m_new", 1, where=starts("| E3m | "), wrap=("| ", " | "))
rep("V4-10", "e3_old", "e3_new", 1, where=starts("| E3 | "), wrap=("| ", " | "))
rep("V4-6", "e5_old", "e5_new", 1, where=starts("| E5ᵃ | "), wrap=("| ", " | "))
rep("V4-11", "e8_old", "e8_new", 1, where=starts("| E8 | "), wrap=("| ", " | "))
rep("V4-6", "notea_old", "notea_new", 1, where=starts("ᵃ E5 is informational"))
rep("V4-8", "cross_old", "cross_new", 1, where=starts("| " + T["cross_old"] + " | "), wrap=("| ", " | "))
rep("V4-9", "j_old", "j_new", 1, where=starts("**Table S3.28 (post hoc; sensitivity).**"))


def header_cells(lines, i):
    # the header cells of the table row on 0-based line i: the line before the separator above it
    j = i
    while j >= 0 and not lines[j].startswith("|---"):
        j -= 1
    return lines[j - 1][2:-2].split(" | ")


for i in arm_hits:  # V4-5: the changed cell of the Adopted arm row is NDVI's
    c4 = L4[i][2:-2].split(" | ")
    ks = [k for k, c in enumerate(c4) if c == T["arm_new"]]
    need(len(ks) == 1 and header_cells(L4, i)[ks[0]] == "NDVI" and TABLE_AT[i] == "S3.21",
         "V4-5: the plain arm's cell is not NDVI's cell of Table S3.21")

same = (EXP == L4)
need(same, "the expected version 4 (version 3 with the order's texts) differs from tables.md")
if not same:
    for k in range(min(len(EXP), len(L4))):
        if EXP[k] != L4[k]:
            print("EXPECTED != BUILT on line %d" % (k + 1))
print("expected version 4 == built version 4:", same, "| changes applied on", len(APPLIED), "lines,",
      sum(len(v) for v in APPLIED.values()), "replacements")

# ---------------------------------------------------------------------------------------------------------------------
# 1. The changed lines, with the order items applied and the number tokens removed / added

NUMTOK = re.compile(r"[0-9](?:[0-9,.]*[0-9])?|[⁰¹²³⁴-⁹⁻]+")


def toks(s):
    return collections.Counter(NUMTOK.findall(s))


def fmt_c(c):
    return "[" + ", ".join(sorted(c.elements())) + "]" if c else "[]"


def what(line):
    return line[:64] + ("..." if len(line) > 64 else "")


pos_changed = [k + 1 for k in range(N) if L3[k] != L4[k]]
m_lines = re.search(r"The lines that change \(1-based, (\d+)\): ([0-9, ]+)\.", ch_flat)
want_pos = [int(x) for x in m_lines.group(2).split(", ")] if need(m_lines is not None, "CHANGES_v4.md's line list") else []
need(m_lines is not None and int(m_lines.group(1)) == len(want_pos), "CHANGES_v4.md's line count")
need(pos_changed == want_pos, "the changed lines are not those of CHANGES_v4.md")
print("\n== changed lines of tables.md (1-based; v3 line = v4 line): %d" % len(pos_changed))
print("  " + ", ".join(str(x) for x in pos_changed))
need(sorted(i + 1 for i in APPLIED) == pos_changed, "a changed line without an order item, or an item on an unchanged line")

print("\n== per changed line: table, the order items, the number tokens removed / added")
ADDED_ALL, REMOVED_ALL = collections.Counter(), collections.Counter()
ADDED_AT = collections.OrderedDict()
for no in pos_changed:
    i = no - 1
    t3, t4 = toks(L3[i]), toks(L4[i])
    rem, add = t3 - t4, t4 - t3
    olds, news, ord_old, ord_new = (collections.Counter() for _ in range(4))
    for item, o, w, oo, on in APPLIED[i]:
        olds += toks(o)
        news += toks(w)
        ord_old += toks(oo)
        ord_new += toks(on)
    # the line's tokens are exactly those of version 3 with the replaced texts' tokens swapped
    need(not (olds - t3) and t4 == (t3 - olds) + news, "line %d: the number tokens are not v3's with the texts swapped" % no)
    need(not (rem - ord_old), "line %d: removed tokens %s outside the order's OLD texts" % (no, fmt_c(rem - ord_old)))
    need(not (add - ord_new), "line %d: added tokens %s outside the order's NEW texts" % (no, fmt_c(add - ord_new)))
    ADDED_ALL += add
    REMOVED_ALL += rem
    if add:
        ADDED_AT[no] = add
    ids = "+".join(sorted(set(item for item, o, w, oo, on in APPLIED[i]), key=lambda s: int(s.split("-")[1])))
    extra = ""
    if L3[i].startswith("| "):
        c3, c4 = L3[i][2:-2].split(" | "), L4[i][2:-2].split(" | ")
        if need(len(c3) == len(c4), "line %d: the cell count changed" % no):
            ch = [k for k in range(len(c3)) if c3[k] != c4[k]]
            for k in ch:
                need(toks(c3[k]) == toks(c4[k]), "line %d cell %d: number tokens changed" % (no, k + 1))
            extra = " | cells changed %s, their number tokens unchanged" % [k + 1 for k in ch]
    print("  %4d %-6s [%s] %s | removed %s added %s%s" % (no, TABLE_AT[i] or "-", ids, what(L4[i]), fmt_c(rem),
                                                          fmt_c(add), extra))
for k in range(N):
    if L3[k] == L4[k]:
        need(toks(L3[k]) == toks(L4[k]), "unchanged line with different tokens")
    if L3[k].startswith("| ") and L4[k].startswith("| "):
        c3, c4 = L3[k][2:-2].split(" | "), L4[k][2:-2].split(" | ")
        need(len(c3) == len(c4) and all(toks(x) == toks(y) for x, y in zip(c3, c4)),
             "line %d: a table cell whose number tokens changed" % (k + 1))
T3, T4 = toks("\n".join(L3)), toks("\n".join(L4))
print("\nnumber tokens in the whole file: v3 %d, v4 %d; removed %s; added %s"
      % (sum(T3.values()), sum(T4.values()), fmt_c(T3 - T4), fmt_c(T4 - T3)))
need(T3 - T4 == REMOVED_ALL and T4 - T3 == ADDED_ALL, "the whole-file token differences are not the per-line ones")
need(not REMOVED_ALL, "a number token was removed")
need(list(ADDED_AT.keys()) == [1, 22], "tokens added on lines other than 1 and 22: %r" % list(ADDED_AT.keys()))
print("tokens added per line:", {k: fmt_c(v) for k, v in ADDED_AT.items()})

# ---------------------------------------------------------------------------------------------------------------------
# 4. cells.json

d3 = json.loads(raw["cells_v3.json"].decode("utf-8"))
d4 = json.loads(raw[V4_CJ].decode("utf-8"))
need(list(d3.keys()) == list(d4.keys()) == ["tables_file", "spec", "entries"], "cells.json top keys")
need(d3["tables_file"] == d4["tables_file"] == "tables.md" and d3["spec"] == d4["spec"] == "OUT\\spec\\TABLE_SPEC.md",
     "cells.json header values")
E3, E4 = d3["entries"], d4["entries"]
need(len(E3) == len(E4), "cells.json: %d entries in v3, %d in v4" % (len(E3), len(E4)))
SAME_KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "source", "selector", "stored"]


def cell_index(line, cell):
    if line.startswith("| "):
        cs = line[2:-2].split(" | ")
        return [k for k, c in enumerate(cs) if c == cell]
    return [0] if line == cell else []


n_cell = collections.Counter()
for k, (a, b) in enumerate(zip(E3, E4)):
    need(list(a.keys()) == list(b.keys()), "entry %d: keys" % k)
    for key in SAME_KEYS:
        need(a[key] == b[key], "entry %d (line %d): %s differs: %r -> %r" % (k, a["line"], key, a[key], b[key]))
    need(b["cell"] in L4[b["line"] - 1] and b["printed"] in b["cell"], "entry %d: not on its v4 line" % k)
    need(len(cell_index(L4[b["line"] - 1], b["cell"])) >= 1, "entry %d: its cell is not a cell of its v4 line" % k)
    if a["cell"] != b["cell"]:
        no = a["line"]
        ia, ib = cell_index(L3[no - 1], a["cell"]), cell_index(L4[no - 1], b["cell"])
        ok = no in pos_changed and len(ia) >= 1 and ia == ib
        if need(ok, "entry %d (line %d): cell changed but it is not the same cell of a changed line" % (k, no)):
            n_cell[no] += 1
by_cell = collections.defaultdict(lambda: [[], []])
for a, b in zip(E3, E4):
    key = (b["line"], b["table"], b["panel"], b["row"], b["column"])
    by_cell[key][0].append(a["printed"])
    by_cell[key][1].append(b["printed"])
need(all(x == y for x, y in by_cell.values()), "a cell whose printed tokens differ")
on_changed = collections.Counter(b["line"] for b in E4 if b["line"] in pos_changed)
kept = {no: c - n_cell.get(no, 0) for no, c in on_changed.items()}
print("\n== cells.json: %d entries in v3 and %d in v4; every key but `cell` equal; `cell` changed on %d entries %s"
      % (len(E3), len(E4), sum(n_cell.values()), dict(sorted(n_cell.items()))))
print("entries on changed lines, per line:", dict(sorted(on_changed.items())))
print("of those, keeping their cell:", dict(sorted((k, v) for k, v in kept.items() if v)))
need(not n_cell, "an entry whose cell changed (CHANGES_v4.md: none)")
need(dict(on_changed) == {135: 3, 143: 12}, "the entries on changed lines are not 3 on line 135 and 12 on line 143")
print("cells with entries: %d; each prints the same tokens in the same order in v3 and v4" % len(by_cell))
print("cells.json byte-identical to cells_v3.json:", raw[V4_CJ] == raw["cells_v3.json"])

numbers_unchanged = same and not fails
print("\nnumbers_unchanged:", numbers_unchanged, "| n_lines:", len(L4), "| entries:", len(E4))
print("failures:", len(fails))
for m in fails[:50]:
    print("FAIL", m)
sys.exit(1 if fails else 0)
