# -*- coding: utf-8 -*-
# Builder A: version 3 of the outputs against version 2, by script (prints only; writes nothing).
# Reads OUT\A\tables_v2.md and OUT\A\cells_v2.json (byte copies of version 2), OUT\A\tables.md and OUT\A\cells.json
# (version 3), the order's OLD and NEW printed texts as OUT\spec\CHANGES_v3.md quotes them (27 OLD, 28 NEW), the
# lines CHANGES_v3.md expects to change, and M and P of the Link cell rule of OUT\spec\TABLE_SPEC.md (4.7).
# 1. Lines: the same count in v2 and v3 (no line added or dropped, so v2 line n = v3 line n); every line that differs.
# 2. Expected version 3: version 2 with each order text applied where the order names it (each edit's count of
#    places is fixed below and must be found exactly), the new Table 9 sentence inserted after its anchor, and M -> P
#    in the Link cells; it must equal tables.md byte for byte, and the lines it changes must be CHANGES_v3.md's list.
# 3. Number tokens (digit runs with internal , or ., and runs of superscript digits): on every line the tokens outside
#    the edited spans are the same tokens at the same places; every added or removed token lies inside an edited span
#    (an order text) and none straddles a span's edge; the file's token difference is the sum over the edits.
# 4. cells.json: the v2 and v3 entries paired by position; every key equal except `cell`, which may differ only where
#    an edited span lies inside that cell, and then is the v3 text of that cell; every printed token found at its v2
#    place, shifted only by the edits before it on its line.
# Version 4 round (2026-11-17): version 3 of the outputs is now kept as OUT\A\tables_v3.md and OUT\A\cells_v3.json
# (byte copies; tables.md and cells.json hold version 4), so this script reads those two names; nothing else changed.
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
for n, fn in (("tables_v2.md", "tables_v2.md"), ("tables.md", "tables_v3.md"), ("cells_v2.json", "cells_v2.json"),
              ("cells.json", "cells_v3.json")):
    with open(os.path.join(OUT_X, fn), "rb") as f:
        raw[n] = f.read()
    print("%s  %9d bytes  %s" % (hashlib.sha256(raw[n]).hexdigest(), len(raw[n]), fn))
for n in ("tables_v2.md", "tables.md"):
    if not raw[n].endswith(b"\n") or b"\r" in raw[n] or raw[n].startswith(b"\xef\xbb\xbf"):
        bad(n + ": line ends or BOM")
A = raw["tables_v2.md"].decode("utf-8").split("\n")[:-1]
B = raw["tables.md"].decode("utf-8").split("\n")[:-1]

# ------------------------------------------------------------------ the order's texts (CHANGES_v3.md) and the spec's M, P
with open(os.path.join(OUT, "spec", "CHANGES_v3.md"), "r", encoding="utf-8") as f:
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
            kind = "O" if "OLD printed text" in label else ("N" if "NEW printed text" in label else "?")
            if kind == "?" or len(body) != 1:
                bad("CHANGES_v3.md block at line %d: %r" % (i + 1, label))
            items.append((sec, kind, body[0], label))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text, label in items:
    seq.setdefault(s_, []).append((kind, text, label))
got = {s_: "".join(k for k, t, lab in v) for s_, v in seq.items()}
if got != {"V3-1": "NONONONONONON", "V3-2": "ONONONONON", "V3-3": "ONON", "V3-4": "ON", "V3-5": "ON",
           "V3-6": "ONONONONONONONONONON", "V3-7": "ONON"}:
    bad("CHANGES_v3.md printed-text blocks: %r" % got)
n_old = sum(k == "O" for s_, k, t, lab in items)
n_new = sum(k == "N" for s_, k, t, lab in items)


def prs(s_, skip=0):
    v = seq[s_][skip:]
    return [(v[q][1], v[q + 1][1]) for q in range(0, len(v) - 1, 2)]


INS = seq["V3-1"][0][1]
mo = re.search(r"directly after `([^`]+)`", seq["V3-1"][0][2])
ANCHOR = mo.group(1) if mo else None
V31, V32, V33, V34, V35, V36, V37 = (prs("V3-1", 1), prs("V3-2"), prs("V3-3"), prs("V3-4"), prs("V3-5"), prs("V3-6"),
                                     prs("V3-7"))
