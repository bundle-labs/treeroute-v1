# Comparison only (builder B): version 5 of OUT\B\tables.md and cells.json against version 4 (OUT\B\tables_v4.md and
# cells_v4.json, byte copies made before the rebuild). Writes nothing. (Made from compare_v3_v4.py for versions 4
# and 5.)
#
# 1. Lists every changed line of tables.md. No line is added or dropped, so v4 line k is v5 line k.
# 2. Builds the expected version 5 from version 4 by the change order's OLD and NEW printed texts, as quoted in
#    OUT\spec\CHANGES_v5.md (each also found in OUT\_brief\fix_order_v5.md, its wrapped lines joined by one space), and
#    requires it equal to version 5; every place of version 4 that holds an OLD text is one of the places changed.
# 3. Number tokens: on a changed line the tokens removed are tokens of the order's OLD texts applied to that line and
#    the tokens added are tokens of its NEW texts (the anchors of the V5-5 sentence excluded); in a table row a cell
#    keeps its number tokens unless the cell is an order text replaced whole, and then its added and removed tokens
#    are tokens of that NEW and OLD text; the other lines are unchanged.
# 4. cells.json: every entry equals its v4 entry in every key but `cell`, and `cell` differs only where the cell text
#    itself changed (the same cell of a changed line), so every printed token is the v4 token of the same cell.
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
CHANGES = os.path.join(OUT_DIR, "spec", "CHANGES_v5.md")
ORDER = os.path.join(OUT_DIR, "_brief", "fix_order_v5.md")

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


raw = {n: rb(n) for n in ("tables_v4.md", "tables.md", "cells_v4.json", "cells.json")}
SHA = {n: hashlib.sha256(b).hexdigest() for n, b in raw.items()}
for n, b in raw.items():
    print("%-14s sha256 %s  %d bytes" % (n, SHA[n], len(b)))
for n in ("tables_v4.md", "tables.md"):
    need(raw[n].endswith(b"\n") and not raw[n].endswith(b"\n\n") and b"\r" not in raw[n], n + ": line ends")
L4 = raw["tables_v4.md"].decode("utf-8")[:-1].split("\n")
L5 = raw["tables.md"].decode("utf-8")[:-1].split("\n")
print("lines: v4 %d, v5 %d" % (len(L4), len(L5)))
need(len(L4) == len(L5) == 785, "the line counts are not 785 and 785")
N = min(len(L4), len(L5))

# ---------------------------------------------------------------------------------------------------------------------
# The order's printed texts, from CHANGES_v5.md (fenced blocks whose label line says "printed text"; the "v4 spec
# text" and "v5 spec text" blocks of S12 print nothing)

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
need(not inside, "CHANGES_v5.md: an unclosed fence")
PRINTED = collections.OrderedDict()
for sec, lab, body in blocks:
    if "printed text" in lab:
        PRINTED.setdefault(sec, []).append((lab, body))
want_counts = collections.OrderedDict([("V5-1", 2), ("V5-2", 4), ("V5-3", 4), ("V5-4", 2), ("V5-5", 1)])
need(list(PRINTED.keys()) == list(want_counts.keys()), "CHANGES_v5.md: printed blocks in sections %r" % list(PRINTED))
for sec, n in want_counts.items():
    need(len(PRINTED.get(sec, [])) == n, "CHANGES_v5.md %s: %d printed blocks, expected %d" % (sec, len(PRINTED.get(sec, [])), n))
n_old = sum(1 for v in PRINTED.values() for lab, body in v if "OLD printed" in lab)
n_new = sum(1 for v in PRINTED.values() for lab, body in v if "NEW printed" in lab)
print("CHANGES_v5.md: %d fenced blocks, %d printed texts (%d OLD, %d NEW)" % (len(blocks), n_old + n_new, n_old, n_new))
need((n_old, n_new) == (6, 7), "CHANGES_v5.md: not 6 OLD and 7 NEW printed texts (the 7th: V5-5's sentence)")


