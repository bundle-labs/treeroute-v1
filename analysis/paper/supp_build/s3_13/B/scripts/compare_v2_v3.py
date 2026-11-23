# Comparison only (builder B): version 3 of OUT\B\tables.md and cells.json against version 2 (OUT\B\tables_v2.md and
# cells_v2.json, byte copies made before the rebuild). Writes nothing.
# Since the version-4 rebuild, tables.md and cells.json hold version 4, so version 3 is read from its byte copies
# OUT\B\tables_v3.md and cells_v3.json (V3_MD and V3_CJ below); the checks are unchanged.
#
# 1. Lists every changed line of tables.md. No line is added or dropped, so v2 line k is v3 line k.
# 2. Builds the expected version 3 from version 2 by the change order's OLD and NEW printed texts, as quoted in
#    OUT\spec\CHANGES_v3.md (each also found in OUT\_brief\fix_order_v3.md, its wrapped lines joined by one space; the
#    texts that the order starts with "..." are looked for with that start), and requires it equal to version 3.
# 3. Number tokens: on a changed line the tokens removed are tokens of the OLD texts applied to that line and the
#    tokens added are tokens of its NEW texts; in a table row every cell keeps its number tokens; the other lines are
#    unchanged.
# 4. cells.json: every entry equals its v2 entry in every key but `cell`, and `cell` differs only where the cell text
#    itself changed (the same cell of a changed line), so every printed token is the v2 token of the same cell.
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
CHANGES = os.path.join(OUT_DIR, "spec", "CHANGES_v3.md")
ORDER = os.path.join(OUT_DIR, "_brief", "fix_order_v3.md")

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


V3_MD, V3_CJ = "tables_v3.md", "cells_v3.json"  # the version-3 outputs (byte copies made before the version-4 rebuild)
raw = {n: rb(n) for n in ("tables_v2.md", V3_MD, "cells_v2.json", V3_CJ)}
for n, b in raw.items():
    print("%-14s sha256 %s  %d bytes" % (n, hashlib.sha256(b).hexdigest(), len(b)))
for n in ("tables_v2.md", V3_MD):
    need(raw[n].endswith(b"\n") and not raw[n].endswith(b"\n\n") and b"\r" not in raw[n], n + ": line ends")
L2 = raw["tables_v2.md"].decode("utf-8")[:-1].split("\n")
L3 = raw[V3_MD].decode("utf-8")[:-1].split("\n")
print("lines: v2 %d, v3 %d" % (len(L2), len(L3)))
need(len(L2) == len(L3) == 785, "the line counts are not 785 and 785")
N = min(len(L2), len(L3))

# ---------------------------------------------------------------------------------------------------------------------
# The order's printed texts, from CHANGES_v3.md (fenced blocks whose label line says "printed text")

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
need(not inside, "CHANGES_v3.md: an unclosed fence")
PRINTED = collections.OrderedDict()
for sec, lab, body in blocks:
    if "printed text" in lab:
        PRINTED.setdefault(sec, []).append((lab, body))
want_counts = collections.OrderedDict([("V3-1", 13), ("V3-2", 10), ("V3-3", 4), ("V3-4", 2), ("V3-5", 2),
                                       ("V3-6", 20), ("V3-7", 4)])
need(list(PRINTED.keys()) == list(want_counts.keys()), "CHANGES_v3.md: printed blocks in sections %r" % list(PRINTED))
for sec, n in want_counts.items():
    need(len(PRINTED.get(sec, [])) == n, "CHANGES_v3.md %s: %d printed blocks, expected %d" % (sec, len(PRINTED.get(sec, [])), n))
n_old = sum(1 for v in PRINTED.values() for lab, body in v if "OLD printed text" in lab)
n_new = sum(1 for v in PRINTED.values() for lab, body in v if "NEW printed text" in lab)
print("CHANGES_v3.md: %d fenced blocks, %d printed texts (%d OLD, %d NEW)" % (len(blocks), n_old + n_new, n_old, n_new))
need((n_old, n_new) == (27, 28), "CHANGES_v3.md: not 27 OLD and 28 NEW printed texts")


def pt(sec, idx, must):
    lab, body = PRINTED[sec][idx]
    need(must in lab, "CHANGES_v3.md %s printed block %d has label %r, expected %r" % (sec, idx, lab, must))
    need(len(body) == 1, "CHANGES_v3.md %s printed block %d has %d lines" % (sec, idx, len(body)))
    return body[0]


