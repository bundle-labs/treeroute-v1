# -*- coding: utf-8 -*-
# Builder A: version 5 of the outputs against version 4, by script (prints only; writes nothing).
# Reads OUT\A\tables_v4.md and OUT\A\cells_v4.json (byte copies of version 4), OUT\A\tables.md and OUT\A\cells.json
# (version 5), the order's OLD and NEW printed texts as OUT\spec\CHANGES_v5.md quotes them (6 OLD, 6 NEW and the
# sentence that V5-5 adds; each must also be in the order OUT\_brief\fix_order_v5.md, wrapped lines joined by one
# space), and what CHANGES_v5.md expects of the outputs (the line count, the changed lines, the entries, the entries
# on changed lines and their cell, the number tokens added).
# 1. Lines: the same count in v4 and v5 (no line added or dropped, so v4 line n = v5 line n); every line that differs.
# 2. Expected version 5: version 4 with each order text applied where the order names it (each edit's count of
#    places is fixed below and must be found exactly) and the V5-5 sentence inserted directly after the Version 4
#    sentence; it must equal tables.md byte for byte, and the lines it changes must be CHANGES_v5.md's list.
# 3. Number tokens (digit runs with internal , or ., and runs of superscript digits): on every line the tokens outside
#    the edited spans are the same tokens at the same places; every added or removed token lies inside an edited span
#    (an order text) and none straddles a span's edge; the file's token difference is the sum over the edits.
#    3b. Cell by cell (a table row's cells; any other line is one cell): the number tokens of every v5 cell equal those
#    of the same v4 cell, in order, except in a cell that holds an edit, whose added and removed tokens are the edit's.
# 4. cells.json: the v4 and v5 entries paired by position; every key equal except `cell`, which may differ only where
#    an edited span lies inside that cell, and then is the v5 text of that cell; every printed token found at its v4
#    place, shifted only by the edits before it on its line.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import json
import hashlib
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_X = os.path.dirname(HERE)
OUT = os.path.dirname(OUT_X)
fails = []


def bad(msg):
    fails.append(msg)


raw = {}
for n in ("tables_v4.md", "tables.md", "cells_v4.json", "cells.json"):
    with open(os.path.join(OUT_X, n), "rb") as f:
        raw[n] = f.read()
    print("%s  %9d bytes  %s" % (hashlib.sha256(raw[n]).hexdigest(), len(raw[n]), n))
for n in ("tables_v4.md", "tables.md"):
    if not raw[n].endswith(b"\n") or b"\r" in raw[n] or raw[n].startswith(b"\xef\xbb\xbf"):
        bad(n + ": line ends or BOM")
A = raw["tables_v4.md"].decode("utf-8").split("\n")[:-1]
B = raw["tables.md"].decode("utf-8").split("\n")[:-1]

# ------------------------------------------------------------------ the order's texts (CHANGES_v5.md, fix_order_v5.md)
with open(os.path.join(OUT, "spec", "CHANGES_v5.md"), "r", encoding="utf-8") as f:
    CH = f.read().split("\n")
items, sec, i = [], None, 0
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
            kind = "O" if "OLD printed" in label else ("N" if "NEW printed" in label else "?")
            if kind == "?" or len(body) != 1:
                bad("CHANGES_v5.md block at line %d: %r" % (i + 1, label))
            items.append((sec, kind, body[0], label))
        elif not label.endswith("spec text:"):
            bad("CHANGES_v5.md block at line %d has an unknown label: %r" % (i + 1, label))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text, label in items:
    seq.setdefault(s_, []).append((kind, text, label))
got = {s_: "".join(k for k, t, lab in v) for s_, v in seq.items()}
if got != {"V5-1": "ON", "V5-2": "ONON", "V5-3": "ONON", "V5-4": "ON", "V5-5": "N"}:
    bad("CHANGES_v5.md printed-text blocks: %r" % got)
n_old = sum(k == "O" for s_, k, t, lab in items)
n_new = sum(k == "N" for s_, k, t, lab in items)
if not ("Table 9 caption" in seq["V5-2"][0][2] and "note ᶜ" in seq["V5-2"][2][2]
        and "E5's" in seq["V5-3"][0][2] and "Note ᵃ" in seq["V5-3"][2][2]):
    bad("CHANGES_v5.md: labels of V5-2 and V5-3")


