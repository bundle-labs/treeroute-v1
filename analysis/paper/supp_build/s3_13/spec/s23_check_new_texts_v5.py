# s23_check_new_texts_v5.py - version 5 of TABLE_SPEC.md (2026-11-17). Read-only check that a builder who follows the
# version-5 spec prints each NEW text of the change order OUT\_brief\fix_order_v5.md exactly where the order says.
# 1. Reads the order's OLD and NEW code spans (wrapped lines joined by one space) and the sentence V5-5 adds to the
#    header comment, and builds the expected version 5 of tables.md from the agreed version-4 tables
#    (OUT\reconcile\tables_agreed.md): each OLD replaced by its NEW on the line the order names, and the sentence
#    inserted directly after the Version 4 sentence of line 1.
# 2. Instantiates every changed printed text of TABLE_SPEC.md: the fenced blocks (header comment, Table 9 caption,
#    S3.19 notes, S3.21 notes) and the S3.21 rows E3m and E5 (their constant "What it checks" cells; E5's constant
#    problem cell; E3m's problem-cell rule applied to the five rebuild records SHAP\rebuild\<p>\lead_0\gates.json).
#    Each must equal the expected line, and together they must cover every expected changed line.
# 3. Lists the number tokens that each changed line adds or removes (each must sit inside a text the order quotes),
#    checks the cells.json entries (OUT\reconcile\cells.json) against the expected version 5, and checks that the
#    spec's rules and constants (sections 0 to 8) hold every NEW text and no OLD text.
# Prints only. Run from this folder: py -3.9 -I -B s23_check_new_texts_v5.py
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


order = rd("_brief", "fix_order_v5.md")
agreed = rd("reconcile", "tables_agreed.md").split("\n")[:-1]
S4 = rd("spec", "TABLE_SPEC_v4.md").split("\n")
S5 = rd("spec", "TABLE_SPEC.md").split("\n")
cells = json.loads(rd("reconcile", "cells.json"))
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


def norm(s):
    return re.sub(r"[ \t]*\n[ \t]*", " ", s)


def COUNT(n):
    if not (isinstance(n, int) or (isinstance(n, float) and n.is_integer())):
        raise ValueError("COUNT of a non-integer")
    return format(int(n), ",")


# ---- 1. The order's texts, by position (checked by a key below).
spans = [(m.group(1), norm(m.group(2))) for m in re.finditer(r"(OLD|NEW)[^`:\n]*:\s+`(.*?)`", order, re.S)]
OLD = [t for k, t in spans if k == "OLD"]
NEW = [t for k, t in spans if k == "NEW"]
adds = [norm(m.group(1)) for m in re.finditer(r"after the Version 4 sentence, add `(.*?)`", order, re.S)]
print("order: {} OLD texts, {} NEW texts, {} added sentence".format(len(OLD), len(NEW), len(adds)))
NAMES = ["V5-1 Table 9 families", "V5-2 Table 9 caption", "V5-2 S3.19 note c", "V5-3 E5", "V5-3 S3.21 note a",
         "V5-4 E3m"]
KEYS = [("local drivers", "local drivers"), ("(forest loss", "(forest loss"), ("a pool of", "a pool of"),
        ("tree-bank fingerprint", "fingerprint of the"), ("the rebuilt tree bank's", "the rebuilt fingerprint"),
        ("a moved dataset", "a moved dataset")]
if len(OLD) != 6 or len(NEW) != 6 or len(adds) != 1:
    fail("expected 6 OLD texts, 6 NEW texts and one added sentence")
it = collections.OrderedDict()
for i, name in enumerate(NAMES):
    o, n = OLD[i], NEW[i]
    if not o.startswith(KEYS[i][0]) or not n.startswith(KEYS[i][1]):
        fail("order texts {} ({}) do not start with {!r}: {!r} / {!r}".format(i, name, KEYS[i], o[:40], n[:40]))
    it[name] = (o, n)
ADD = adds[0]
if not ADD.startswith("Version 5 (2026-11-17, after the fourth check):"):
    fail("the added header sentence does not start as expected")
for name, (o, n) in it.items():
    print("  {:22s} OLD {!r}".format(name, o))
    print("  {:22s} NEW {!r}".format("", n))
print("  {:22s} ADD {!r}".format("V5-5 header comment", ADD))

# ---- 2. Expected version 5 of tables.md.
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


def one(pred, what):
    hits = [i for i, ln in enumerate(exp) if pred(ln)]
    if len(hits) != 1:
        fail("{}: {} lines found, not 1".format(what, len(hits)))
        return None
    return hits[0]


