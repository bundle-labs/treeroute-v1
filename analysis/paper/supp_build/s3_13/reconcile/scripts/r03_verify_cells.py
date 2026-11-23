# r03: resolve every entry of OUT\A\cells.json and OUT\B\cells.json in its source with the reconciler's own
# reader of the selector grammar (TABLE_SPEC.md section 5); check stored == source, printed == the spec's
# format of stored, the cell text is a cell of that line of tables.md, the printed token sits in it, and the
# entries are in reading order. Read-only; prints a summary and every problem found.
import sys, re, json, math, collections
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *  # noqa: E402,F401,F403
import pandas as pd  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
print("format self-test vectors:", selftest())

text = (OUT / "A" / "tables.md").read_text(encoding="utf-8")
LINES = text.split("\n")


def short_to_path(src):
    if src.startswith("SHAP\\"):
        return SHAP / src[5:].replace("\\", "/")
    if src.startswith("V\\"):
        return V / src[2:].replace("\\", "/")
    raise Stop("unknown source prefix " + src)


_cache = {}


def jsonsrc(path):
    if path not in _cache:
        strict = path.name == "results.json"
        _cache[path] = load_json(path, strict=strict)
    return _cache[path]


def pq(path):
    if path not in _cache:
        _cache[path] = pd.read_parquet(path)
    return _cache[path]


def textlines(path):
    key = ("lines", path)
    if key not in _cache:
        raw = path.read_bytes()
        t = raw.decode("utf-8")
        if t.startswith("﻿"):
            t = t[1:]
        _cache[key] = t.replace("\r\n", "\n").split("\n")
    return _cache[key]


def json_path(obj, sel):
    pos, cur = 0, obj
    first = True
    while pos < len(sel):
        if sel[pos] == "[":
            if sel[pos + 1] == '"':
                # JSON string key
                dec = json.JSONDecoder()
                key, end = dec.raw_decode(sel, pos + 1)
                if sel[end] != "]":
                    raise Stop("bad selector " + sel)
                cur = cur[key]
                pos = end + 1
            else:
                end = sel.index("]", pos)
                cur = cur[int(sel[pos + 1:end])]
                pos = end + 1
        else:
            if not first:
                if sel[pos] != ".":
                    raise Stop("bad selector " + sel)
                pos += 1
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", sel[pos:])
            if not m:
                raise Stop("bad selector " + sel)
            cur = cur[m.group(0)]
            pos += len(m.group(0))
        first = False
    return cur


KEYCOLS = {"pairs.parquet": ["level", "model_a", "model_b", "statistic"], "importance.parquet": ["level", "model", "player"],
           "families.parquet": ["model", "family"]}

