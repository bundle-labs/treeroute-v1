# -*- coding: utf-8 -*-
# Builder A: version 2 of the outputs against version 1, by script (prints only; writes nothing).
# Reads OUT\A\tables_v1.md and OUT\A\cells_v1.json (byte copies of version 1), OUT\A\tables.md and OUT\A\cells.json
# (version 2), and the OLD/NEW printed texts of OUT\spec\CHANGES_v2.md.
# 1. Line alignment of tables.md (difflib, no junk heuristic): every changed, dropped and added line, v1 line -> v2
#    line, with the changed part (common prefix and suffix trimmed to word boundaries); the map of the other lines.
# 2. Expected version 2: version 1 with the order's OLD texts replaced by its NEW texts (as quoted in CHANGES_v2.md),
#    the CRW Outlook row dropped and the two inserted texts inserted; it must equal tables.md byte for byte.
# 3. Number tokens (digit runs with internal , or ., and superscript runs) of every aligned line pair: equal on the
#    unchanged lines; on the changed lines only inside the changed part; every cells.json token of a changed line
#    lies outside the changed part, at the same place.
# 4. cells.json: the v1 and v2 entries paired by position; every key equal except `line` (the v1 line mapped through
#    the alignment), `part` (G1) and `cell` (only on a changed line, and then the v2 line's text of that cell).
# Version 3 round (2026-11-17): version 2 of the outputs is now kept as OUT\A\tables_v2.md and OUT\A\cells_v2.json
# (byte copies; tables.md and cells.json hold version 3), so this script reads those two names; nothing else changed.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import json
import hashlib
import difflib
import itertools
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_X = os.path.dirname(HERE)
OUT = os.path.dirname(OUT_X)
fails = []


def bad(msg):
    fails.append(msg)


raw = {}
for n, fn in (("tables_v1.md", "tables_v1.md"), ("tables.md", "tables_v2.md"), ("cells_v1.json", "cells_v1.json"),
              ("cells.json", "cells_v2.json")):
    with open(os.path.join(OUT_X, fn), "rb") as f:
        raw[n] = f.read()
    print("%s  %9d bytes  %s" % (hashlib.sha256(raw[n]).hexdigest(), len(raw[n]), fn))
for n in ("tables_v1.md", "tables.md"):
    if not raw[n].endswith(b"\n") or b"\r" in raw[n]:
        bad(n + ": line ends")
A = raw["tables_v1.md"].decode("utf-8").split("\n")[:-1]
B = raw["tables.md"].decode("utf-8").split("\n")[:-1]
print("lines: v1 %d, v2 %d" % (len(A), len(B)))

# ------------------------------------------------------------------ 1. alignment


def trim(a, b):
    """Common prefix and suffix of a and b, cut back to word boundaries: (p, s) with a[:p] == b[:p] and the last s
    characters equal."""
    n = min(len(a), len(b))
    p = 0
    while p < n and a[p] == b[p]:
        p += 1
    s = 0
    while s < n - p and a[-1 - s] == b[-1 - s]:
        s += 1

    def in_word_p(p):
        return p > 0 and a[p - 1].isalnum() and ((p < len(a) and a[p].isalnum()) or (p < len(b) and b[p].isalnum()))

    def in_word_s(s):
        if s == 0:
            return False
        ka, kb = len(a) - s, len(b) - s
        return a[ka].isalnum() and ((ka > 0 and a[ka - 1].isalnum()) or (kb > 0 and b[kb - 1].isalnum()))

    while in_word_p(p):
        p -= 1
    while in_word_s(s):
        s -= 1
    return p, s


def sim(x, y):
    return difflib.SequenceMatcher(None, x, y, autojunk=False).ratio()


lmap = {}       # v1 line -> v2 line, for every line kept (changed or not)
pairs = []      # (v1 line, v2 line) of changed lines
dropped, added = [], []
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1):
            lmap[i1 + k + 1] = j1 + k + 1
        continue
    olds, news = list(range(i1 + 1, i2 + 1)), list(range(j1 + 1, j2 + 1))
    if tag == "replace" and len(olds) == len(news):
        match = list(zip(olds, news))
    else:  # order-preserving pairing of the most similar lines (blocks here are at most 2 lines)
        best = None
        if olds and news:
            k = min(len(olds), len(news))
            for oi in itertools.combinations(olds, k):
                for nj in itertools.combinations(news, k):
                    sc = sum(sim(A[x - 1], B[y - 1]) for x, y in zip(oi, nj))
                    if best is None or sc > best[0]:
                        best = (sc, list(zip(oi, nj)))
        match = best[1] if best else []
    for x, y in match:
        lmap[x] = y
        pairs.append((x, y))
    dropped += [x for x in olds if x not in lmap]
    added += [y for y in news if y not in [m[1] for m in match]]