def prs(s_):
    v = seq[s_]
    return [(v[q][1], v[q + 1][1]) for q in range(0, len(v) - 1, 2)]


V51, V52, V53, V54 = prs("V5-1"), prs("V5-2"), prs("V5-3"), prs("V5-4")
INS, INS_LABEL = seq["V5-5"][0][1], seq["V5-5"][0][2]
mo_a = re.findall(r"which ends `([^`]+)`", INS_LABEL)
mo_b = re.findall(r"and before `([^`]+)`", INS_LABEL)
AFTER, BEFORE = (mo_a[0], mo_b[0]) if len(mo_a) == 1 and len(mo_b) == 1 else (None, None)
with open(os.path.join(OUT, "_brief", "fix_order_v5.md"), "r", encoding="utf-8") as f:
    flat_order = " ".join(x.strip() for x in f.read().split("\n"))
not_in_order = [(s_, k) for s_, k, t, lab in items if t not in flat_order]
if not_in_order:
    bad("texts not in the order: %r" % not_in_order)
flat_ch = " ".join(x.strip() for x in CH)
mo = re.search(r"tables\.md keeps its (\d+) lines", flat_ch)
N_LINES = int(mo.group(1)) if mo else None
mo = re.search(r"The lines that change \(1-based, (\d+)\): ([0-9, ]+)\.", flat_ch)
EXPECTED_CHANGED = [int(x) for x in mo.group(2).split(", ")] if mo else []
if not mo or int(mo.group(1)) != len(EXPECTED_CHANGED):
    bad("CHANGES_v5.md: list of changed lines not found")
mo = re.search(r"cells\.json keeps its ([0-9,]+) entries", flat_ch)
N_ENTRIES = int(mo.group(1).replace(",", "")) if mo else None
mo = re.search(r"The (\d+) entries on changed lines \(on line (\d+), [^)]+\) keep their `cell` `([^`]+)`", flat_ch)
ON_CHANGED = {int(mo.group(2)): int(mo.group(1))} if mo else {}
KEPT_CELL = mo.group(3) if mo else None
if not mo:
    bad("CHANGES_v5.md: the entries on changed lines not found")
print("order texts (CHANGES_v5.md): %d OLD, %d NEW (the V5-5 sentence among them); all in fix_order_v5.md: %s; "
      "V5-5 anchor %r, followed by %r" % (n_old, n_new, not not_in_order, AFTER, BEFORE))

# ------------------------------------------------------------------ 1. lines
print("lines: v4 %d, v5 %d (CHANGES_v5.md: %s)" % (len(A), len(B), N_LINES))
if not (len(A) == len(B) == N_LINES):
    bad("line counts differ")
diff_lines = [n + 1 for n in range(min(len(A), len(B))) if A[n] != B[n]]

# ------------------------------------------------------------------ 2. expected version 5
# (id, OLD, NEW, places, match): match "sub" = anywhere in a line; "cell" = a whole table cell; "line" = a whole line;
# "ins" = NEW + " " inserted between OLD = (after, before) + " ", which both stay
EDITS = [
    ("V5-5 header comment: the Version 5 sentence", (AFTER, BEFORE), INS, 1, "ins"),
    ("V5-2 Table 9 caption: coral bleaching's background", V52[0][0], V52[0][1], 1, "sub"),
    ("V5-1 Table 9 caption: the context-and-calendar family", V51[0][0], V51[0][1], 1, "sub"),
    ("V5-2 S3.19 note c", V52[1][0], V52[1][1], 1, "sub"),
    ("V5-4 S3.21 E3m", V54[0][0], V54[0][1], 1, "cell"),
    ("V5-3 S3.21 E5", V53[0][0], V53[0][1], 1, "cell"),
    ("V5-3 S3.21 note a", V53[1][0], V53[1][1], 1, "sub"),
]
if len(EDITS) != 7 or n_old != 6 or n_new != 7:
    bad("edit list: %d edits, %d OLD, %d NEW" % (len(EDITS), n_old, n_new))