def pt(sec, idx, must):
    lab, body = PRINTED[sec][idx]
    need(must in lab, "CHANGES_v5.md %s printed block %d has label %r, expected %r" % (sec, idx, lab, must))
    need(len(body) == 1, "CHANGES_v5.md %s printed block %d has %d lines" % (sec, idx, len(body)))
    return body[0]


T = collections.OrderedDict([
    ("t9_ctx_old", pt("V5-1", 0, "OLD printed text")), ("t9_ctx_new", pt("V5-1", 1, "NEW printed text")),
    ("t9_coral_old", pt("V5-2", 0, "Table 9 caption, OLD printed text")), ("t9_coral_new", pt("V5-2", 1, "NEW printed text")),
    ("notec_old", pt("V5-2", 2, "S3.19 note ᶜ, the end of the note's first sentence, OLD printed text")),
    ("notec_new", pt("V5-2", 3, "NEW printed text")),
    ("e5_old", pt("V5-3", 0, "E5's \"What it checks\", OLD printed text")), ("e5_new", pt("V5-3", 1, "NEW printed text")),
    ("notea_old", pt("V5-3", 2, "Note ᵃ, OLD printed text")), ("notea_new", pt("V5-3", 3, "NEW printed text")),
    ("e3m_old", pt("V5-4", 0, "OLD printed text")), ("e3m_new", pt("V5-4", 1, "NEW printed text")),
    ("hdr_new", pt("V5-5", 0, "NEW printed text")),
])

# each text is also in the change order itself (its backticked spans, the order's wrapped lines joined by one space)
with open(ORDER, "r", encoding="utf-8") as f:
    order_flat = re.sub(r"\n[ ]*", " ", f.read())
n_found = 0
for k, v in T.items():
    if need(("`" + v + "`") in order_flat, "fix_order_v5.md does not hold the text %s" % k):
        n_found += 1
print("order texts found in fix_order_v5.md: %d of %d" % (n_found, len(T)))
# V5-5's place: directly after the Version 4 sentence (CHANGES_v5.md names its end) and before "Built from ..."
ch_flat = re.sub(r"\n[ ]*", " ", ch_text)
m_anchor = re.search(r"\(which ends `([^`]+)`\) and before `([^`]+)`, NEW printed text:", ch_flat)
END4, BEFORE = (m_anchor.group(1), m_anchor.group(2)) if need(m_anchor is not None, "CHANGES_v5.md's V5-5 anchors") else ("?", "?")
need("after the Version 4 sentence, add `" + T["hdr_new"] + "`" in order_flat, "the order's V5-5 sentence and its place")
i_v4, i_end = L4[0].find("Version 4 ("), L4[0].find(END4 + " " + BEFORE)
need(i_v4 >= 0 and i_end > i_v4 and ". " not in L4[0][i_v4:i_end + len(END4) - 1] and "Version 5" not in L4[0],
     "line 1 of version 4: the Version 4 sentence does not end with the anchor")

# ---------------------------------------------------------------------------------------------------------------------
# The expected version 5: version 4 with the order's changes applied (no line added or dropped)

TABLE_AT = []
cur_t = None
for ln in L4:
    mt = re.match(r"^\*\*Table (9|S3\.\d+)[ .]", ln)
    if mt:
        cur_t = mt.group(1)
    TABLE_AT.append(cur_t)

EXP = list(L4)
APPLIED = collections.defaultdict(list)  # line index -> list of (item, old, new, order OLD text, order NEW text)
WHOLE_CELL = collections.defaultdict(list)  # line index -> list of (order OLD text, order NEW text) replaced as a cell


def rep(item, key_old, key_new, n_lines, where=lambda i, ln: True, wrap=("", "")):
    old, new = T[key_old], T[key_new]
    o, w = wrap[0] + old + wrap[1], wrap[0] + new + wrap[1]
    hits = [i for i, ln in enumerate(EXP) if o in ln and where(i, ln)]
    need(len(hits) == n_lines, "%s %r: in %d lines, expected %d" % (item, old[:50], len(hits), n_lines))
    # every place of version 4 that holds the OLD text is one of the places changed
    need(sum(ln.count(old) for ln in L4) == len(hits), "%s %r: the OLD text is elsewhere in version 4 too" % (item, old[:50]))
    for i in hits:
        need(EXP[i].count(o) == 1, "%s: more than once on line %d" % (item, i + 1))
        EXP[i] = EXP[i].replace(o, w)
        APPLIED[i].append((item, o, w, old, new))
        if wrap == ("| ", " | "):
            WHOLE_CELL[i].append((old, new))
    return hits


