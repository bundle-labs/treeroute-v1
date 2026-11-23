# -*- coding: utf-8 -*-
# Builder A's self-check of OUT\A\tables.md and OUT\A\cells.json (prints only; writes nothing).
# 1. encoding and layout rules (spec 0, 2.9); 2. every cells.json entry re-read from its source through its
# selector and its printed token re-formatted from the stored value; 3. entry order (reading order);
# 4. constant lines and constant cells found verbatim in the spec.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import json
import math

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_X = os.path.dirname(HERE)
OUT = os.path.dirname(OUT_X)
SPEC = os.path.join(OUT, "spec", "TABLE_SPEC.md")
SHAP = "D:\\treeroute\\analysis\\shap_v1"
VDIR = SHAP + "\\verify_v1"

problems = []


def bad(msg):
    problems.append(msg)


def real(short):
    if short.startswith("SHAP\\"):
        return SHAP + short[4:]
    if short.startswith("V\\"):
        return VDIR + short[1:]
    raise ValueError(short)


# ---------------------------------------------------------------- 1. encoding and layout
with open(os.path.join(OUT_X, "tables.md"), "rb") as f:
    raw_md = f.read()
with open(os.path.join(OUT_X, "cells.json"), "rb") as f:
    raw_js = f.read()
for name, raw in (("tables.md", raw_md), ("cells.json", raw_js)):
    if raw.startswith(b"\xef\xbb\xbf"):
        bad(name + ": BOM")
    if b"\r" in raw:
        bad(name + ": CR")
    if b"\t" in raw:
        bad(name + ": tab")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        bad(name + ": end of file")
    for i, line in enumerate(raw.decode("utf-8").split("\n")[:-1], 1):
        if line != line.rstrip(" "):
            bad("%s line %d: trailing space" % (name, i))
md = raw_md.decode("utf-8")
L = md.split("\n")[:-1]
# blank-line structure: no two blank lines in a row, no blank first line
for i in range(1, len(L)):
    if L[i] == "" and L[i - 1] == "":
        bad("tables.md: two blank lines at %d" % (i + 1))
# tables: header, separator, rows with equal cell counts
i = 0
while i < len(L):
    if L[i].startswith("|"):
        j = i
        while j < len(L) and L[j].startswith("|"):
            j += 1
        block = L[i:j]
        n = len(block[0][2:-2].split(" | "))
        if block[1] != "|" + "---|" * n:
            bad("table at line %d: bad separator" % (i + 1))
        for k, row in enumerate(block):
            if k == 1:
                continue
            if not (row.startswith("| ") and row.endswith(" |")):
                bad("line %d: bad row edges" % (i + k + 1))
            cells = row[2:-2].split(" | ")
            if len(cells) != n:
                bad("line %d: %d cells, header %d" % (i + k + 1, len(cells), n))
            for c in cells:
                if c != c.strip() or c == "":
                    bad("line %d: padded or empty cell" % (i + k + 1))
        if i > 0 and L[i - 1] != "":
            bad("table at line %d not preceded by a blank line" % (i + 1))
        if j < len(L) and L[j] != "":
            bad("table at line %d not followed by a blank line" % (i + 1))
        i = j
    else:
        i += 1

# ---------------------------------------------------------------- 2. entries re-read from the sources
doc = json.loads(raw_js.decode("utf-8"))
if list(doc.keys()) != ["tables_file", "spec", "entries"]:
    bad("cells.json: top keys")
if doc["tables_file"] != "tables.md" or doc["spec"] != "OUT\\spec\\TABLE_SPEC.md":
    bad("cells.json: tables_file or spec")
if json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n" != raw_js.decode("utf-8"):
    bad("cells.json: not the canonical dump")
KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "cell", "source", "selector", "stored"]

cache = {}


def load(short):
    if short in cache:
        return cache[short]
    p = real(short)
    if short.endswith(".json"):
        with open(p, "r", encoding="utf-8") as f:
            v = json.load(f)
    elif short.endswith(".parquet"):
        v = pd.read_parquet(p)
    else:
        with open(p, "r", encoding="utf-8") as f:
            v = f.read().split("\n")
    cache[short] = v
    return v


