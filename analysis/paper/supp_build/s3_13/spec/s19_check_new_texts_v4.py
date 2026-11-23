# s19_check_new_texts_v4.py - version 4 of TABLE_SPEC.md (2026-11-17). Read-only check that a builder who follows the
# version-4 spec prints each NEW text of the change order OUT\_brief\fix_order_v4.md exactly where the order says.
# 1. Reads the order's OLD and NEW code spans (wrapped lines joined by one space) and the text V4-13 adds to the
#    header comment, and builds the expected version 4 of tables.md from the agreed version-3 tables
#    (OUT\reconcile\tables_agreed.md): each OLD replaced by its NEW on the line the order names.
# 2. Instantiates every changed printed text of TABLE_SPEC.md: the fenced blocks (header comment, Table 9 caption,
#    S3.18 caption, S3.18 panel b table, S3.19 notes, S3.21 notes, S3.28 caption); the constant cells outside fenced
#    blocks (the "What it checks" cells of E3a, E3m, E3, E5 and E8 with the constant problem cells of E3a, E3 and E5,
#    the S3.22 row label); and the rule of S3.21's `Adopted arm` row, applied to the `result` of the five rebuild
#    records SHAP\rebuild\<p>\lead_0\gates.json. Each must equal the expected line, and together they must cover every
#    expected changed line.
# 3. Lists the number tokens that each changed line adds or removes (each must sit inside a text the order quotes),
#    checks the cells.json entries (OUT\reconcile\cells.json) against the expected version 4, and checks that the
#    spec's rules and constants (sections 0 to 8) hold every NEW text and no OLD text.
# Prints only. Run from this folder: py -3.9 -I -B s19_check_new_texts_v4.py
import collections
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
SHAP = "D:/treeroute/analysis/shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def rd(*parts):
    with open(os.path.join(OUT, *parts), encoding="utf-8") as fh:
        return fh.read()


order = rd("_brief", "fix_order_v4.md")
agreed = rd("reconcile", "tables_agreed.md").split("\n")[:-1]
S3 = rd("spec", "TABLE_SPEC_v3.md").split("\n")
S4 = rd("spec", "TABLE_SPEC.md").split("\n")
cells = json.loads(rd("reconcile", "cells.json"))
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


def norm(s):
    return re.sub(r"[ \t]*\n[ \t]*", " ", s)


# ---- 1. The order's texts, by position (checked by a key below).
spans = [(m.group(1), norm(m.group(2))) for m in re.finditer(r"(OLD|NEW)[^`:\n]*:\s+`(.*?)`", order, re.S)]
OLD = [t for k, t in spans if k == "OLD"]
NEW = [t for k, t in spans if k == "NEW"]
adds = [norm(m.group(1)) for m in re.finditer(r"after the Version 3 sentence, add `(.*?)`", order, re.S)]
print("order: {} OLD texts, {} NEW texts, {} added sentence".format(len(OLD), len(NEW), len(adds)))
NAMES = ["V4-1 E3m", "V4-2 E3a", "V4-3 S3.19 note b", "V4-3 S3.19 note c", "V4-3 Table 9 caption",
         "V4-4 Table 9 families", "V4-5 Adopted arm (NDVI)", "V4-6 E5", "V4-6 S3.21 note a", "V4-7 S3.18 b header",
         "V4-8 S3.22 row label", "V4-9 S3.28 J", "V4-10 E3", "V4-11 E8", "V4-12 S3.18 source comment"]
KEYS = [("a moved dataset", "a moved dataset"), ("inputs, before", "inputs, before"),
        ("ᵇ Coral bleaching:", "ᵇ Coral bleaching:"), ("a pool of", "a pool of"), ("(forest loss", "(forest loss"),
        ("local drivers", "local drivers"), ("identity, plain", "identity, plain"), ("bank fingerprint", "tree-bank"),
        ("the rebuilt bank's", "the rebuilt tree bank's"), ("| Problem | Rival |", "| Problem | Rival or"),
        ("Rivals in another", "Rivals that explain"), ("(the players", "(the players"), ("dataset package", "the dataset"),
        ("kept predictions", "the adopted arm's"), ("paper/draft/03_protocol.md", "paper/draft/03_protocol.md")]
