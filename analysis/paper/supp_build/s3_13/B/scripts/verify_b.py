# Verification only (builder B): re-reads OUT\B\tables.md and OUT\B\cells.json and checks them against the sources,
# independently of build_tables.py's data paths: every entry's selector is resolved again in its source file, its
# stored values compared, its printed token re-formatted; every number in a table row must belong to an entry; the
# layout rules of spec 0 and 2.9 hold. Writes nothing.
import sys, os, re, json, math, hashlib
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_B = os.path.dirname(HERE)
SHAP = "D:\\treeroute\\analysis\\shap_v1"
VDIR = SHAP + "\\verify_v1"

fails = []


def bad(msg):
    fails.append(msg)


with open(os.path.join(OUT_B, "tables.md"), "rb") as f:
    raw_md = f.read()
with open(os.path.join(OUT_B, "cells.json"), "rb") as f:
    raw_cj = f.read()
print("tables.md sha256", hashlib.sha256(raw_md).hexdigest(), "bytes", len(raw_md))
print("cells.json sha256", hashlib.sha256(raw_cj).hexdigest(), "bytes", len(raw_cj))

# ---- encoding and layout (spec 0, 2.9)
for name, raw in (("tables.md", raw_md), ("cells.json", raw_cj)):
    if raw.startswith(b"\xef\xbb\xbf"):
        bad(name + " has a BOM")
    if b"\r" in raw or b"\t" in raw:
        bad(name + " has CR or TAB")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        bad(name + " does not end with exactly one newline")
md = raw_md.decode("utf-8")
lines = md[:-1].split("\n")
for i, ln in enumerate(lines, 1):
    if ln != ln.rstrip(" "):
        bad("trailing space on line %d" % i)
    if ln == "" and (i == 1 or lines[i - 2] == ""):
        bad("double blank at line %d" % i)
doc = json.loads(raw_cj.decode("utf-8"))
cj_again = json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
if cj_again.encode("utf-8") != raw_cj:
    bad("cells.json is not in the json.dumps(indent=1, ensure_ascii=False) form")
if list(doc.keys()) != ["tables_file", "spec", "entries"] or doc["tables_file"] != "tables.md" or doc["spec"] != "OUT\\spec\\TABLE_SPEC.md":
    bad("cells.json header keys")
E = doc["entries"]
KEYS = ["line", "table", "panel", "row", "column", "part", "printed", "cell", "source", "selector", "stored"]
for e in E:
    if list(e.keys()) != KEYS:
        bad("entry keys %r" % list(e.keys()))
        break
for i in range(len(E) - 1):
    if E[i]["line"] > E[i + 1]["line"]:
        bad("entries not in line order at %d" % i)
        break
_root_full = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(OUT_B))))  # ROOT, found at run time
for w in (os.path.basename(os.path.expanduser("~")), _root_full, _root_full.replace("\\", "/")):
    if w in md or w in raw_cj.decode("utf-8"):
        bad("a forbidden path or user fragment %r in the outputs" % w)

# ---- sources
cache = {}


def load(src):
    if src in cache:
        return cache[src]
    if src.startswith("V\\"):
        path = VDIR + "\\" + src[2:]
    elif src.startswith("SHAP\\"):
        path = SHAP + "\\" + src[5:]
    else:
        raise ValueError(src)
    if path.endswith(".parquet"):
        obj = pd.read_parquet(path)
    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    else:
        with open(path, "r", encoding="utf-8-sig") as f:
            obj = f.read().split("\n")
    cache[src] = obj
    return obj


SEG = re.compile(r'\.?([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]|\[("(?:[^"\\]|\\.)*")\]')


def jpath(obj, path):
    pos = 0
    while pos < len(path):
        m = SEG.match(path, pos)
        if not m or m.end() == pos:
            raise ValueError("bad path %r at %d" % (path, pos))
        if m.group(1) is not None:
            obj = obj[m.group(1)]
        elif m.group(2) is not None:
            obj = obj[int(m.group(2))]
        else:
            obj = obj[json.loads(m.group(3))]
        pos = m.end()
    return obj