SETUP = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] (\w+) lead 0: (\d+) rows, (\d+) background pairs,")
DONE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \+\s*[0-9.]+s\] treeroute SHAP (\w+) lead 0 done in ([0-9.]+) s \(tree SHAP ([0-9.]+) s\)$")
MAXL = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ \(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")


def resolve(src, sel):
    """returns the list of stored values the selector names"""
    path = short_to_path(src)
    name = path.name
    if name.endswith(".parquet"):
        terms = sel.split("; ")
        kv = dict(t.split("=", 1) for t in terms)
        col = kv.pop("column")
        if sorted(kv) != sorted(KEYCOLS[name]):
            raise Stop("key columns of %s: %s" % (name, sorted(kv)))
        df = pq(path)
        mask = pd.Series(True, index=df.index)
        for k, v in kv.items():
            mask &= df[k].astype(str) == v
        sub = df[mask]
        if len(sub) != 1:
            raise Stop("%d rows for %s %s" % (len(sub), src, sel))
        x = sub.iloc[0][col]
        x = x.item() if hasattr(x, "item") else x
        return [nan2none(x)]
    if name.endswith(".json"):
        obj = jsonsrc(path)
        m = re.match(r"^len\((.*)\)$", sel)
        if m:
            return [len(json_path(obj, m.group(1)))]
        if " - " in sel:
            a, b = sel.split(" - ")
            return [nan2none(json_path(obj, a)), nan2none(json_path(obj, b))]
        return [nan2none(json_path(obj, sel))]
    # text sources: "line <n>: <field>"
    m = re.match(r"^line (\d+): (.+)$", sel)
    if not m:
        raise Stop("bad text selector " + sel)
    n, field = int(m.group(1)), m.group(2)
    L = textlines(path)[n - 1]
    if name == "SAMPLE_REGISTER.txt":
        kv = dict(x.split("=", 1) for x in L.split(" ")[1:])
        return [int(kv[field])]
    if name == "bardl_maxima.txt":
        mm = MAXL.match(L)
        return [float({"spread": mm.group(2), "value 1": mm.group(6), "value 2": mm.group(7), "value 3": mm.group(8)}[field])]
    if name.endswith(".log"):
        if field == "background pairs":
            return [int(SETUP.match(L).group(4))]
        mm = DONE.match(L)
        return [float({"total seconds": mm.group(3), "tree SHAP seconds": mm.group(4)}[field])]
    raise Stop("unknown text source " + src)


def fmt_kind(e):
    t, pan, col, part = e["table"], e["panel"], e["column"], e["part"]
    if t in ("9", "S3.22"):
        return "NUM2"
    if t == "S3.19":
        return "MED" if part == "median" else "COUNT"
    if t == "S3.20":
        return "SCI2" if col in ("max_abs_diff", "additivity", "s_exact") else "COUNT"
    if t == "S3.21":
        return "SCI2" if part == "max_rel" else "COUNT"
    if t in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27"):
        if e["row"] == "note":
            return "COUNT" if col in ("z_var", "j_var", "z_feat", "j_feat") else "NUM2"
        if pan in ("a", "b", "c"):
            return "COUNT" if part in ("n_finite", "signs") else "NUM2"
        if pan in ("d", "e", "g"):
            return "COUNT" if part == "count" else "PCT1"
        if pan == "f":
            return "PCT1"
    if t == "S3.28":
        return "COUNT" if part in ("n_finite", "count", "determined", "agree") else "NUM2"
    if t == "S3.29":
        if part == "n_finite":
            return "COUNT"
        return "NUM2" if e["row"] == "own_history_share" else "PCT1"
    if t == "S3.30":
        if col in ("total_seconds", "tree_shap_seconds"):
            return "SECS"
        if e["row"] in ("max_abs_diff_phi", "max_abs_diff_phiv"):
            return "SCI2"
        return "COUNT"
    raise Stop("no format for %r" % (e,))


FMT = {"NUM2": NUM2, "PCT1": PCT1, "COUNT": COUNT, "SCI2": SCI2, "SECS": SECS, "MED": MED}


def cells_of_line(ln):
    s = LINES[ln - 1]
    if s.startswith("| ") and s.endswith(" |"):
        inner = s[2:-2]
        out, pos = [], 2
        for c in inner.split(" | "):
            out.append((pos, c))
            pos += len(c) + 3
        return out
    return [(0, s)]


def check(doc, label):
    probs = []
    ents = doc["entries"]
    if list(doc.keys()) != ["tables_file", "spec", "entries"] or doc["tables_file"] != "tables.md" or doc["spec"] != "OUT\\spec\\TABLE_SPEC.md":
        probs.append("top-level keys/values")
    keyorder = ["line", "table", "panel", "row", "column", "part", "printed", "cell", "source", "selector", "stored"]
    cursor = {}
    lastline = 0
    kinds = collections.Counter()
    for i, e in enumerate(ents):
        if list(e.keys()) != keyorder:
            probs.append((i, "key order"))
        try:
            got = resolve(e["source"], e["selector"])
        except Exception as ex:  # noqa: BLE001
            probs.append((i, "resolve failed", e["source"], e["selector"], repr(ex)))
            continue
        if got != e["stored"] or any(type(a) != type(b) for a, b in zip(got, e["stored"])):
            probs.append((i, "stored != source", e["stored"], got))
        kind = fmt_kind(e)
        kinds[kind] += 1
        st = e["stored"]
        if e["printed"] == "undefined":
            if st != [None]:
                probs.append((i, "undefined with stored", st))
        else:
            if len(st) == 2:   # derived difference
                val = st[0] - st[1]
            else:
                val = st[0]
            try:
                want = FMT[kind](val)
            except Exception as ex:  # noqa: BLE001
                probs.append((i, "format failed", kind, val, repr(ex)))
                continue
            if want != e["printed"]:
                probs.append((i, "printed != format(stored)", kind, val, e["printed"], want))
        # cell on that line
        if e["line"] < lastline:
            probs.append((i, "line order"))
        lastline = e["line"]
        cl = cells_of_line(e["line"])
        line_text = LINES[e["line"] - 1]
        pos0 = cursor.get(e["line"], 0)
        found = None
        tok = e["printed"]
        k = line_text.find(tok, pos0)
        while k != -1:
            prev = line_text[k - 1] if k > 0 else " "
            prev2 = line_text[k - 2] if k > 1 else " "
            nxt = line_text[k + len(tok)] if k + len(tok) < len(line_text) else " "
            nxt2 = line_text[k + len(tok) + 1] if k + len(tok) + 1 < len(line_text) else " "
            bad_prev = prev.isdigit() or (prev in ".," and prev2.isdigit()) or prev in "−-"
            bad_next = nxt.isdigit() or (nxt in ".," and nxt2.isdigit()) or nxt == "%"
            okb = not bad_prev and not bad_next
            if okb:
                for (cp, ctext) in cl:
                    if cp <= k < cp + len(ctext) and ctext == e["cell"] and k + len(tok) <= cp + len(ctext):
                        found = k
                        break
            if found is not None:
                break
            k = line_text.find(tok, k + 1)
        if found is None:
            probs.append((i, "token not found in order in its cell", e["line"], tok, e["cell"][:80]))
        else:
            cursor[e["line"]] = found + len(tok)
    print(label, "entries", len(ents), "format kinds", dict(kinds), "problems", len(probs))
    for p in probs[:40]:
        print("   ", p)
    return probs


da = load_json(OUT / "A" / "cells.json")
db = load_json(OUT / "B" / "cells.json")
pa = check(da, "A")
pb = check(db, "B")
# cells.json text form: json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"
for X, d in (("A", da), ("B", db)):
    raw = (OUT / X / "cells.json").read_text(encoding="utf-8")
    print(X, "cells.json written as the spec's json.dumps form:", raw == json.dumps(d, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
# every line of tables.md that holds a data number: count entries per table
per_table = collections.Counter(e["table"] for e in da["entries"])
print("entries per table:", dict(sorted(per_table.items(), key=lambda t: (len(t[0]), t[0]))))

# completeness: every number printed in a data cell (or a note with placeholders) has an entry, and no entry
# is left over. Constant columns (labels, gate names, ranks) are skipped; backticked names are removed first.
TOKRE = re.compile(r"(?<![\w.,−-])(<0\.1%|undefined|−?\d[\d,]*\.\d × 10[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+|−?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|−?\d+(?:\.\d+)?%?)(?![\w.,]\d|\d)")
_, TABLES, NOTES = parse_tables(text)
SKIP = {"9": 1, "S3.19": 1, "S3.20": 2, "S3.21": 2, "S3.22": 1, "S3.28": 1, "S3.29": 1, "S3.30": 1}
by_line = collections.defaultdict(list)
for e in da["entries"]:
    by_line[e["line"]].append(e["printed"])
miss = []
seen_lines = set()
for (tid, pan), t in TABLES.items():
    if tid == "S3.18":
        continue
    if tid in SKIP:
        skip = SKIP[tid]
    else:
        skip = 2 if pan in ("a", "b") else 1
    for r, ln in zip(t["rows"], t["lines"]):
        toks = []
        for c in r[skip:]:
            c2 = re.sub(r"`[^`]*`", "", c)
            toks += TOKRE.findall(c2)
        seen_lines.add(ln)
        if collections.Counter(toks) != collections.Counter(by_line.get(ln, [])):
            miss.append((tid, pan, ln, sorted(toks), sorted(by_line.get(ln, []))))
for tid, nl in NOTES.items():
    for ln, nt in nl:
        if ln in by_line:
            seen_lines.add(ln)
            toks = TOKRE.findall(re.sub(r"`[^`]*`", "", nt))
            # constant numbers in the ndvi note text (none) and the S3.19 note's problem names (PM2.5) are removed
            toks = [x for x in toks if x not in ("2.5",)]
            if collections.Counter(toks) != collections.Counter(by_line[ln]):
                miss.append((tid, "note", ln, sorted(toks), sorted(by_line[ln])))
left = sorted(set(by_line) - seen_lines)
print("completeness: lines checked", len(seen_lines), "mismatching lines", len(miss), "entry lines not checked", left)
for m in miss[:20]:
    print("   ", m)