def starts(prefix):
    return lambda i, ln: ln.startswith(prefix)


def header_cells(lines, i):
    # the header cells of the table row on 0-based line i: the line before the separator above it
    j = i
    while j >= 0 and not lines[j].startswith("|---"):
        j -= 1
    return lines[j - 1][2:-2].split(" | ")


# V5-5: the new sentence after the Version 4 sentence of line 1 (the anchors are not order texts)
a_old, a_new = END4 + " " + BEFORE, END4 + " " + T["hdr_new"] + " " + BEFORE
if need(EXP[0].count(a_old) == 1 and sum(ln.count(a_old) for ln in L4) == 1, "V5-5: the anchor on line 1 only"):
    EXP[0] = EXP[0].replace(a_old, a_new)
    APPLIED[0].append(("V5-5", a_old, a_new, "", T["hdr_new"]))
rep("V5-1", "t9_ctx_old", "t9_ctx_new", 1, where=starts("**Table 9.**"))
rep("V5-2", "t9_coral_old", "t9_coral_new", 1, where=starts("**Table 9.**"))
rep("V5-2", "notec_old", "notec_new", 1, where=starts("ᶜ Background (B2):"))
e3m_hits = rep("V5-4", "e3m_old", "e3m_new", 1, where=starts("| E3m | "), wrap=("| ", " | "))
e5_hits = rep("V5-3", "e5_old", "e5_new", 1, where=starts("| E5ᵃ | "), wrap=("| ", " | "))
rep("V5-3", "notea_old", "notea_new", 1, where=starts("ᵃ E5 is informational"))

# the two S3.21 cells are the "What it checks" cells (the second column) of Table S3.21
for i in e3m_hits + e5_hits:
    c5 = L5[i][2:-2].split(" | ")
    need(TABLE_AT[i] == "S3.21" and len(c5) == 7 and c5[1] in (T["e3m_new"], T["e5_new"]),
         "line %d: the changed cell is not the What it checks cell of Table S3.21" % (i + 1))

same = (EXP == L5)
need(same, "the expected version 5 (version 4 with the order's texts) differs from tables.md")
if not same:
    for k in range(min(len(EXP), len(L5))):
        if EXP[k] != L5[k]:
            print("EXPECTED != BUILT on line %d" % (k + 1))