moved = sorted((x, y) for x, y in lmap.items() if x != y)
print("alignment: %d lines kept, %d changed, %d dropped, %d added; kept lines whose number differs: %s"
      % (len(lmap), len(pairs), len(dropped), len(added), ", ".join("v1 %d -> v2 %d" % m for m in moved) or "none"))
pos_diff = [i + 1 for i in range(min(len(A), len(B))) if A[i] != B[i]]
print("by position (same line number in v1 and v2): %d lines differ: %s" % (len(pos_diff), ", ".join(map(str, pos_diff))))
if pos_diff != [1, 5, 65, 66, 67, 121, 122, 144, 146, 155, 171, 174, 251, 256, 342, 344, 348, 451, 457, 543, 548, 661,
                711, 784]:
    bad("the lines that differ by position are not CHANGES_v2.md's list")

TOK = re.compile(r"\d+(?:[.,]\d+)*|[⁰¹²³⁴-⁹⁻]+")
changed_lines = []
tok_added, tok_removed = Counter(), Counter()
mid_span = {}  # v2 line -> (p, s, len v1 line, len v2 line)
for x, y in sorted(pairs):
    a, b = A[x - 1], B[y - 1]
    p, s = trim(a, b)
    mo, mn = a[p:len(a) - s], b[p:len(b) - s]
    mid_span[y] = (p, s, len(a), len(b))
    ta, tb = Counter(TOK.findall(mo)), Counter(TOK.findall(mn))
    tok_added += tb - ta
    tok_removed += ta - tb
    if Counter(TOK.findall(a[:p])) != Counter(TOK.findall(b[:p])) or a[len(a) - s:] != b[len(b) - s:]:
        bad("line %d: prefix or suffix differs" % y)
    dd = []
    if tb - ta:
        dd.append("tokens added " + ", ".join("%s x%d" % kv for kv in sorted((tb - ta).items())))
    if ta - tb:
        dd.append("tokens removed " + ", ".join("%s x%d" % kv for kv in sorted((ta - tb).items())))
    changed_lines.append("v1 %d -> v2 %d: \"%s\" -> \"%s\"%s" % (x, y, mo, mn, (" (" + "; ".join(dd) + ")") if dd else ""))
for x in dropped:
    t = Counter(TOK.findall(A[x - 1]))
    tok_removed += t
    changed_lines.append("v1 %d -> dropped: \"%s\" (tokens removed %s)" % (
        x, A[x - 1], ", ".join("%s x%d" % kv for kv in sorted(t.items())) or "none"))
for x, y in moved:
    if (x, y) not in pairs:
        changed_lines.append("v1 %d -> v2 %d: unchanged text %s, line number shifted" % (
            x, y, "(blank line)" if A[x - 1] == "" else "\"%s\"" % A[x - 1]))
for y in added:
    t = Counter(TOK.findall(B[y - 1]))
    tok_added += t
    changed_lines.append("added -> v2 %d: \"%s\" (tokens added %s)" % (
        y, B[y - 1], ", ".join("%s x%d" % kv for kv in sorted(t.items())) or "none"))
changed_lines.sort(key=lambda t: int(re.search(r"v[12] (\d+)", t).group(1)))
print("changed lines (v1 line -> v2 line: OLD part -> NEW part):")
for t in changed_lines:
    print("  " + t)
# whole-file token totals: the difference is exactly the tokens of the changed parts
ca = Counter(t for line in A for t in TOK.findall(line))
cb = Counter(t for line in B for t in TOK.findall(line))
if (cb - ca) != (tok_added - tok_removed):
    bad("file token difference (added) does not match the changed parts")
if (ca - cb) != (tok_removed - tok_added):
    bad("file token difference (removed) does not match the changed parts")
print("number tokens in the file: v1 %d, v2 %d; added %s; removed %s" % (
    sum(ca.values()), sum(cb.values()), dict(sorted((cb - ca).items())), dict(sorted((ca - cb).items()))))
for x in range(1, len(A) + 1):
    if x in lmap and (x, lmap[x]) not in pairs and A[x - 1] != B[lmap[x] - 1]:
        bad("v1 line %d mapped to a different text" % x)