spans = {}  # v4 line -> [(start, end, NEW, id)]
for eid, old, newt, places, how in EDITS:
    if old is None or old == "" or old == (None, None):
        bad("%s: no OLD text" % eid)
        continue
    found = []
    for n, a in enumerate(A, 1):
        if how == "line":
            if a == old:
                found.append((n, 0, len(a), newt))
            continue
        pat = {"sub": old, "cell": "| %s |" % (old,), "ins": "%s %s" % old if how == "ins" else None}[how]
        pos = a.find(pat)
        while pos >= 0:
            if how == "sub":
                found.append((n, pos, pos + len(old), newt))
            elif how == "cell":
                found.append((n, pos + 2, pos + 2 + len(old), newt))
            else:
                q = pos + len(old[0]) + 1
                found.append((n, q, q, newt + " "))
            pos = a.find(pat, pos + 1)
    if len(found) != places:
        bad("%s: found at %d places, the order names %d" % (eid, len(found), places))
    for n, s, e, t in found:
        spans.setdefault(n, []).append((s, e, t, eid))
for n in spans:
    spans[n].sort()
    for (s1, e1, t1, i1), (s2, e2, t2, i2) in zip(spans[n], spans[n][1:]):
        if s2 < e1 or (s2 == e1 == s1 == e2):
            bad("line %d: edits %s and %s overlap" % (n, i1, i2))
T = []
for n, a in enumerate(A, 1):
    out, last = [], 0
    for s, e, t, eid in spans.get(n, []):
        out += [a[last:s], t]
        last = e
    out.append(a[last:])
    T.append("".join(out))
exp = ("\n".join(T) + "\n").encode("utf-8")
same = exp == raw["tables.md"]
print("expected v5 (v4 + %d edits at %d places on %d lines): sha256 %s; equal to tables.md: %s"
      % (len(EDITS), sum(len(v) for v in spans.values()), len(spans), hashlib.sha256(exp).hexdigest(), same))
if not same:
    bad("tables.md is not v4 + the order's texts")
    for n in range(min(len(T), len(B))):
        if T[n] != B[n]:
            print("    line %d differs: expected %r / got %r" % (n + 1, T[n][:160], B[n][:160]))
print("lines that differ, v4 vs v5 (same line number): %d: %s" % (len(diff_lines), ", ".join(map(str, diff_lines))))
if diff_lines != sorted(spans) or diff_lines != EXPECTED_CHANGED:
    bad("the changed lines are not the edited lines or not CHANGES_v5.md's list")
print("equal to CHANGES_v5.md's list of %d lines: %s" % (len(EXPECTED_CHANGED), diff_lines == EXPECTED_CHANGED))

# ------------------------------------------------------------------ 3. number tokens
TOK = re.compile(r"\d+(?:[.,]\d+)*|[⁰¹²³⁴-⁹⁻]+")


def regions(n, which):
    """(start, end, kind) of the line's segments and edit spans, in order; which = 'a' (v4) or 'b' (v5)."""
    out, pa, pb = [], 0, 0
    for s, e, t, eid in spans.get(n, []):
        seg = s - pa
        out.append((pb if which == "b" else pa, (pb if which == "b" else pa) + seg, "seg"))
        pb += seg
        pa = s
        if which == "b":
            out.append((pb, pb + len(t), eid))
        else:
            out.append((pa, e, eid))
        pb += len(t)
        pa = e
    a_len = len(A[n - 1])
    out.append((pb if which == "b" else pa, (pb + a_len - pa) if which == "b" else a_len, "seg"))
    return out


def classify(text, regs, where):
    seg_toks, span_toks = [], {}
    for mo in TOK.finditer(text):
        s, e = mo.start(), mo.end()
        hit = [(q, r) for q, r in enumerate(regs) if r[0] <= s < r[1]]
        if len(hit) != 1 or not (hit[0][1][0] <= s and e <= hit[0][1][1]):
            bad("%s: token %r at %d straddles an edit's edge" % (where, mo.group(0), s))
            continue
        q, r = hit[0]
        if r[2] == "seg":
            seg_toks.append((q, s - r[0], mo.group(0)))
        else:
            span_toks.setdefault(q, []).append(mo.group(0))
    return seg_toks, span_toks