if len(OLD) != 15 or len(NEW) != 15 or len(adds) != 1:
    fail("expected 15 OLD texts, 15 NEW texts and one added sentence")
it = collections.OrderedDict()
for i, name in enumerate(NAMES):
    o, n = OLD[i], NEW[i]
    if not o.startswith(KEYS[i][0]) or not n.startswith(KEYS[i][1]):
        fail("order texts {} ({}) do not start with {!r}: {!r} / {!r}".format(i, name, KEYS[i], o[:40], n[:40]))
    it[name] = (o, n)
ADD = adds[0]
if not ADD.startswith("Version 4 (2026-11-17, after the third check):"):
    fail("the added header sentence does not start as expected")

# ---- 2. Expected version 4 of tables.md.
exp = list(agreed)
if len(exp) != 785:
    fail("tables_agreed.md has {} lines, not 785".format(len(exp)))
table_of = []
cur = None
for ln in exp:
    m = re.match(r"\*\*Table (S?[0-9]+(?:\.[0-9]+)?)", ln)
    if m:
        cur = m.group(1)
    table_of.append(cur)
where = collections.defaultdict(list)  # item name -> line indices changed


def rep(name, i, o, n, times=1):
    if i is None:
        return
    c = exp[i].count(o)
    if c != times:
        fail("{}: line {}: OLD text found {} times, not {}: {!r}".format(name, i + 1, c, times, o[:60]))
        return
    exp[i] = exp[i].replace(o, n)
    where[name].append(i)


def lines_where(pred):
    return [i for i, ln in enumerate(exp) if pred(ln)]


def one(pred, what):
    hits = lines_where(pred)
    if len(hits) != 1:
        fail("{}: {} lines found, not 1".format(what, len(hits)))
        return None
    return hits[0]


cap = {t: one(lambda ln, t=t: ln.startswith("**Table " + t + " ") or ln.startswith("**Table " + t + ".**"), t)
       for t in ["9", "S3.18", "S3.28"]}
for g, name in (("E3m", "V4-1 E3m"), ("E3a", "V4-2 E3a"), ("E5ᵃ", "V4-6 E5"), ("E3", "V4-10 E3"), ("E8", "V4-11 E8")):
    o, n = it[name]
    i = one(lambda ln, g=g, o=o: ln.startswith("| " + g + " | " + o + " | "), "S3.21 row " + g)
    if i is not None and table_of[i] != "S3.21":
        fail(name + ": not in Table S3.21")
    rep(name, i, "| " + g + " | " + o + " | ", "| " + g + " | " + n + " | ")
o, n = it["V4-3 S3.19 note b"]
i = one(lambda ln: ln == o, "S3.19 note b")
rep("V4-3 S3.19 note b", i, o, n)
i = one(lambda ln: ln.startswith("ᶜ Background (B2)"), "S3.19 note c")
rep("V4-3 S3.19 note c", i, *it["V4-3 S3.19 note c"])
rep("V4-3 Table 9 caption", cap["9"], *it["V4-3 Table 9 caption"])
rep("V4-4 Table 9 families", cap["9"], *it["V4-4 Table 9 families"])
o, n = it["V4-5 Adopted arm (NDVI)"]
i = one(lambda ln: ln.startswith("| Adopted arm | "), "S3.21 Adopted arm row")
if i is not None:
    hdr = [ln for ln in exp if ln.startswith("| Gate | What it checks | ")]
    cols = hdr[0].split(" | ") if hdr else []
    row = exp[i].split(" | ")
    at = [k for k, c in enumerate(row) if c == o]
    if len(at) != 1 or cols[at[0]] != "NDVI":
        fail("V4-5: the OLD cell is not exactly NDVI's cell of the Adopted arm row")
    rep("V4-5 Adopted arm (NDVI)", i, "| " + o + " |", "| " + n + " |")