flat_ch = " ".join(x.strip() for x in CH)
mo = re.search(r"tables\.md keeps its (\d+) lines", flat_ch)
N_LINES = int(mo.group(1)) if mo else None
mo = re.search(r"The lines that change \(1-based, (\d+)\): ([0-9, ]+)\.", flat_ch)
EXPECTED_CHANGED = [int(x) for x in mo.group(2).split(", ")] if mo else []
if not mo or int(mo.group(1)) != len(EXPECTED_CHANGED):
    bad("CHANGES_v3.md: list of changed lines not found")
with open(os.path.join(OUT, "spec", "TABLE_SPEC.md"), "r", encoding="utf-8") as f:
    rule = [x for x in f.read().split("\n") if x.startswith("| Link | - | from the pair's `pair_label` ")]
M = re.findall(r'\bM = "([^"]*)"', rule[0]) if len(rule) == 1 else []
P = re.findall(r'\bP = "([^"]*)"', rule[0]) if len(rule) == 1 else []
if len(M) != 1 or len(P) != 1:
    bad("spec 4.7: M and P not found once")
M, P = (M[0], P[0]) if len(M) == 1 and len(P) == 1 else ("\0", "\0")
if V36[9][0].replace(M, P) != V36[9][1]:
    bad("CHANGES_v3.md's Link example is not M -> P")
print("order texts (CHANGES_v3.md): %d OLD, %d NEW; insertion anchor found: %s; spec 4.7: M %r, P %r"
      % (n_old, n_new, ANCHOR is not None, M, P))

# ------------------------------------------------------------------ 1. lines
print("lines: v2 %d, v3 %d (CHANGES_v3.md: %s)" % (len(A), len(B), N_LINES))
if not (len(A) == len(B) == N_LINES):
    bad("line counts differ")
diff_lines = [n + 1 for n in range(min(len(A), len(B))) if A[n] != B[n]]

# ------------------------------------------------------------------ 2. expected version 3
# (id, OLD, NEW, places, match): match "sub" = anywhere in a line; "cell" = a whole table cell; "line" = a whole line;
# "ins" = NEW + " " inserted right after OLD + " " (the anchor stays)
EDITS = [
    ("V3-1 Table 9: new importance sentence", ANCHOR, INS, 1, "ins"),
    ("V3-1 Table 9: RBO consensus", V31[0][0], V31[0][1], 1, "sub"),
    ("V3-1 Table 9: own-history share", V31[1][0], V31[1][1], 1, "sub"),
    ("V3-1 S3.19 caption: J", V31[2][0], V31[2][1], 1, "sub"),
    ("V3-1 {shares_sentence} (d, e)", V31[3][0], V31[3][1], 3, "sub"),
    ("V3-1 {shares_sentence} (d, e, g)", V31[4][0], V31[4][1], 2, "sub"),
    ("V3-1 S3.29 caption", V31[5][0], V31[5][1], 1, "sub"),
    ("V3-2 S3.18 caption", V32[0][0], V32[0][1], 1, "sub"),
    ("V3-2 S3.18 source comment", V32[1][0], V32[1][1], 1, "sub"),
    ("V3-2 S3.18 panel b label", V32[2][0], V32[2][1], 1, "line"),
    ("V3-2 S3.18 b baselines row", V32[3][0], V32[3][1], 1, "line"),
    ("V3-2 S3.18 first note line", V32[4][0], V32[4][1], 1, "line"),
    ("V3-3 count clause", V33[0][0], V33[0][1], 5, "sub"),
    ("V3-3 {extra_src}", V33[1][0], V33[1][1], 1, "sub"),
    ("V3-4 NDVI note", V34[0][0], V34[0][1], 1, "sub"),
    ("V3-5 S3.22 row label", V35[0][0], V35[0][1], 1, "cell"),
    ("V3-6 treeroute skill-guard cell", V36[0][0], V36[0][1], 10, "cell"),
    ("V3-6 S3.21 first row label", V36[1][0], V36[1][1], 1, "cell"),
    ("V3-6 random forest's method", V36[2][0], V36[2][1], 5, "sub"),
    ("V3-6 S3.19 note c", V36[3][0], V36[3][1], 1, "sub"),
    ("V3-6 S3.21 E10", V36[4][0], V36[4][1], 1, "sub"),
    ("V3-6 S3.21 E3a", V36[5][0], V36[5][1], 1, "cell"),
    ("V3-6 S3.21 E3m", V36[6][0], V36[6][1], 1, "cell"),
    ("V3-6 S3.21 E3", V36[7][0], V36[7][1], 1, "cell"),
    ("V3-6 S3.21 E6", V36[8][0], V36[8][1], 1, "cell"),
    ("V3-6 S3.25 Link cells (M -> P)", M, P, 8, "sub"),
    ("V3-7 header comment: version sentences", V37[0][0], V37[0][1], 1, "sub"),
    ("V3-7 header comment: data numbers", V37[1][0], V37[1][1], 1, "sub"),
]
if len(EDITS) != 28:
    bad("edit list")