T = collections.OrderedDict([
    ("t9_sent_new", pt("V3-1", 0, "(NEW printed text)")),
    ("t9_rbo_old", pt("V3-1", 1, "Table 9 caption, OLD")), ("t9_rbo_new", pt("V3-1", 2, "NEW printed text")),
    ("t9_oh_old", pt("V3-1", 3, "Table 9 caption, OLD")), ("t9_oh_new", pt("V3-1", 4, "NEW printed text")),
    ("s319_j_old", pt("V3-1", 5, "S3.19 caption, OLD")), ("s319_j_new", pt("V3-1", 6, "NEW printed text")),
    ("ss_de_old", pt("V3-1", 7, "OLD printed text")), ("ss_de_new", pt("V3-1", 8, "NEW printed text")),
    ("ss_deg_old", pt("V3-1", 9, '"(d, e, g)", OLD')), ("ss_deg_new", pt("V3-1", 10, "NEW printed text")),
    ("s329_old", pt("V3-1", 11, "Caption of S3.29, OLD")), ("s329_new", pt("V3-1", 12, "NEW printed text")),
    ("s318_cap_old", pt("V3-2", 0, "Caption, OLD")), ("s318_cap_new", pt("V3-2", 1, "NEW printed text")),
    ("s318_src_old", pt("V3-2", 2, "source comment, OLD")), ("s318_src_new", pt("V3-2", 3, "NEW printed text")),
    ("s318_lab_old", pt("V3-2", 4, "Panel b label, OLD")), ("s318_lab_new", pt("V3-2", 5, "NEW printed text")),
    ("s318_row_old", pt("V3-2", 6, "baselines row, OLD")), ("s318_row_new", pt("V3-2", 7, "NEW printed text")),
    ("s318_note_old", pt("V3-2", 8, "note line after panel b")), ("s318_note_new", pt("V3-2", 9, "NEW printed text")),
    ("count_old", pt("V3-3", 0, "all five captions, OLD")), ("count_new", pt("V3-3", 1, "NEW printed text")),
    ("xsrc_old", pt("V3-3", 2, "`{extra_src}`")), ("xsrc_new", pt("V3-3", 3, "NEW printed text")),
    ("bardl_old", pt("V3-4", 0, "OLD printed text (the footnote's second sentence)")),
    ("bardl_new", pt("V3-4", 1, "NEW printed text")),
    ("cross_old", pt("V3-5", 0, "OLD printed text")), ("cross_new", pt("V3-5", 1, "NEW printed text")),
    ("guard_old", pt("V3-6", 0, "five treeroute v1 rows")), ("guard_new", pt("V3-6", 1, "NEW printed text")),
    ("arm_old", pt("V3-6", 2, "first row label")), ("arm_new", pt("V3-6", 3, "NEW printed text")),
    ("rf_old", pt("V3-6", 4, "random-forest rows")), ("rf_new", pt("V3-6", 5, "NEW printed text")),
    ("notec_old", pt("V3-6", 6, "S3.19 note")), ("notec_new", pt("V3-6", 7, "NEW printed text")),
    ("e10_old", pt("V3-6", 8, "E10's")), ("e10_new", pt("V3-6", 9, "NEW printed text")),
    ("e3a_old", pt("V3-6", 10, "E3a's")), ("e3a_new", pt("V3-6", 11, "NEW printed text")),
    ("e3m_old", pt("V3-6", 12, "E3m's")), ("e3m_new", pt("V3-6", 13, "NEW printed text")),
    ("e3_old", pt("V3-6", 14, "E3's")), ("e3_new", pt("V3-6", 15, "NEW printed text")),
    ("e6_old", pt("V3-6", 16, "E6's")), ("e6_new", pt("V3-6", 17, "NEW printed text")),
    ("link_ex_old", pt("V3-6", 18, "Link cell of every Ridge pair")), ("link_ex_new", pt("V3-6", 19, "NEW printed text")),
    ("hdr_v2_old", pt("V3-7", 0, "Header comment, OLD")), ("hdr_v2_new", pt("V3-7", 1, "NEW printed text")),
    ("hdr_cj_old", pt("V3-7", 2, "Header comment, OLD")), ("hdr_cj_new", pt("V3-7", 3, "NEW printed text")),
])

# each text is also in the change order itself (its backticked spans, the order's wrapped lines joined by one space);
# the order starts the shares tails and the S3.29 text with "..."; the Link cell example is checked against the
# order's M and P
with open(ORDER, "r", encoding="utf-8") as f:
    order_flat = re.sub(r"\n[ ]*", " ", f.read())