i = one(lambda ln: ln.startswith("ᵃ E5 is informational"), "S3.21 note a")
rep("V4-6 S3.21 note a", i, *it["V4-6 S3.21 note a"])
o, n = it["V4-7 S3.18 b header"]
i = one(lambda ln: ln == o, "S3.18 b header")
if i is not None and table_of[i] != "S3.18":
    fail("V4-7: header not in Table S3.18")
rep("V4-7 S3.18 b header", i, o, n)
o, n = it["V4-8 S3.22 row label"]
i = one(lambda ln: ln.startswith("| " + o + " | "), "S3.22 row")
if i is not None and table_of[i] != "S3.22":
    fail("V4-8: row not in Table S3.22")
rep("V4-8 S3.22 row label", i, "| " + o + " | ", "| " + n + " | ")
rep("V4-9 S3.28 J", cap["S3.28"], *it["V4-9 S3.28 J"])
rep("V4-12 S3.18 source comment", cap["S3.18"], *it["V4-12 S3.18 source comment"])
V3S = "CHANGES_v3.md lists; no number changed."
if exp[0].count(V3S + " Built from") != 1:
    fail("V4-13: the Version 3 sentence is not followed once by ' Built from'")
else:
    exp[0] = exp[0].replace(V3S + " Built from", V3S + " " + ADD + " Built from")
    where["V4-13 header comment"].append(0)
changed = sorted(i for i in range(len(exp)) if exp[i] != agreed[i])
print("expected version 4 of tables.md: {} lines (version 3: {}); {} lines differ from version 3 (1-based): {}".format(
    len(exp), len(agreed), len(changed), [i + 1 for i in changed]))
for name in list(it) + ["V4-13 header comment"]:
    if not where[name]:
        fail(name + ": not applied")
    else:
        print("  {:28s} line {} ({})".format(name, ", ".join(str(i + 1) for i in where[name]),
                                             table_of[where[name][0]] or "header"))
for name, (o, n) in it.items():
    if any(n in ln for ln in agreed):
        fail(name + ": the NEW text is already in version 3 of tables.md")


# ---- 3. The version-4 spec's texts.
def blocks(lines):
    out, inside, cur_ = [], False, None
    for k, ln in enumerate(lines):
        if ln.startswith("```"):
            if inside:
                out.append(cur_)
                inside = False
            else:
                inside, cur_ = True, {"at": k, "lines": []}
        elif inside:
            cur_["lines"].append(ln)
    return out


B3, B4 = blocks(S3), blocks(S4)
covered = set()


def block_by_first(blist, prefix):
    hits = [(k, b) for k, b in enumerate(blist) if b["lines"] and b["lines"][0].startswith(prefix)]
    if len(hits) != 1:
        fail("block starting {!r} found {} times".format(prefix, len(hits)))
        return None, None
    return hits[0]


def check_block_lines(prefix, v3prefix):
    k4, b4 = block_by_first(B4, prefix)
    k3, b3 = block_by_first(B3, v3prefix)
    if b4 is None or b3 is None:
        return
    if k4 != k3:
        fail("block {!r} is at position {} in version 4 and {} in version 3".format(prefix, k4 + 1, k3 + 1))
    first = b4["lines"][0]
    starts = [i for i, ln in enumerate(exp) if ln == first]
    if len(starts) != 1:
        fail("block {!r}: its first line is {} times in the expected tables".format(prefix, len(starts)))
        return
    s = starts[0]
    for d, ln in enumerate(b4["lines"]):
        if exp[s + d] != ln:
            fail("block {!r}, line {}: differs from the expected line {}".format(prefix, d + 1, s + d + 1))
        covered.add(s + d)
    print("  block {:2d} {!r}: {} lines = expected lines {}-{}{}".format(
        k4 + 1, prefix[:36], len(b4["lines"]), s + 1, s + len(b4["lines"]),
        "" if b4["lines"][0] == b3["lines"][0] else " (new first line)"))


print("fenced blocks: version 3 {}, version 4 {}".format(len(B3), len(B4)))
for p4, p3 in (("<!-- Draft tables", "<!-- Draft tables"), ("**Table 9.**", "**Table 9.**"),
               ("**Table S3.18 (post hoc).**", "**Table S3.18 (post hoc).**"),
               ("| Problem | Rival or naive baseline |", "| Problem | Rival |"), ("ᵃ Frame:", "ᵃ Frame:"),
               ("ᵃ E5 is informational", "ᵃ E5 is informational"), ("**Table S3.28", "**Table S3.28")):
    check_block_lines(p4, p3)