# ------------------------------------------------------------------ 2. expected version 2 from the order's texts
with open(os.path.join(OUT, "spec", "CHANGES_v2.md"), "r", encoding="utf-8") as f:
    CH = f.read().split("\n")
sec, items, i = None, [], 0
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
        while CH[k].strip() == "":
            k -= 1
        if "printed text" in CH[k]:
            kind = "OLD" if "OLD printed text" in CH[k] else ("NEW" if "NEW printed text" in CH[k] else None)
            if kind is None or len(body) != 1:
                bad("CHANGES_v2.md block at line %d: %r" % (i + 1, CH[k]))
            items.append((sec, kind, body[0]))
        i = j + 1
        continue
    i += 1
seq = {}
for s_, kind, text in items:
    seq.setdefault(s_, []).append((kind, text))
want = {"C1": "ONONNON", "C2": "ONON", "C3": "ONON", "C4": "OONNON", "C5": "ON", "C6": "ONON", "C7": "ON", "C8": "ON",
        "C9": "N"}
got = {s_: "".join(k[0] for k, t in v) for s_, v in seq.items()}
if got != want:
    bad("CHANGES_v2.md printed-text blocks: %r" % got)
T = list(A)


def sub(old, new, count, what, only=None):
    hits = [n for n, line in enumerate(T) if old in line and (only is None or only(line))]
    if sum(T[n].count(old) for n in hits) != count:
        bad("%s: OLD found %d times, expected %d" % (what, sum(T[n].count(old) for n in hits), count))
    for n in hits:
        T[n] = T[n].replace(old, new)


c1, c2, c3, c4 = seq["C1"], seq["C2"], seq["C3"], seq["C4"]
sub(c1[0][1], c1[1][1], 1, "C1 Table 9")
sub(c1[2][1], c1[4][1], 2, "C1 S3.25/S3.27", lambda L: L.startswith("**Table S3.25 ") or L.startswith("**Table S3.27 "))
sub(c1[2][1], c1[3][1], 3, "C1 S3.23/S3.24/S3.26")
sub(c1[5][1], c1[6][1], 1, "C1 S3.29")
sub(c2[0][1], c2[1][1], 1, "C2 note a")
sub(c2[2][1], c2[3][1], 1, "C2 note b")
sub(c3[0][1], c3[1][1], 1, "C3 first sentence")
sub(c3[2][1], c3[3][1], 1, "C3 second sentence")
drop = [n for n, line in enumerate(T) if line == c4[0][1]]
if len(drop) != 1:
    bad("C4 dropped row found %d times" % len(drop))
else:
    del T[drop[0]]
sub(c4[1][1], c4[2][1], 1, "C4 baselines row")
anchor = [n for n, line in enumerate(T) if line.startswith("ᵃ Failed")]
if len(anchor) != 1:
    bad("C4 insertion anchor found %d times" % len(anchor))
else:
    T.insert(anchor[0], c4[3][1])
sub(c4[4][1], c4[5][1], 1, "C4 S3.30 note")
sub("| " + seq["C5"][0][1] + " |", "| " + seq["C5"][1][1] + " |", 1, "C5 row label")
c6 = seq["C6"]
sub("| " + c6[0][1] + " |", "| " + c6[1][1] + " |", 1, "C6 E10")
sub(c6[2][1], c6[3][1], 1, "C6 note a")
sub(seq["C7"][0][1], seq["C7"][1][1], 5, "C7 sign note")
sub(seq["C8"][0][1], seq["C8"][1][1], 1, "C8 note d")
sub("the nowcast of each problem. Built", "the nowcast of each problem. " + seq["C9"][0][1] + " Built", 1, "C9 header",
    lambda L: L.startswith("<!-- "))
exp = ("\n".join(T) + "\n").encode("utf-8")
same = exp == raw["tables.md"]
print("expected v2 (v1 + the order's %d OLD/NEW texts of CHANGES_v2.md): %d bytes, sha256 %s; equal to tables.md: %s"
      % (len(items), len(exp), hashlib.sha256(exp).hexdigest(), same))
if not same:
    bad("tables.md is not v1 + the order's texts")
    for d in difflib.unified_diff(T, B, "expected", "tables.md", n=0, lineterm=""):
        print("    " + d[:300])

# ------------------------------------------------------------------ 3 and 4. cells.json
D1 = json.loads(raw["cells_v1.json"].decode("utf-8"))
D2 = json.loads(raw["cells.json"].decode("utf-8"))
for k in ("tables_file", "spec"):
    if D1[k] != D2[k]:
        bad("cells.json %s differs" % k)