cap9 = one(lambda ln: ln.startswith("**Table 9.**"), "Table 9 caption")
rep("V5-1 Table 9 families", cap9, *it["V5-1 Table 9 families"])
rep("V5-2 Table 9 caption", cap9, *it["V5-2 Table 9 caption"])
i = one(lambda ln: ln.startswith("ᶜ Background (B2)"), "S3.19 note c")
if i is not None and table_of[i] != "S3.19":
    fail("V5-2: note c not in Table S3.19")
rep("V5-2 S3.19 note c", i, *it["V5-2 S3.19 note c"])
for g, name in (("E5ᵃ", "V5-3 E5"), ("E3m", "V5-4 E3m")):
    o, n = it[name]
    i = one(lambda ln, g=g, o=o: ln.startswith("| " + g + " | " + o + " | "), "S3.21 row " + g)
    if i is not None and table_of[i] != "S3.21":
        fail(name + ": not in Table S3.21")
    rep(name, i, "| " + g + " | " + o + " | ", "| " + g + " | " + n + " | ")
i = one(lambda ln: ln.startswith("ᵃ E5 is informational"), "S3.21 note a")
if i is not None and table_of[i] != "S3.21":
    fail("V5-3: note a not in Table S3.21")
rep("V5-3 S3.21 note a", i, *it["V5-3 S3.21 note a"])
V4S = "CHANGES_v4.md lists; no number changed."
if exp[0].count(V4S + " Built from") != 1:
    fail("V5-5: the Version 4 sentence is not followed once by ' Built from'")
else:
    exp[0] = exp[0].replace(V4S + " Built from", V4S + " " + ADD + " Built from")
    where["V5-5 header comment"].append(0)
changed = sorted(i for i in range(len(exp)) if exp[i] != agreed[i])
print("expected version 5 of tables.md: {} lines (version 4: {}); {} lines differ from version 4 (1-based): {}".format(
    len(exp), len(agreed), len(changed), [i + 1 for i in changed]))
for name in list(it) + ["V5-5 header comment"]:
    if not where[name]:
        fail(name + ": not applied")
    else:
        print("  {:22s} line {} ({})".format(name, ", ".join(str(i + 1) for i in where[name]),
                                             table_of[where[name][0]] or "header"))
for name, (o, n) in it.items():
    if any(n in ln for ln in agreed):
        fail(name + ": the NEW text is already in version 4 of tables.md")
if any(ADD in ln for ln in agreed):
    fail("V5-5: the added sentence is already in version 4 of tables.md")


# ---- 3. The version-5 spec's texts.
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


B4, B5 = blocks(S4), blocks(S5)
covered = set()


def block_by_first(blist, prefix):
    hits = [(k, b) for k, b in enumerate(blist) if b["lines"] and b["lines"][0].startswith(prefix)]
    if len(hits) != 1:
        fail("block starting {!r} found {} times".format(prefix, len(hits)))
        return None, None
    return hits[0]


def check_block_lines(prefix):
    k5, b5 = block_by_first(B5, prefix)
    k4, b4 = block_by_first(B4, prefix)
    if b5 is None or b4 is None:
        return
    if k5 != k4:
        fail("block {!r} is at position {} in version 5 and {} in version 4".format(prefix, k5 + 1, k4 + 1))
    first = b5["lines"][0]
    starts = [i for i, ln in enumerate(exp) if ln == first]
    if len(starts) != 1:
        fail("block {!r}: its first line is {} times in the expected tables".format(prefix, len(starts)))
        return
    s = starts[0]
    for d, ln in enumerate(b5["lines"]):
        if exp[s + d] != ln:
            fail("block {!r}, line {}: differs from the expected line {}".format(prefix, d + 1, s + d + 1))
        covered.add(s + d)
    print("  block {:2d} {!r}: {} lines = expected lines {}-{}{}".format(
        k5 + 1, prefix[:36], len(b5["lines"]), s + 1, s + len(b5["lines"]),
        "" if b5["lines"] == b4["lines"] else " (changed in version 5)"))


print("fenced blocks: version 4 {}, version 5 {}".format(len(B4), len(B5)))
for p in ("<!-- Draft tables", "**Table 9.**", "ᵃ Frame:", "ᵃ E5 is informational"):
    check_block_lines(p)

# 3a. The S3.21 rows E5 and E3m: "What it checks" (constant) and the problem cells.
gates_rows = {}
for ln in S5:
    m = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| (.*) \|$", ln)
    if m:
        gates_rows[m.group(1)] = (m.group(2), m.group(3))
records = {}
for p in PROBLEMS:
    with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
        records[p] = json.load(fh)["gates"]