TAILS = ("ss_de_old", "ss_de_new", "ss_deg_old", "ss_deg_new", "s329_old", "s329_new")
n_found = 0
for k, v in T.items():
    if k.startswith("link_ex"):
        continue
    probe = ("`..." if k in TAILS else "`") + v + "`"
    if need(probe in order_flat, "fix_order_v3.md does not hold the text %s" % k):
        n_found += 1
m_link = re.search(r"Table S3\.25, every pair label that carries it \(panels a and b; Ridge's pairs\)\. OLD: `([^`]+)` "
                   r"NEW: `([^`]+)`", order_flat)
M, P = (m_link.group(1), m_link.group(2)) if need(m_link is not None, "the order's S3.25 item") else ("", "")
need(M in T["link_ex_old"] and T["link_ex_new"] == T["link_ex_old"].replace(M, P),
     "CHANGES_v3.md's Link cell example is not the order's OLD -> NEW")
m_anchor = re.search(r"a new sentence directly after `([^`]+)` NEW: `([^`]+)`", order_flat)
ANCHOR = m_anchor.group(1) if need(m_anchor is not None, "the order's Table 9 item") else ""
need(m_anchor is not None and m_anchor.group(2) == T["t9_sent_new"], "the order's new Table 9 sentence")
print("order texts found in fix_order_v3.md: %d of %d (and M, P and the Table 9 anchor)" % (n_found, len(T) - 2))

# ---------------------------------------------------------------------------------------------------------------------
# The expected version 3: version 2 with the order's changes applied (no line added or dropped)

TABLE_AT = []
cur_t = None
for ln in L2:
    mt = re.match(r"^\*\*Table (9|S3\.\d+)[ .]", ln)
    if mt:
        cur_t = mt.group(1)
    TABLE_AT.append(cur_t)

EXP = list(L2)
APPLIED = collections.defaultdict(list)  # line index -> list of (item, old, new)


def rep(item, old, new, n_lines, where=lambda i, ln: True, wrap=("", "")):
    o = wrap[0] + old + wrap[1]
    w = wrap[0] + new + wrap[1]
    hits = [i for i, ln in enumerate(EXP) if o in ln and where(i, ln)]
    need(len(hits) == n_lines, "%s %r: in %d lines, expected %d" % (item, old[:50], len(hits), n_lines))
    for i in hits:
        need(EXP[i].count(o) == 1, "%s: more than once on line %d" % (item, i + 1))
        EXP[i] = EXP[i].replace(o, w)
        APPLIED[i].append((item, o, w))
    return hits


def starts(prefix):
    return lambda i, ln: ln.startswith(prefix)


def caption_of(nums):
    return lambda i, ln: any(ln.startswith("**Table S3.%s (post hoc).**" % x) for x in nums)


def whole(text):
    return lambda i, ln: ln == text