print("expected version 5 == built version 5:", same, "| changes applied on", len(APPLIED), "lines,",
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


pos_changed = [k + 1 for k in range(N) if L4[k] != L5[k]]
m_lines = re.search(r"The lines that change \(1-based, (\d+)\): ([0-9, ]+)\.", ch_flat)
want_pos = [int(x) for x in m_lines.group(2).split(", ")] if need(m_lines is not None, "CHANGES_v5.md's line list") else []
need(m_lines is not None and int(m_lines.group(1)) == len(want_pos), "CHANGES_v5.md's line count")
need(pos_changed == want_pos, "the changed lines are not those of CHANGES_v5.md")
print("\n== changed lines of tables.md (1-based; v4 line = v5 line): %d" % len(pos_changed))
print("  " + ", ".join(str(x) for x in pos_changed))
need(sorted(i + 1 for i in APPLIED) == pos_changed, "a changed line without an order item, or an item on an unchanged line")

print("\n== per changed line: table, the order items, the number tokens removed / added")
ADDED_ALL, REMOVED_ALL = collections.Counter(), collections.Counter()
ADDED_AT = collections.OrderedDict()
for no in pos_changed:
    i = no - 1
    t4, t5 = toks(L4[i]), toks(L5[i])
    rem, add = t4 - t5, t5 - t4
    olds, news, ord_old, ord_new = (collections.Counter() for _ in range(4))
    for item, o, w, oo, on in APPLIED[i]:
        olds += toks(o)
        news += toks(w)
        ord_old += toks(oo)
        ord_new += toks(on)
    # the line's tokens are exactly those of version 4 with the replaced texts' tokens swapped
    need(not (olds - t4) and t5 == (t4 - olds) + news, "line %d: the number tokens are not v4's with the texts swapped" % no)
    need(not (rem - ord_old), "line %d: removed tokens %s outside the order's OLD texts" % (no, fmt_c(rem - ord_old)))
    need(not (add - ord_new), "line %d: added tokens %s outside the order's NEW texts" % (no, fmt_c(add - ord_new)))
    ADDED_ALL += add
    REMOVED_ALL += rem
    if add:
        ADDED_AT[no] = add
    ids = "+".join(sorted(set(item for item, o, w, oo, on in APPLIED[i]), key=lambda s: int(s.split("-")[1])))
    extra = ""
    if L4[i].startswith("| "):
        c4, c5 = L4[i][2:-2].split(" | "), L5[i][2:-2].split(" | ")
        if need(len(c4) == len(c5), "line %d: the cell count changed" % no):
            ch = [k for k in range(len(c4)) if c4[k] != c5[k]]
            for k in ch:
                # a changed cell is an order text replaced whole; its token changes lie in that OLD and NEW text
                pair = [(oo, on) for oo, on in WHOLE_CELL[i] if c4[k] == oo and c5[k] == on]
                if need(len(pair) == 1, "line %d cell %d: changed, but not an order text replaced whole" % (no, k + 1)):
                    oo, on = pair[0]
                    need(not ((toks(c4[k]) - toks(c5[k])) - toks(oo)) and not ((toks(c5[k]) - toks(c4[k])) - toks(on)),
                         "line %d cell %d: number tokens changed outside the order's texts" % (no, k + 1))
            hdr = header_cells(L5, i)
            extra = " | row %r, cells changed %s (%s), each an order text replaced whole" % (
                c5[0], [k + 1 for k in ch], ", ".join(repr(hdr[k]) for k in ch))
    print("  %4d %-6s [%s] %s | removed %s added %s%s" % (no, TABLE_AT[i] or "-", ids, what(L5[i]), fmt_c(rem),
                                                          fmt_c(add), extra))
for k in range(N):
    if L4[k] == L5[k]:
        need(toks(L4[k]) == toks(L5[k]), "unchanged line with different tokens")
    if L4[k].startswith("| ") and L5[k].startswith("| "):
        c4, c5 = L4[k][2:-2].split(" | "), L5[k][2:-2].split(" | ")
        whole = set(WHOLE_CELL.get(k, []))
        need(len(c4) == len(c5) and all(toks(x) == toks(y) or (x, y) in whole for x, y in zip(c4, c5)),
             "line %d: a table cell whose number tokens changed (not an order text replaced whole)" % (k + 1))
T4, T5 = toks("\n".join(L4)), toks("\n".join(L5))
print("\nnumber tokens in the whole file: v4 %d, v5 %d; removed %s; added %s"
      % (sum(T4.values()), sum(T5.values()), fmt_c(T4 - T5), fmt_c(T5 - T4)))
need(T4 - T5 == REMOVED_ALL and T5 - T4 == ADDED_ALL, "the whole-file token differences are not the per-line ones")
need(not REMOVED_ALL, "a number token was removed")
need(list(ADDED_AT.keys()) == [1, 135], "tokens added on lines other than 1 and 135: %r" % list(ADDED_AT.keys()))
need(ADDED_AT.get(135) == toks(T["e3m_new"]) - toks(T["e3m_old"]) == collections.Counter({"256": 1}),
     "line 135: the added tokens are not the 256 of the order's SHA-256")
need(ADDED_AT.get(1) == toks(T["hdr_new"]), "line 1: the added tokens are not those of the V5-5 sentence")
print("tokens added per line:", {k: fmt_c(v) for k, v in ADDED_AT.items()})

# ---------------------------------------------------------------------------------------------------------------------
# 4. cells.json

d4 = json.loads(raw["cells_v4.json"].decode("utf-8"))
d5 = json.loads(raw["cells.json"].decode("utf-8"))
need(list(d4.keys()) == list(d5.keys()) == ["tables_file", "spec", "entries"], "cells.json top keys")
need(d4["tables_file"] == d5["tables_file"] == "tables.md" and d4["spec"] == d5["spec"] == "OUT\\spec\\TABLE_SPEC.md",
     "cells.json header values")
E4, E5 = d4["entries"], d5["entries"]
need(len(E4) == len(E5), "cells.json: %d entries in v4, %d in v5" % (len(E4), len(E5)))
SAME_KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "source", "selector", "stored"]