spans = {}  # v2 line -> [(start, end, NEW, id)]
for eid, old, newt, places, how in EDITS:
    if old is None or old == "":
        bad("%s: no OLD text" % eid)
        continue
    found = []
    for n, a in enumerate(A, 1):
        if how == "line":
            if a == old:
                found.append((n, 0, len(a), newt))
            continue
        pat = {"sub": old, "cell": "| " + old + " |", "ins": old + " "}[how]
        pos = a.find(pat)
        while pos >= 0:
            if how == "sub":
                found.append((n, pos, pos + len(old), newt))
            elif how == "cell":
                found.append((n, pos + 2, pos + 2 + len(old), newt))
            else:
                q = pos + len(old) + 1
                found.append((n, q, q, newt + " "))
            pos = a.find(pat, pos + 1)
    if len(found) != places:
        bad("%s: found at %d places, the order names %d" % (eid, len(found), places))
    for n, s, e, t in found:
        spans.setdefault(n, []).append((s, e, t, eid))
if sum(a.count("| " + V36[9][0] + " |") for a in A) != 4:
    bad("the order's Link example (a cross-link Ridge pair) is not found as 4 cells of version 2")
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
print("expected v3 (v2 + %d edits at %d places on %d lines): sha256 %s; equal to tables.md: %s"
      % (len(EDITS), sum(len(v) for v in spans.values()), len(spans), hashlib.sha256(exp).hexdigest(), same))
if not same:
    bad("tables.md is not v2 + the order's texts")
    for n in range(min(len(T), len(B))):
        if T[n] != B[n]:
            print("    line %d differs: expected %r / got %r" % (n + 1, T[n][:160], B[n][:160]))
print("lines that differ, v2 vs v3 (same line number): %d: %s" % (len(diff_lines), ", ".join(map(str, diff_lines))))
if diff_lines != sorted(spans) or diff_lines != EXPECTED_CHANGED:
    bad("the changed lines are not the edited lines or not CHANGES_v3.md's list")
print("equal to CHANGES_v3.md's list of %d lines: %s" % (len(EXPECTED_CHANGED), diff_lines == EXPECTED_CHANGED))

# ------------------------------------------------------------------ 3. number tokens
TOK = re.compile(r"\d+(?:[.,]\d+)*|[⁰¹²³⁴-⁹⁻]+")


def regions(n, which):
    """(start, end, kind) of the line's segments and edit spans, in order; which = 'a' (v2) or 'b' (v3)."""
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
changed_report = []
cur_table, cur_panel, prev_line = None, "", ""
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
    elif b.startswith("| "):
        c = b[2:-2].split(" | ")
        first = c[0] + ((" / " + c[1]) if (cur_table, cur_panel) in (("S3.18", "a"), ("S3.20", "")) else "")
        where_of[n] = "Table %s%s row %s" % (cur_table, (" " + cur_panel) if cur_panel else "", first)
    else:
        where_of[n] = "Table %s note" % cur_table