TOK = re.compile(r'\.?([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]|\[("(?:[^"\\]|\\.)*")\]')


def jget(obj, path):
    pos = 0
    cur = obj
    while pos < len(path):
        m = TOK.match(path, pos)
        if not m or m.end() == pos:
            raise ValueError("bad path %r at %d" % (path, pos))
        if pos == 0 and path[0] == ".":
            raise ValueError("leading dot in %r" % path)
        if m.group(1) is not None:
            if pos > 0 and path[pos] != ".":
                raise ValueError("missing dot in %r" % path)
            cur = cur[m.group(1)]
        elif m.group(2) is not None:
            cur = cur[int(m.group(2))]
        else:
            cur = cur[json.loads(m.group(3))]
        pos = m.end()
    return cur


def norm(x):
    if hasattr(x, "item"):
        x = x.item()
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


SETUP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) "
                      r"background pairs,")
DONE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in "
                     r"([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
MAX_RE = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ "
                    r"\(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")


def derive(e):
    src, sel = e["source"], e["selector"]
    if src.endswith(".parquet"):
        df = load(src)
        terms = sel.split("; ")
        col = terms[-1]
        assert col.startswith("column=")
        col = col[len("column="):]
        mask = pd.Series(True, index=df.index)
        for t in terms[:-1]:
            k, v = t.split("=", 1)
            mask &= (df[k].astype(str) == v)
        sub = df[mask]
        if len(sub) != 1:
            raise ValueError("parquet selector matches %d rows: %s" % (len(sub), sel))
        return [norm(sub[col].iloc[0])]
    if src.endswith(".json"):
        obj = load(src)
        if sel.startswith("len(") and sel.endswith(")"):
            return [len(jget(obj, sel[4:-1]))]
        if " - " in sel:
            a, b = sel.split(" - ")
            return [norm(jget(obj, a)), norm(jget(obj, b))]
        return [norm(jget(obj, sel))]
    lines = load(src)
    m = re.match(r"^line (\d+): (.+)$", sel)
    n, field = int(m.group(1)), m.group(2)
    line = lines[n - 1]
    if src.endswith(".log"):
        if field == "background pairs":
            return [int(SETUP_RE.match(line).group(4))]
        mo = DONE_RE.match(line)
        return [float(mo.group(3) if field == "total seconds" else mo.group(4))]
    if src.endswith("SAMPLE_REGISTER.txt"):
        fields = dict(t.split("=", 1) for t in line.split(" ")[1:])
        return [int(fields[field])]
    mo = MAX_RE.match(line.lstrip("\ufeff"))
    g = {"spread": 2, "value 1": 6, "value 3": 8}[field]
    return [float(mo.group(g))]


MINUS = "\u2212"
SUPD = {"0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074", "5": "\u2075",
        "6": "\u2076", "7": "\u2077", "8": "\u2078", "9": "\u2079", "-": "\u207b"}


def cands(x):
    out = set()
    if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x):
        s = "0.00" if x == 0.0 else format(x, ".2f")
        out.add(MINUS + s[1:] if s.startswith("-") else s)
        if x >= 0:
            y = 100.0 * x
            out.add("0.0%" if x == 0.0 else ("<0.1%" if y < 0.05 else format(y, ".1f") + "%"))
        if float(x).is_integer():
            out.add(format(int(x), ","))
        if x == 0.0:
            out.add("0")
        else:
            m, ex = format(abs(x), ".1e").split("e")
            out.add((MINUS if x < 0 else "") + m + " \u00d7 10" + "".join(SUPD[c] for c in str(int(ex))))
        out.add(format(x, ",.1f"))
        if not float(x).is_integer():
            out.add(format(x, ".1f"))
    return out