def spec_line(prefix, lines=S4):
    hits = [ln for ln in lines if ln.startswith(prefix)]
    if len(hits) != 1:
        fail("spec line starting {!r} found {} times".format(prefix, len(hits)))
        return ""
    return hits[0]


# 3a. The S3.21 rows: "What it checks" (constant) and the constant problem cells.
gates = {}
for ln in S4:
    m = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| (.*) \|$", ln)
    if m:
        gates[m.group(1)] = (m.group(2), m.group(3))
for g, name, const in (("E3a", "V4-2 E3a", "passed"), ("E3m", "V4-1 E3m", None), ("E3", "V4-10 E3", "passed"),
                       ("E5ᵃ", "V4-6 E5", "differs (informational)"), ("E8", "V4-11 E8", None)):
    if g not in gates:
        fail("S3.21 row {} not in the spec".format(g))
        continue
    what, rule = gates[g]
    if what != it[name][1]:
        fail("S3.21 {}: 'What it checks' is not the order's NEW text".format(g))
    i = one(lambda ln, g=g, what=what: ln.startswith("| " + g + " | " + what + " | "), "S3.21 row " + g)
    if i is None:
        continue
    if const is not None:
        if rule != "`" + const + "`":
            fail("S3.21 {}: the problem cell is not the constant {!r}".format(g, const))
        want = "| " + g + " | " + what + " | " + " | ".join([const] * 5) + " |"
        if exp[i] != want:
            fail("S3.21 {}: the spec row gives {!r}".format(g, want[:80]))
    else:
        rest_old = agreed[i].split(" | ", 2)[2]
        if exp[i].split(" | ", 2)[2] != rest_old:
            fail("S3.21 {}: the problem cells changed".format(g))
    covered.add(i)
    print("  S3.21 {:4s} row: 'What it checks' = order NEW{} (expected line {})".format(
        g, "" if const is None else ", problem cells " + repr(const), i + 1))

# 3b. The rule of the Adopted arm row, applied to the rebuild records' `result`.
rule = spec_line("| `Adopted arm` | `link, answer type and weighting; router type` | ")
m_t = re.search(r'\("([^"]+)" if R `table_kind` == plain, "([^"]+)" if corrector\)', rule)
m_w = re.search(r'\("([^"]+)" if R `weighted` is true, else "([^"]+)"\)', rule)
m_k = re.search(r'\("([^"]+)" for per_unit, "([^"]+)" for region, "([^"]+)" for neighbour\)', rule)
disp = {}
for ln in S4:
    mm = re.match(r"^\| (identity|log_c|log_mu|arcsine) \| `([^`]+)` \|$", ln)
    if mm:
        disp[mm.group(1)] = mm.group(2)
if not (m_t and m_w and m_k) or len(disp) != 4:
    fail("the Adopted arm rule or the link display table not parsed")
else:
    if m_t.group(1) != "plain tree answers":
        fail("the Adopted arm rule does not print 'plain tree answers' for a plain arm")
    TK = {"plain": m_t.group(1), "corrector": m_t.group(2)}
    KIND = {"per_unit": m_k.group(1), "region": m_k.group(2), "neighbour": m_k.group(3)}
    got = []
    for p in PROBLEMS:
        with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
            R = json.load(fh)["result"]
        got.append(disp[R["link"].split("|")[0]] + ", " + TK[R["table_kind"]] + ", "
                   + (m_w.group(1) if R["weighted"] is True else m_w.group(2)) + "; " + KIND[R["kind"]])
    i = one(lambda ln: ln.startswith("| Adopted arm | "), "S3.21 Adopted arm row")
    if i is not None:
        want = "| Adopted arm | link, answer type and weighting; router type | " + " | ".join(got) + " |"
        if exp[i] != want:
            fail("the Adopted arm rule gives {!r}".format(want))
        else:
            covered.add(i)
            print("  S3.21 Adopted arm rule on the five records' result = expected line {}: {}".format(i + 1, got))