added_all, removed_all = Counter(), Counter()
added_by_line, removed_by_line = {}, {}
changed_report = []
cur_table, cur_panel = None, ""
where_of = {}
for n, b in enumerate(B, 1):
    mt = re.match(r"^\*\*Table (S3\.\d+|\d+)", b)
    if mt:
        cur_table, cur_panel = mt.group(1), ""
        where_of[n] = "Table %s caption" % cur_table
    elif re.match(r"^\*\*([a-g])\. ", b):
        cur_panel = b[2]
        where_of[n] = "Table %s panel %s label" % (cur_table, cur_panel)
    elif n == 1:
        where_of[n] = "header comment"
    elif b.startswith("| ") and n < len(B) and B[n].startswith("|---"):
        where_of[n] = "Table %s%s column header" % (cur_table, (" " + cur_panel) if cur_panel else "")
    elif b.startswith("| "):
        c = b[2:-2].split(" | ")
        first = c[0] + ((" / " + c[1]) if (cur_table, cur_panel) in (("S3.18", "a"), ("S3.20", "")) else "")
        where_of[n] = "Table %s%s row %s" % (cur_table, (" " + cur_panel) if cur_panel else "", first)
    else:
        where_of[n] = "Table %s note%s" % (cur_table, (" " + b[0]) if b[:1] in "ᵃᵇᶜᵈ†‡§" and b[:1] else "")
for n in range(1, len(A) + 1):
    if n > len(B):
        break
    ra, rb = regions(n, "a"), regions(n, "b")
    sa, xa = classify(A[n - 1], ra, "v4 line %d" % n)
    sb, xb = classify(B[n - 1], rb, "v5 line %d" % n)
    if sa != sb:
        bad("line %d: the tokens outside the edits differ" % n)
    if n not in spans:
        continue
    parts = []
    for q, r in enumerate(rb):
        if r[2] == "seg":
            continue
        old_toks = Counter(xa.get(q, []))
        new_toks = Counter(xb.get(q, []))
        add, rem = new_toks - old_toks, old_toks - new_toks
        added_all += add
        removed_all += rem
        if add:
            added_by_line.setdefault(n, Counter()).update(add)
        if rem:
            removed_by_line.setdefault(n, Counter()).update(rem)
        s, e = ra[q][0], ra[q][1]
        old_text, new_text = A[n - 1][s:e], B[n - 1][r[0]:r[1]]
        extra = []
        if add:
            extra.append("number tokens added: " + ", ".join("%s x%d" % kv for kv in sorted(add.items())))
        if rem:
            extra.append("number tokens removed: " + ", ".join("%s x%d" % kv for kv in sorted(rem.items())))
        if s == e:
            parts.append("%s: inserted \"%s\"%s" % (r[2], new_text.rstrip(" "), (" (" + "; ".join(extra) + ")") if extra else ""))
        else:
            parts.append("%s: \"%s\" -> \"%s\"%s" % (r[2], old_text, new_text, (" (" + "; ".join(extra) + ")") if extra else ""))
    changed_report.append("L%d (%s): %s" % (n, where_of[n], " | ".join(parts)))
ca = Counter(t for line in A for t in TOK.findall(line))
cb = Counter(t for line in B for t in TOK.findall(line))
if (cb - ca) != (added_all - removed_all) or (ca - cb) != (removed_all - added_all):
    bad("the file's token difference is not the sum over the edits")
# CHANGES_v5.md: tokens added only on line 1 (the V5-5 sentence: "Version 5", the date and the path) and on line 135
# (the "256" of SHA-256, V5-4); none removed
if removed_all or sorted(added_by_line) != [1, 135] or added_by_line.get(135) != Counter({"256": 1}) \
        or added_by_line.get(1) != Counter(TOK.findall(INS)):
    bad("number tokens added or removed other than CHANGES_v5.md says: added %r, removed %r" % (added_by_line,
                                                                                               removed_by_line))
print("number tokens in the file: v4 %d, v5 %d; added (all inside order texts) %s; removed %s" % (
    sum(ca.values()), sum(cb.values()), dict(sorted(added_all.items())), dict(sorted(removed_all.items())) or "none"))
print("lines with added number tokens: %s" % ", ".join("%d: %s" % (n, dict(sorted(c.items())))
                                                       for n, c in sorted(added_by_line.items())))


# 3b. cell by cell
def cells_of(t):
    return t[2:-2].split(" | ") if t.startswith("| ") else [t]


def cell_spans(t):
    """(start, end) of each cell of the line, as cells_of splits it."""
    if not t.startswith("| "):
        return [(0, len(t))]
    out, pos = [], 2
    for c in cells_of(t):
        out.append((pos, pos + len(c)))
        pos += len(c) + 3
    return out