rep("V3-7", T["hdr_v2_old"], T["hdr_v2_new"], 1, where=lambda i, ln: i == 0)
rep("V3-7", T["hdr_cj_old"], T["hdr_cj_new"], 1, where=lambda i, ln: i == 0)
rep("V3-1", ANCHOR + " ", ANCHOR + " " + T["t9_sent_new"] + " ", 1, where=starts("**Table 9.**"))
rep("V3-1", T["t9_rbo_old"], T["t9_rbo_new"], 1, where=starts("**Table 9.**"))
rep("V3-1", T["t9_oh_old"], T["t9_oh_new"], 1, where=starts("**Table 9.**"))
rep("V3-1", T["s319_j_old"], T["s319_j_new"], 1, where=starts("**Table S3.19 (post hoc).**"))
rep("V3-1", T["ss_de_old"], T["ss_de_new"], 3, where=caption_of(("23", "24", "26")))
rep("V3-1", T["ss_deg_old"], T["ss_deg_new"], 2, where=caption_of(("25", "27")))
rep("V3-1", T["s329_old"], T["s329_new"], 1, where=starts("**Table S3.29 (post hoc; sensitivity).**"))
rep("V3-2", T["s318_cap_old"], T["s318_cap_new"], 1, where=starts("**Table S3.18 (post hoc).**"))
rep("V3-2", T["s318_src_old"], T["s318_src_new"], 1, where=starts("**Table S3.18 (post hoc).**"))
rep("V3-2", T["s318_lab_old"], T["s318_lab_new"], 1, where=whole(T["s318_lab_old"]))
rep("V3-2", T["s318_row_old"], T["s318_row_new"], 1, where=whole(T["s318_row_old"]))
rep("V3-2", T["s318_note_old"], T["s318_note_new"], 1, where=whole(T["s318_note_old"]))
rep("V3-3", T["count_old"], T["count_new"], 5, where=caption_of(("23", "24", "25", "26", "27")))
rep("V3-3", T["xsrc_old"], T["xsrc_new"], 1, where=caption_of(("24",)))
rep("V3-4", T["bardl_old"], T["bardl_new"], 1, where=starts("‡ BARDL reads"))
rep("V3-5", T["cross_old"], T["cross_new"], 1, where=starts("| " + T["cross_old"] + " | "), wrap=("| ", " | "))
g_hits = rep("V3-6", T["guard_old"], T["guard_new"], 10, wrap=("| ", " |"))
need(collections.Counter(TABLE_AT[i] for i in g_hits) == {"S3.18": 5, "S3.20": 5}, "the guard cells' tables")
rep("V3-6", T["arm_old"], T["arm_new"], 1, where=starts("| " + T["arm_old"] + " | "), wrap=("| ", " | "))
rf_hits = rep("V3-6", T["rf_old"], T["rf_new"], 5, wrap=("| ", ""))
need(all(TABLE_AT[i] == "S3.18" for i in rf_hits), "the random-forest cells' table")
rep("V3-6", T["notec_old"], T["notec_new"], 1, where=starts("ᶜ Background (B2):"))
rep("V3-6", T["e10_old"], T["e10_new"], 1, where=starts("| E10 | "))
for g in ("e3a", "e3m", "e3", "e6"):
    rep("V3-6", T[g + "_old"], T[g + "_new"], 1, where=starts("| " + {"e3a": "E3a", "e3m": "E3m", "e3": "E3", "e6": "E6"}[g] + " | "),
        wrap=("| ", " | "))
need(sum(ln.count(M) for ln in L2) == 8, "M is not on exactly 8 places of version 2")
l_hits = rep("V3-6", M, P, 8, where=lambda i, ln: ln.startswith("| ") and M in ln[2:-2].split(" | ")[1])
need(all(TABLE_AT[i] == "S3.25" for i in l_hits), "the Link cells' table")

same = (EXP == L3)
need(same, "the expected version 3 (version 2 with the order's texts) differs from tables.md")
if not same:
    for k in range(min(len(EXP), len(L3))):
        if EXP[k] != L3[k]:
            print("EXPECTED != BUILT on line %d" % (k + 1))
print("expected version 3 == built version 3:", same, "| changes applied on", len(APPLIED), "lines,",
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


pos_changed = [k + 1 for k in range(N) if L2[k] != L3[k]]
flat_changes = re.sub(r"\n[ ]*", " ", ch_text)
m_lines = re.search(r"The lines that change \(1-based, (\d+)\): ([0-9, ]+)\.", flat_changes)
want_pos = [int(x) for x in m_lines.group(2).split(", ")] if need(m_lines is not None, "CHANGES_v3.md's line list") else []
need(m_lines is not None and int(m_lines.group(1)) == len(want_pos), "CHANGES_v3.md's line count")
need(pos_changed == want_pos, "the changed lines are not those of CHANGES_v3.md")
print("\n== changed lines of tables.md (1-based; v2 line = v3 line): %d" % len(pos_changed))
print("  " + ", ".join(str(x) for x in pos_changed))
need(sorted(i + 1 for i in APPLIED) == pos_changed, "a changed line without an order item, or an item on an unchanged line")

print("\n== per changed line: table, the order items, the number tokens removed / added")
ADDED_ALL, REMOVED_ALL = collections.Counter(), collections.Counter()
CELLS_CHANGED = {}
for no in pos_changed:
    i = no - 1
    rem, add = toks(L2[i]) - toks(L3[i]), toks(L3[i]) - toks(L2[i])
    olds, news = collections.Counter(), collections.Counter()
    for item, o, w in APPLIED[i]:
        olds += toks(o)
        news += toks(w)
    need(not (rem - olds), "line %d: removed tokens %s outside the OLD texts" % (no, fmt_c(rem - olds)))
    need(not (add - news), "line %d: added tokens %s outside the NEW texts" % (no, fmt_c(add - news)))
    ADDED_ALL += add
    REMOVED_ALL += rem
    ids = "+".join(sorted(set(item for item, o, w in APPLIED[i])))
    extra = ""
    if L2[i].startswith("| "):
        c2, c3 = L2[i][2:-2].split(" | "), L3[i][2:-2].split(" | ")
        if need(len(c2) == len(c3), "line %d: the cell count changed" % no):
            ch = [k for k in range(len(c2)) if c2[k] != c3[k]]
            for k in ch:
                need(toks(c2[k]) == toks(c3[k]), "line %d cell %d: number tokens changed" % (no, k + 1))
            CELLS_CHANGED[no] = ch
            extra = " | cells changed %s, their number tokens unchanged" % [k + 1 for k in ch]
    print("  %4d %-6s [%s] %s | removed %s added %s%s" % (no, TABLE_AT[i] or "-", ids, what(L3[i]), fmt_c(rem),
                                                          fmt_c(add), extra))
for k in range(N):
    if L2[k] == L3[k]:
        need(toks(L2[k]) == toks(L3[k]), "unchanged line with different tokens")
T2, T3 = toks("\n".join(L2)), toks("\n".join(L3))
print("\nnumber tokens in the whole file: v2 %d, v3 %d; removed %s; added %s"
      % (sum(T2.values()), sum(T3.values()), fmt_c(T2 - T3), fmt_c(T3 - T2)))
need(T2 - T3 == REMOVED_ALL and T3 - T2 == ADDED_ALL, "the whole-file token differences are not the per-line ones")

# ---------------------------------------------------------------------------------------------------------------------
# 4. cells.json

d2 = json.loads(raw["cells_v2.json"].decode("utf-8"))
d3 = json.loads(raw[V3_CJ].decode("utf-8"))
need(list(d2.keys()) == list(d3.keys()) == ["tables_file", "spec", "entries"], "cells.json top keys")
need(d2["tables_file"] == d3["tables_file"] == "tables.md" and d2["spec"] == d3["spec"] == "OUT\\spec\\TABLE_SPEC.md",
     "cells.json header values")
E2, E3 = d2["entries"], d3["entries"]
need(len(E2) == len(E3), "cells.json: %d entries in v2, %d in v3" % (len(E2), len(E3)))
SAME_KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "source", "selector", "stored"]