# 3c. The S3.22 row label.
lab = spec_line("| `Rivals that explain").split("`")[1]
if lab != it["V4-8 S3.22 row label"][1]:
    fail("S3.22 row label is not the order's NEW text")
i = one(lambda ln: ln.startswith("| " + lab + " | "), "S3.22 row")
if i is not None:
    if exp[i].split(" | ", 1)[1] != agreed[i].split(" | ", 1)[1]:
        fail("S3.22 row: its cells changed")
    covered.add(i)
    print("  S3.22 row label = order NEW (expected line {})".format(i + 1))

missing = [i + 1 for i in changed if i not in covered]
print("changed lines covered by an instantiated spec text: {} of {}; not covered: {}".format(
    len([i for i in changed if i in covered]), len(changed), missing))
if missing:
    fail("changed lines not produced by a checked spec text")

# 3d. Sections 0 to 8 of the spec (the rules and texts a builder follows): every NEW text, no OLD text.
end = next(k for k, ln in enumerate(S4) if ln.startswith("## 9. Version 2"))
body4 = "\n".join(S4[:end])
end3 = next(k for k, ln in enumerate(S3) if ln.startswith("## 9. Version 2"))
body3 = "\n".join(S3[:end3])
for name, (o, n) in it.items():
    if name.startswith("V4-5"):
        o, n = '"plain answers"', '"plain tree answers"'  # the rule's literal, not a printed cell
    if o not in body3:
        fail(name + ": the OLD text is not in sections 0-8 of version 3")
    if body4.count(o) - body4.count(n) * n.count(o) != 0:  # an OLD text inside its NEW text (V4-6, E5) is no leftover
        fail(name + ": the OLD text is still in sections 0-8 of version 4")
    if n not in body4:
        fail(name + ": the NEW text is not in sections 0-8 of version 4")
if ADD not in body4:
    fail("V4-13: the added sentence is not in the spec")
print("spec sections 0-8: every NEW text present, no OLD text left: {}".format("yes" if ok else "see FAIL lines"))

# ---- 4. Number tokens of the changed lines (regex of OUT\skeptic\k09_number_tokens.py, as s14 used).
NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<]")
quoted = [t for (o, n) in it.values() for t in (o, n)] + [ADD]
tot_add, tot_rem = collections.Counter(), collections.Counter()
for i in changed:
    a, b = collections.Counter(NUM.findall(agreed[i])), collections.Counter(NUM.findall(exp[i]))
    add, rem = b - a, a - b
    tot_add += add
    tot_rem += rem
    for tok in list(add) + list(rem):
        if not any(tok in q for q in quoted):
            fail("line {}: number token {!r} is not inside a text the order quotes".format(i + 1, tok))
    if add or rem:
        print("  line {:3d} ({}): number tokens added {} removed {}".format(i + 1, table_of[i] or "header",
                                                                         dict(add), dict(rem)))
print("number tokens added in all: {}; removed: {}".format(dict(tot_add), dict(tot_rem)))

# ---- 5. cells.json entries against the expected version 4.
E = cells["entries"]
moved = collections.Counter()
for e in E:
    i = e["line"] - 1
    if e["printed"] not in e["cell"]:
        fail("entry on line {}: printed token not in its cell".format(e["line"]))
    if e["cell"] in exp[i]:
        continue
    if e["cell"] == agreed[i] and exp[i] != agreed[i]:
        moved[e["line"]] += 1  # a note line that changed: the entry's cell becomes the new line
    else:
        fail("entry on line {}: its cell is not on the expected version-4 line".format(e["line"]))
on_changed = collections.Counter(e["line"] for e in E if e["line"] - 1 in changed)
print("cells.json: {} entries; on changed lines: {}; entries whose cell (a whole note line) changes: {}".format(
    len(E), dict(on_changed), dict(moved)))
print("RESULT:", "every NEW text of the order is what the version-4 spec prints" if ok else "FAILED")
sys.exit(0 if ok else 1)