n_cells, n_same, tok_cells = 0, 0, []
for n in range(1, min(len(A), len(B)) + 1):
    xa_, xb_ = cells_of(A[n - 1]), cells_of(B[n - 1])
    if len(xa_) != len(xb_):
        bad("line %d: %d cells in v4, %d in v5" % (n, len(xa_), len(xb_)))
        continue
    csa = cell_spans(A[n - 1])
    for ci, (x, y) in enumerate(zip(xa_, xb_)):
        n_cells += 1
        tx, ty = TOK.findall(x), TOK.findall(y)
        if tx == ty:
            n_same += 1
            continue
        edits_in = [(s, e, t, eid) for s, e, t, eid in spans.get(n, []) if csa[ci][0] <= s and e <= csa[ci][1]]
        add = Counter(ty) - Counter(tx)
        rem = Counter(tx) - Counter(ty)
        want_add = Counter()
        want_rem = Counter()
        for s, e, t, eid in edits_in:
            want_add += Counter(TOK.findall(t))
            want_rem += Counter(TOK.findall(A[n - 1][s:e]))
        net_add, net_rem = want_add - want_rem, want_rem - want_add
        if not edits_in or add != net_add or rem != net_rem:
            bad("line %d cell %d: number tokens changed outside an order text (added %r, removed %r)" % (n, ci, add, rem))
        tok_cells.append((n, ci, dict(sorted(add.items())), dict(sorted(rem.items()))))
print("cells compared: %d; number tokens equal in order (v4 = v5): %d; cells whose tokens differ: %d (%s), each "
      "only by the tokens of the order texts inside it" % (n_cells, n_same, len(tok_cells), "; ".join(
          "line %d cell %d: added %s, removed %s" % (n, ci, a, r or "none") for n, ci, a, r in tok_cells)))
if sorted((n, ci) for n, ci, a, r in tok_cells) != [(1, 0), (135, 1)]:
    bad("the cells whose number tokens differ are not line 1 and the E3m row's 'What it checks' cell")
print("changed lines (v4 line = v5 line; edit: OLD -> NEW):")
for t in changed_report:
    print("  " + t)

# ------------------------------------------------------------------ 4. cells.json
D4 = json.loads(raw["cells_v4.json"].decode("utf-8"))
D5 = json.loads(raw["cells.json"].decode("utf-8"))
if list(D4.keys()) != list(D5.keys()) or D4["tables_file"] != D5["tables_file"] or D4["spec"] != D5["spec"]:
    bad("cells.json top keys, tables_file or spec differ")
if D5["spec"] != "OUT\\spec\\TABLE_SPEC.md" or D5["tables_file"] != "tables.md":
    bad("cells.json: spec or tables_file is not as CHANGES_v5.md says")
if json.dumps(D5, ensure_ascii=False, indent=1, allow_nan=False) + "\n" != raw["cells.json"].decode("utf-8"):
    bad("cells.json v5 is not the canonical dump")
E4, E5 = D4["entries"], D5["entries"]
print("entries: v4 %d, v5 %d (CHANGES_v5.md: %s); tables_file %r, spec %r" % (len(E4), len(E5), N_ENTRIES,
                                                                            D5["tables_file"], D5["spec"]))
if not (len(E4) == len(E5) == N_ENTRIES):
    bad("entry counts differ")
KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "cell", "source", "selector", "stored"]


def locate(lines, entries):
    """(offset of the printed token in its line, cell start, cell end) of every entry, in reading order."""
    out = []
    prev = (0, -1, -1)
    for e in entries:
        t = lines[e["line"] - 1]
        if t.startswith("| "):
            cells = t[2:-2].split(" | ")
            starts, pos = [], 2
            for c in cells:
                starts.append(pos)
                pos += len(c) + 3
        else:
            cells, starts = [t], [0]
        found = None
        for ci in range(prev[1] if prev[0] == e["line"] else 0, len(cells)):
            if cells[ci] == e["cell"]:
                fp = prev[2] if (prev[0] == e["line"] and ci == prev[1]) else 0
                q = cells[ci].find(e["printed"], max(fp, 0))
                if q >= 0:
                    found = (ci, q + len(e["printed"]), starts[ci] + q, starts[ci], starts[ci] + len(cells[ci]))
                    break
        if found is None:
            out.append(None)
            prev = (e["line"], 0, 0)
        else:
            out.append(found[2:])
            prev = (e["line"], found[0], found[1])
    return out