def nn(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


SETUP = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,")
DONE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
MAXL = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")


def resolve(src, sel):
    obj = load(src)
    if src.endswith(".parquet"):
        terms = [t.split("=", 1) for t in sel.split("; ")]
        col = terms[-1]
        if col[0] != "column":
            raise ValueError(sel)
        df = obj
        for k, v in terms[:-1]:
            df = df[df[k] == v]
        if len(df) != 1:
            raise ValueError("%d rows for %s" % (len(df), sel))
        return [nn(df[col[1]].tolist()[0])]
    if src.endswith(".json"):
        if sel.startswith("len(") and sel.endswith(")"):
            return [len(jpath(obj, sel[4:-1]))]
        if " - " in sel:
            a, b = sel.split(" - ")
            return [jpath(obj, a), jpath(obj, b)]
        return [nn(jpath(obj, sel))]
    m = re.match(r"^line (\d+): (.+)$", sel)
    ln = obj[int(m.group(1)) - 1]
    field = m.group(2)
    if src.endswith("SAMPLE_REGISTER.txt"):
        fields = dict(t.split("=", 1) for t in ln.split(" ")[1:])
        return [int(fields[field])]
    if src.endswith(".log"):
        if field == "background pairs":
            return [int(SETUP.match(ln).group(4))]
        md_ = DONE.match(ln)
        return [float(md_.group(3) if field == "total seconds" else md_.group(4))]
    mm = MAXL.match(ln)
    return [float({"spread": mm.group(2), "value 1": mm.group(6), "value 3": mm.group(8)}[field])]


MINUS = "\u2212"
SUP = {"0": "\u2070", "1": "\u00b9", "2": "\u00b2", "3": "\u00b3", "4": "\u2074", "5": "\u2075", "6": "\u2076",
       "7": "\u2077", "8": "\u2078", "9": "\u2079", "-": "\u207b"}


def f_num2(x):
    if x == 0.0:
        return "0.00"
    s = format(x, ".2f")
    return MINUS + s[1:] if s[0] == "-" else s


def f_pct1(x):
    if x < 0:
        raise ValueError
    if x == 0.0:
        return "0.0%"
    y = 100.0 * x
    return "<0.1%" if y < 0.05 else format(y, ".1f") + "%"


def f_count(n):
    if isinstance(n, float):
        if not n.is_integer():
            raise ValueError
        n = int(n)
    return format(n, ",")


def f_sci2(x):
    if x == 0.0:
        return "0"
    m, e = format(abs(x), ".1e").split("e")
    return (MINUS if x < 0 else "") + m + " \u00d7 10" + "".join(SUP[c] for c in str(int(e)))


def f_secs(x):
    return format(x, ",.1f")


FMTS = [f_num2, f_pct1, f_count, f_sci2, f_secs]

for e in E:
    try:
        got = resolve(e["source"], e["selector"])
    except Exception as ex:
        bad("cannot resolve %s %s: %r" % (e["source"], e["selector"], ex))
        continue
    if got != e["stored"]:
        bad("stored differs: %s %s %r != %r" % (e["source"], e["selector"], got, e["stored"]))
        continue
    x = got[0] - got[1] if len(got) == 2 else got[0]
    if x is None:
        if e["printed"] != "undefined":
            bad("a null printed as %r" % e["printed"])
        continue
    ok = False
    for f in FMTS:
        try:
            if f(x) == e["printed"]:
                ok = True
                break
        except Exception:
            pass
    if not ok:
        bad("printed %r does not format stored %r (%s %s)" % (e["printed"], x, e["source"], e["selector"]))

# ---- each entry's cell is a cell of its line; printed tokens in order
by_line = {}
for e in E:
    by_line.setdefault(e["line"], []).append(e)
for no, es in by_line.items():
    ln = lines[no - 1]
    if ln.startswith("| "):
        cells = ln[2:-2].split(" | ")
    else:
        cells = [ln]
    # assign entries to cells left to right
    ci, pos = 0, 0
    for e in es:
        while ci < len(cells) and not (cells[ci] == e["cell"] and cells[ci].find(e["printed"], pos) >= 0):
            ci += 1
            pos = 0
        if ci >= len(cells):
            bad("line %d: entry %r not found in order" % (no, e["printed"]))
            break
        j = cells[ci].find(e["printed"], pos)
        pos = j + len(e["printed"])

# ---- coverage: no number in a table data row without an entry
# Version 4 of the spec (V4-7): the header line of S3.18 panel b (constant rows, no entries) changed, so it is read
# from the spec, the first line of its fenced block 15, instead of being typed here.
with open(os.path.join(os.path.dirname(OUT_B), "spec", "TABLE_SPEC.md"), "r", encoding="utf-8", newline="") as f:
    _spec = f.read().split("\n")
_fences = [i for i, ln in enumerate(_spec) if ln == "```"]
PANEL_B_HDR = _spec[_fences[2 * 14] + 1]
print("S3.18 panel b header (spec line %d): %s" % (_fences[2 * 14] + 2, PANEL_B_HDR))
# Version 5 of the spec (V5-4): E3m's "What it checks" (a constant cell of S3.21, no entries) now holds "SHA-256", a
# constant of the text, so the check allows that cell's whole text, read from the spec's E3m row of 4.5 (not typed
# here); a number anywhere else in that row is still checked.
_e3m = [(i, m.group(1)) for i, m in ((i, re.match(r"^\| `E3m` \| `([^`\n]+)` \| ", ln)) for i, ln in enumerate(_spec)) if m]
if len(_e3m) != 1:
    bad("the spec has %d E3m rows in 4.5, expected 1" % len(_e3m))
E3M_WHAT = _e3m[0][1] if len(_e3m) == 1 else None
print("S3.21 E3m \"What it checks\" (spec line %s): %s" % (_e3m[0][0] + 1 if E3M_WHAT else "?", E3M_WHAT))
ALLOW = ([E3M_WHAT] if E3M_WHAT else []) + [
         "treeroute v1", "PM2.5", "B1 run", "D8 tolerance", "top-20", "top-10", "[95% CI]", "p = 0.95", "p = 0.9",
         "top 3", "Top 3 (share)", "Jaccard top 5", "Jaccard top 10", "Jaccard top 20", "E3a", "E3m", "E5a", "E5\u1d43", "E10", "E0", "E1",
         "E2", "E3", "E4", "E6", "E7", "E8", "E9", "Rows with a forecast above 0"]
panel_b_s318 = False
for no, ln in enumerate(lines, 1):
    if ln.startswith(PANEL_B_HDR):
        panel_b_s318 = True
    if not ln.startswith("|"):
        panel_b_s318 = False if ln == "" else panel_b_s318
        continue
    if panel_b_s318 or set(ln) <= set("|-"):
        continue
    if no + 1 <= len(lines) and lines[no].startswith("|---"):
        continue  # a header line
    cells = ln[2:-2].split(" | ")
    es = by_line.get(no, [])
    masked = list(cells)
    for e in es:
        for k, c in enumerate(masked):
            if c.replace("#", "") and cells[k] == e["cell"] and e["printed"] in masked[k]:
                masked[k] = masked[k].replace(e["printed"], "#", 1)
                break
    for k, c in enumerate(masked):
        r = re.sub(r"`[^`]*`", "", c)
        for a in ALLOW:
            r = r.replace(a, "")
        if k == 0 and re.fullmatch(r"\d+", r):
            continue  # a Rank label
        if re.search(r"[0-9\u2070-\u2079\u00b9\u00b2\u00b3]", r):
            bad("line %d cell %d: a number without an entry: %r" % (no, k, cells[k]))

print("entries", len(E), "checked; failures:", len(fails))
for m in fails[:40]:
    print("FAIL", m)