def cell_index(line, cell):
    if line.startswith("| "):
        cs = line[2:-2].split(" | ")
        return [k for k, c in enumerate(cs) if c == cell]
    return [0] if line == cell else []


n_cell = collections.Counter()
for k, (a, b) in enumerate(zip(E2, E3)):
    need(list(a.keys()) == list(b.keys()), "entry %d: keys" % k)
    for key in SAME_KEYS:
        need(a[key] == b[key], "entry %d (line %d): %s differs: %r -> %r" % (k, a["line"], key, a[key], b[key]))
    need(b["cell"] in L3[b["line"] - 1] and b["printed"] in b["cell"], "entry %d: not on its v3 line" % k)
    if a["cell"] != b["cell"]:
        no = a["line"]
        ia, ib = cell_index(L2[no - 1], a["cell"]), cell_index(L3[no - 1], b["cell"])
        ok = no in pos_changed and len(ia) >= 1 and ia == ib
        if need(ok, "entry %d (line %d): cell changed but it is not the same cell of a changed line" % (k, no)):
            n_cell[no] += 1
by_cell = collections.defaultdict(lambda: [[], []])
for a, b in zip(E2, E3):
    key = (b["line"], b["table"], b["panel"], b["row"], b["column"])
    by_cell[key][0].append(a["printed"])
    by_cell[key][1].append(b["printed"])
need(all(x == y for x, y in by_cell.values()), "a cell whose printed tokens differ")
on_changed = collections.Counter(b["line"] for b in E3 if b["line"] in pos_changed)
kept = {no: c - n_cell.get(no, 0) for no, c in on_changed.items()}
print("\n== cells.json: %d entries in v2 and %d in v3; every key but `cell` equal; `cell` changed on %d entries %s"
      % (len(E2), len(E3), sum(n_cell.values()), dict(sorted(n_cell.items()))))
print("entries on changed lines, per line:", dict(sorted(on_changed.items())))
print("of those, keeping their cell:", dict(sorted((k, v) for k, v in kept.items() if v)))
need(dict(n_cell) == {344: 12}, "the cell changes are not the 12 entries of line 344")
need(sum(1 for x, y in by_cell.values() if x == y) == len(by_cell), "printed tokens per cell")
print("cells with entries: %d; each prints the same tokens in the same order in v2 and v3" % len(by_cell))

numbers_unchanged = same and not fails
print("\nnumbers_unchanged:", numbers_unchanged, "| n_lines:", len(L3))
print("failures:", len(fails))
for m in fails[:50]:
    print("FAIL", m)
sys.exit(1 if fails else 0)