L4, L5 = locate(A, E4), locate(B, E5)
if None in L4 or None in L5:
    bad("an entry is not found in reading order (v4 %d, v5 %d)" % (L4.count(None), L5.count(None)))
cell_changed = Counter()
moved = 0
on_changed = Counter()
cells_on_changed = Counter()
for n_, (e4, e5) in enumerate(zip(E4, E5)):
    if list(e4.keys()) != KEYS or list(e5.keys()) != KEYS:
        bad("entry %d: keys" % n_)
        continue
    for k in KEYS:
        if k != "cell" and e4[k] != e5[k]:
            bad("entry %d: %s %r -> %r" % (n_, k, e4[k], e5[k]))
    ln = e4["line"]
    if ln in spans:
        on_changed[ln] += 1
        cells_on_changed[e5["cell"]] += 1
    if L4[n_] is None or L5[n_] is None:
        continue
    o4, c4s, c4e = L4[n_]
    o5 = L5[n_][0]
    sp = spans.get(ln, [])
    shift = 0
    for s, e, t, eid in sp:
        if e <= o4:
            shift += len(t) - (e - s)
        elif s < o4 + len(e4["printed"]) and o4 < e:
            bad("entry %d: printed token inside the edit %s" % (n_, eid))
    if o5 != o4 + shift:
        bad("entry %d: printed token at %d in v5, expected %d" % (n_, o5, o4 + shift))
    if B[ln - 1][o5:o5 + len(e5["printed"])] != e5["printed"] or A[ln - 1][o4:o4 + len(e4["printed"])] != e4["printed"]:
        bad("entry %d: printed token not at its place" % n_)
    if shift:
        moved += 1
    inside = [eid for s, e, t, eid in sp if c4s <= s and e <= c4e]
    if e4["cell"] != e5["cell"]:
        cell_changed[(ln, e5["table"], e5["row"])] += 1
        if not inside:
            bad("entry %d: cell changed, but no edit lies inside it" % n_)
        if B[ln - 1][L5[n_][1]:L5[n_][2]] != e5["cell"]:
            bad("entry %d: v5 cell is not the v5 line's text of that cell" % n_)
    elif inside:
        bad("entry %d: an edit lies inside its cell, but the cell did not change" % n_)
if dict(on_changed) != ON_CHANGED or cell_changed or dict(cells_on_changed) != {KEPT_CELL: sum(ON_CHANGED.values())}:
    bad("entries on changed lines %r (CHANGES_v5.md: %r, keeping their cell %r); their cells %r; cells changed %r" % (
        dict(on_changed), ON_CHANGED, KEPT_CELL, dict(cells_on_changed), dict(cell_changed)))
print("entries with every key but `cell` equal: %d of %d" % (sum(1 for e4, e5 in zip(E4, E5)
                                                                 if all(e4[k] == e5[k] for k in KEYS if k != "cell")),
                                                             len(E5)))
print("entries with every key equal, `cell` included: %d of %d" % (sum(1 for e4, e5 in zip(E4, E5) if e4 == e5),
                                                                   len(E5)))
print("entries whose `cell` changed: %d (%s)" % (sum(cell_changed.values()), ", ".join(
    "line %d, Table %s, row %s: %d" % (k[0], k[1], k[2], v) for k, v in sorted(cell_changed.items())) or "none"))
print("entries on edited lines: %s (CHANGES_v5.md: %s), their cell %s (CHANGES_v5.md: %r); their printed token at the "
      "v4 place, shifted by the edits before it on %d" % (dict(sorted(on_changed.items())),
                                                          dict(sorted(ON_CHANGED.items())), dict(cells_on_changed),
                                                          KEPT_CELL, moved))
print("printed tokens equal entry by entry (v4 = v5): %s" % all(e4["printed"] == e5["printed"] for e4, e5 in zip(E4, E5)))
print("cells.json byte-identical to version 4: %s" % (raw["cells.json"] == raw["cells_v4.json"]))
print("changed_lines as JSON:")
print(json.dumps(changed_report, ensure_ascii=False))
print("FAILURES: %d" % len(fails))
for f_ in fails:
    print("  " + f_)