def cell_index(line, cell):
    if line.startswith("| "):
        cs = line[2:-2].split(" | ")
        return [k for k, c in enumerate(cs) if c == cell]
    return [0] if line == cell else []


n_cell = collections.Counter()
for k, (a, b) in enumerate(zip(E4, E5)):
    need(list(a.keys()) == list(b.keys()), "entry %d: keys" % k)
    for key in SAME_KEYS:
        need(a[key] == b[key], "entry %d (line %d): %s differs: %r -> %r" % (k, a["line"], key, a[key], b[key]))
    need(b["cell"] in L5[b["line"] - 1] and b["printed"] in b["cell"], "entry %d: not on its v5 line" % k)
    need(len(cell_index(L5[b["line"] - 1], b["cell"])) >= 1, "entry %d: its cell is not a cell of its v5 line" % k)
    if a["cell"] != b["cell"]:
        no = a["line"]
        ia, ib = cell_index(L4[no - 1], a["cell"]), cell_index(L5[no - 1], b["cell"])
        ok = no in pos_changed and len(ia) >= 1 and ia == ib
        if need(ok, "entry %d (line %d): cell changed but it is not the same cell of a changed line" % (k, no)):
            n_cell[no] += 1
by_cell = collections.defaultdict(lambda: [[], []])
for a, b in zip(E4, E5):
    key = (b["line"], b["table"], b["panel"], b["row"], b["column"])
    by_cell[key][0].append(a["printed"])
    by_cell[key][1].append(b["printed"])
need(all(x == y for x, y in by_cell.values()), "a cell whose printed tokens differ")
on_changed = collections.Counter(b["line"] for b in E5 if b["line"] in pos_changed)
kept = {no: c - n_cell.get(no, 0) for no, c in on_changed.items()}
print("\n== cells.json: %d entries in v4 and %d in v5; every key but `cell` equal; `cell` changed on %d entries %s"
      % (len(E4), len(E5), sum(n_cell.values()), dict(sorted(n_cell.items()))))
print("entries on changed lines, per line:", dict(sorted(on_changed.items())))
print("of those, keeping their cell:", dict(sorted((k, v) for k, v in kept.items() if v)))
need(not n_cell, "an entry whose cell changed (CHANGES_v5.md: none)")
need(dict(on_changed) == {135: 3}, "the entries on changed lines are not 3 on line 135")
e135 = [b for b in E5 if b["line"] == 135]
need([(b["table"], b["row"], b["column"], b["part"], b["cell"]) for b in e135]
     == [("S3.21", "E3m", p, "files", "passed (1 file)") for p in ("pm25", "ndvi", "fire")],
     "line 135: the entries are not E3m `files` of PM2.5, NDVI and burned fraction with cell 'passed (1 file)'")
# the entries' cells on the changed lines are cells that did not change (the same cell, the same text in v4 and v5)
for b in E5:
    if b["line"] in pos_changed:
        ia, ib = cell_index(L4[b["line"] - 1], b["cell"]), cell_index(L5[b["line"] - 1], b["cell"])
        need(len(ib) >= 1 and ia == ib, "an entry on changed line %d whose cell is not the same v4 cell" % b["line"])
print("cells with entries: %d; each prints the same tokens in the same order in v4 and v5" % len(by_cell))
print("cells.json byte-identical to cells_v4.json:", raw["cells.json"] == raw["cells_v4.json"])

numbers_unchanged = same and not fails
print("\nnumbers_unchanged:", numbers_unchanged, "| n_lines:", len(L5), "| entries:", len(E5))
print("failures:", len(fails))
for m in fails[:50]:
    print("FAIL", m)
sys.exit(1 if fails else 0)