for n in range(1, len(A) + 1):
    if n > len(B):
        break
    ra, rb = regions(n, "a"), regions(n, "b")
    sa, xa = classify(A[n - 1], ra, "v2 line %d" % n)
    sb, xb = classify(B[n - 1], rb, "v3 line %d" % n)
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
print("number tokens in the file: v2 %d, v3 %d; added (all inside order texts) %s; removed %s" % (
    sum(ca.values()), sum(cb.values()), dict(sorted(added_all.items())), dict(sorted(removed_all.items())) or "none"))
print("changed lines (v2 line = v3 line; edit: OLD -> NEW):")
for t in changed_report:
    print("  " + t)

# ------------------------------------------------------------------ 4. cells.json
D2 = json.loads(raw["cells_v2.json"].decode("utf-8"))
D3 = json.loads(raw["cells.json"].decode("utf-8"))
if list(D2.keys()) != list(D3.keys()) or D2["tables_file"] != D3["tables_file"] or D2["spec"] != D3["spec"]:
    bad("cells.json top keys, tables_file or spec differ")
if json.dumps(D3, ensure_ascii=False, indent=1, allow_nan=False) + "\n" != raw["cells.json"].decode("utf-8"):
    bad("cells.json v3 is not the canonical dump")
E2, E3 = D2["entries"], D3["entries"]
print("entries: v2 %d, v3 %d; tables_file %r, spec %r" % (len(E2), len(E3), D3["tables_file"], D3["spec"]))
if len(E2) != len(E3):
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


L2, L3 = locate(A, E2), locate(B, E3)
if None in L2 or None in L3:
    bad("an entry is not found in reading order (v2 %d, v3 %d)" % (L2.count(None), L3.count(None)))
cell_changed = Counter()
moved = 0
for n_, (e2, e3) in enumerate(zip(E2, E3)):
    if list(e2.keys()) != KEYS or list(e3.keys()) != KEYS:
        bad("entry %d: keys" % n_)
        continue
    for k in KEYS:
        if k != "cell" and e2[k] != e3[k]:
            bad("entry %d: %s %r -> %r" % (n_, k, e2[k], e3[k]))
    if L2[n_] is None or L3[n_] is None:
        continue
    o2, c2s, c2e = L2[n_]
    o3 = L3[n_][0]
    ln = e2["line"]
    sp = spans.get(ln, [])
    shift = 0
    for s, e, t, eid in sp:
        if e <= o2:
            shift += len(t) - (e - s)
        elif s < o2 + len(e2["printed"]) and o2 < e:
            bad("entry %d: printed token inside the edit %s" % (n_, eid))
    if o3 != o2 + shift:
        bad("entry %d: printed token at %d in v3, expected %d" % (n_, o3, o2 + shift))
    if shift:
        moved += 1
    inside = [eid for s, e, t, eid in sp if c2s <= s and e <= c2e]
    if e2["cell"] != e3["cell"]:
        cell_changed[(ln, e3["table"], e3["row"])] += 1
        if not inside:
            bad("entry %d: cell changed, but no edit lies inside it" % n_)
        if L3[n_] is not None and B[ln - 1][L3[n_][1]:L3[n_][2]] != e3["cell"]:
            bad("entry %d: v3 cell is not the v3 line's text of that cell" % n_)
    elif inside:
        bad("entry %d: an edit lies inside its cell, but the cell did not change" % n_)
print("entries with every key but `cell` equal: %d of %d" % (sum(1 for e2, e3 in zip(E2, E3)
                                                                 if all(e2[k] == e3[k] for k in KEYS if k != "cell")),
                                                             len(E3)))
print("entries whose `cell` changed: %d (%s)" % (sum(cell_changed.values()), ", ".join(
    "line %d, Table %s, row %s: %d" % (k[0], k[1], k[2], v) for k, v in sorted(cell_changed.items())) or "none"))
print("entries on edited lines: %d; their printed token at the v2 place, shifted by the edits before it on %d"
      % (sum(1 for e in E2 if e["line"] in spans), moved))
print("printed tokens equal entry by entry (v2 = v3): %s" % all(e2["printed"] == e3["printed"] for e2, e3 in zip(E2, E3)))
print("changed_lines as JSON:")
print(json.dumps(changed_report, ensure_ascii=False))
print("FAILURES: %d" % len(fails))
for f_ in fails:
    print("  " + f_)