if list(D1.keys()) != list(D2.keys()):
    bad("cells.json top keys differ")
E1, E2 = D1["entries"], D2["entries"]
print("entries: v1 %d, v2 %d" % (len(E1), len(E2)))
if len(E1) != len(E2):
    bad("entry counts differ")
KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "cell", "source", "selector", "stored"]
SAME = ["table", "panel", "row", "column", "printed", "source", "selector", "stored"]
kinds = Counter()
cell_lines = Counter()
for n, (e1, e2) in enumerate(zip(E1, E2)):
    if list(e1.keys()) != KEYS or list(e2.keys()) != KEYS:
        bad("entry %d: keys" % n)
        continue
    for k in SAME:
        if e1[k] != e2[k]:
            bad("entry %d: %s %r -> %r" % (n, k, e1[k], e2[k]))
    if lmap.get(e1["line"]) != e2["line"]:
        bad("entry %d: line %d -> %d, alignment says %r" % (n, e1["line"], e2["line"], lmap.get(e1["line"])))
    if e1["line"] != e2["line"]:
        kinds["line"] += 1
    if e1["part"] != e2["part"]:
        kinds["part"] += 1
    if e1["cell"] != e2["cell"]:
        kinds["cell"] += 1
        cell_lines[(e2["line"], e2["table"])] += 1
        if (e1["line"], e2["line"]) not in pairs:
            bad("entry %d: cell changed on a line that did not change" % n)


def offsets(lines, entries):
    """Absolute offset of every entry's printed token in its line, in reading order (as verify_outputs.py finds it)."""
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
                    found = (ci, q + len(e["printed"]), starts[ci] + q)
                    break
        if found is None:
            out.append(None)
            prev = (e["line"], 0, 0)
        else:
            out.append(found[2])
            prev = (e["line"], found[0], found[1])
    return out


O1, O2 = offsets(A, E1), offsets(B, E2)
if None in O1 or None in O2:
    bad("an entry is not found in reading order (v1 %d, v2 %d)" % (O1.count(None), O2.count(None)))
on_changed = 0
for n, (e1, e2) in enumerate(zip(E1, E2)):
    o1, o2 = O1[n], O2[n]
    if o1 is None or o2 is None:
        continue
    if e2["line"] in mid_span and (e1["line"], e2["line"]) in pairs:
        on_changed += 1
        p, s, la, lb = mid_span[e2["line"]]
        L_ = len(e1["printed"])
        if o1 + L_ <= p:
            ok = (o2 == o1)
        elif o1 >= la - s:
            ok = (o2 == o1 + lb - la)
        else:
            ok = False
        if not ok:
            bad("entry %d: printed token inside the changed part or moved (v1 %d, v2 %d)" % (n, o1, o2))
    elif o1 != o2:
        bad("entry %d: printed token moved on an unchanged line" % n)
print("entries whose line changed: %d; whose part changed: %d; whose cell changed: %d (%s)" % (
    kinds["line"], kinds["part"], kinds["cell"],
    ", ".join("line %d, Table %s: %d" % (k[0], k[1], v) for k, v in sorted(cell_lines.items())) or "none"))
print("entries on changed lines: %d, every printed token outside the changed part and at the same place" % on_changed)
pf = Counter(e["table"] for e in E2 if e["panel"] == "f")
pf_parts = Counter(e["part"] for e in E2 if e["panel"] == "f" and e["table"] in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27"))
print("panel f entries: %s; parts %s (v1 parts %s)" % (dict(sorted(pf.items())), dict(pf_parts),
                                                      dict(Counter(e["part"] for e in E1 if e["panel"] == "f"))))
print("printed tokens per table, v1 = v2: %s" % (Counter(e["table"] for e in E1) == Counter(e["table"] for e in E2)))
print("(table, panel, row, column, part, printed, stored) multiset equal: %s" % (
    Counter(json.dumps([e[k] for k in ("table", "panel", "row", "column", "part", "printed", "stored")]) for e in E1)
    == Counter(json.dumps([e[k] for k in ("table", "panel", "row", "column", "part", "printed", "stored")]) for e in E2)))
print("changed_lines as JSON:")
print(json.dumps(changed_lines, ensure_ascii=False))
print("FAILURES: %d" % len(fails))
for f_ in fails:
    print("  " + f_)