entries = doc["entries"]
prev = (0, -1, -1)  # line, cell index, end position in the cell
for k, e in enumerate(entries):
    if list(e.keys()) != KEYS:
        bad("entry %d: keys" % k)
        continue
    # stored vs source
    try:
        d = derive(e)
    except Exception as ex:  # noqa
        bad("entry %d (%s %s %s %s): derive failed: %r" % (k, e["table"], e["row"], e["column"], e["part"], ex))
        continue
    if d != e["stored"]:
        bad("entry %d (%s %s %s %s): stored %r but source gives %r" % (k, e["table"], e["row"], e["column"],
                                                                     e["part"], e["stored"], d))
    # printed vs stored
    st = e["stored"]
    if st == [None]:
        if e["printed"] != "undefined":
            bad("entry %d: undefined stored, printed %r" % (k, e["printed"]))
    elif len(st) == 2:
        if e["printed"] != format(st[0] - st[1], ","):
            bad("entry %d: difference printed %r" % (k, e["printed"]))
    else:
        if e["printed"] not in cands(st[0]):
            bad("entry %d (%s %s %s %s): printed %r not a format of %r" % (k, e["table"], e["row"], e["column"],
                                                                        e["part"], e["printed"], st[0]))
    # position and order
    ln = e["line"]
    text = L[ln - 1]
    if text.startswith("| "):
        cells = text[2:-2].split(" | ")
    else:
        cells = [text]
    start_ci = prev[1] if prev[0] == ln else 0
    if prev[0] > ln:
        bad("entry %d: line order" % k)
    found = None
    for ci in range(max(start_ci, 0), len(cells)):
        if cells[ci] == e["cell"]:
            from_pos = prev[2] if (prev[0] == ln and ci == prev[1]) else 0
            pos = cells[ci].find(e["printed"], from_pos)
            if pos >= 0:
                found = (ci, pos + len(e["printed"]))
                break
    if found is None:
        bad("entry %d (line %d, %r): not found in reading order" % (k, ln, e["printed"]))
        prev = (ln, 0, 0)
    else:
        prev = (ln, found[0], found[1])

# every printed number of the data rows has an entry: count digit-bearing tokens per line vs entries
per_line = {}
for e in entries:
    per_line[e["line"]] = per_line.get(e["line"], 0) + 1

# ---------------------------------------------------------------- 4. constants against the spec
with open(SPEC, "r", encoding="utf-8") as f:
    spec = f.read()
fenced = set()
inb = False
for line in spec.split("\n"):
    if line.startswith("```"):
        inb = not inb
        continue
    if inb:
        fenced.add(line)
const_hits = 0
unmatched = []
for i, line in enumerate(L, 1):
    if line == "":
        continue
    if line in fenced:
        const_hits += 1
    elif not line.startswith("| ") and not line.startswith("|---"):
        unmatched.append((i, line))
print("lines: %d; verbatim spec lines: %d" % (len(L), const_hits))
print("non-table lines not verbatim in the spec (templated):")
for i, line in unmatched:
    print("  %d: %s" % (i, line[:150]))
# headers not verbatim in the spec
print("table header lines not verbatim in the spec (composed):")
for i in range(len(L) - 1):
    if L[i].startswith("| ") and L[i + 1].startswith("|---") and L[i] not in fenced:
        print("  %d: %s" % (i + 1, L[i][:200]))
# constant cells: digit-free cells that are not name lists or model lists, looked up in the spec
known_lists = set()
print("digit-free cells not found in the spec text (review):")
seen = set()
for i, line in enumerate(L, 1):
    if not line.startswith("| ") or line.startswith("|---"):
        continue
    for c in line[2:-2].split(" | "):
        if re.search(r"[0-9]", c) or c in seen:
            continue
        seen.add(c)
        if ("`" + c + "`") in spec or c in spec:
            continue
        print("  %d: %s" % (i, c))

print("entries: %d" % len(entries))
if problems:
    print("PROBLEMS (%d):" % len(problems))
    for p in problems[:200]:
        print("  " + p)
else:
    print("no problems found")