for g, name in (("E5ᵃ", "V5-3 E5"), ("E3m", "V5-4 E3m")):
    if g not in gates_rows:
        fail("S3.21 row {} not in the spec".format(g))
        continue
    what, rule = gates_rows[g]
    if what != it[name][1]:
        fail("S3.21 {}: 'What it checks' is not the order's NEW text".format(g))
    if g == "E5ᵃ":
        if rule != "`differs (informational)`":
            fail("S3.21 E5: the problem cell is not the constant 'differs (informational)'")
        got = ["differs (informational)"] * 5
    else:
        mm = re.fullmatch(r'if G has `E3m_recorded_path_map`: "([^"]+)" \+ COUNT\(len\(V `files`\)\) \+ \("([^"]+)" '
                          r'if that count is 1, else "([^"]+)"\); else `([^`]+)`', rule)
        if not mm:
            fail("S3.21 E3m: the problem-cell rule not parsed: {!r}".format(rule[:80]))
            continue
        got = []
        for p in PROBLEMS:
            G = records[p]
            if "E3m_recorded_path_map" in G:
                n_files = len(G["E3m_recorded_path_map"]["values"]["files"])
                got.append(mm.group(1) + COUNT(n_files) + (mm.group(2) if n_files == 1 else mm.group(3)))
            else:
                got.append(mm.group(4))
    i = one(lambda ln, g=g, what=what: ln.startswith("| " + g + " | " + what + " | "), "S3.21 row " + g)
    if i is None:
        continue
    want = "| " + g + " | " + what + " | " + " | ".join(got) + " |"
    if exp[i] != want:
        fail("S3.21 {}: the spec row gives {!r}, expected {!r}".format(g, want[:100], exp[i][:100]))
    else:
        covered.add(i)
        print("  S3.21 {:4s} row: 'What it checks' = order NEW; problem cells {} (expected line {})".format(
            g, got, i + 1))

missing = [i + 1 for i in changed if i not in covered]
print("changed lines covered by an instantiated spec text: {} of {}; not covered: {}".format(
    len([i for i in changed if i in covered]), len(changed), missing))
if missing:
    fail("changed lines not produced by a checked spec text")

# 3b. Sections 0 to 8 of the spec (the rules and texts a builder follows): every NEW text, no OLD text.
end5 = next(k for k, ln in enumerate(S5) if ln.startswith("## 9. Version 2"))
body5 = "\n".join(S5[:end5])
end4 = next(k for k, ln in enumerate(S4) if ln.startswith("## 9. Version 2"))
body4 = "\n".join(S4[:end4])
rest5 = "\n".join(S5[end5:])
for name, (o, n) in it.items():
    if o not in body4:
        fail(name + ": the OLD text is not in sections 0-8 of version 4")
    if body5.count(o) - body5.count(n) * n.count(o) != 0:  # an OLD text inside its NEW text is no leftover
        fail(name + ": the OLD text is still in sections 0-8 of version 5")
    if n not in body5:
        fail(name + ": the NEW text is not in sections 0-8 of version 5")
    print("  {:22s} sections 0-8 of v5: OLD {} times, NEW {} times; sections 9-12 of v5: OLD {} times".format(
        name, body5.count(o), body5.count(n), rest5.count(o)))
if body5.count(ADD) != 1:
    fail("V5-5: the added sentence is not once in sections 0-8 of the spec")
print("spec sections 0-8: every NEW text present, no OLD text left: {}".format("yes" if ok else "see FAIL lines"))

# ---- 4. Number tokens of the changed lines (regex of OUT\skeptic\k09_number_tokens.py, as s14 and s19 used).
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
    print("  line {:3d} ({}): number tokens added {} removed {}".format(i + 1, table_of[i] or "header",
                                                                     dict(add), dict(rem)))
print("number tokens added in all: {}; removed: {}".format(dict(tot_add), dict(tot_rem)))

# ---- 5. cells.json entries against the expected version 5.
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
        fail("entry on line {}: its cell is not on the expected version-5 line".format(e["line"]))
on_changed = collections.Counter(e["line"] for e in E if e["line"] - 1 in changed)
cells_on_changed = sorted(set((e["line"], e["cell"], e["column"]) for e in E if e["line"] - 1 in changed))
print("cells.json: {} entries, spec key {!r}; on changed lines: {}; entries whose cell (a whole note line) changes:"
      " {}".format(len(E), cells.get("spec"), dict(on_changed), dict(moved)))
for ln, cell, col in cells_on_changed:
    print("  line {}: cell {!r}, column {}".format(ln, cell, col))
print("RESULT:", "every NEW text of the order is what the version-5 spec prints" if ok else "FAILED")
sys.exit(0 if ok else 1)
