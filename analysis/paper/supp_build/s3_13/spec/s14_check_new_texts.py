# s14_check_new_texts.py - version 3 of TABLE_SPEC.md (2026-11-17). Read-only check that a builder who follows the
# version-3 spec prints each NEW text of the change order OUT\_brief\fix_order_v3.md exactly where the order says.
# 1. Reads the order's OLD and NEW code spans (wrapped lines joined by one space) and builds the expected version 3 of
#    tables.md from the agreed version-2 tables (OUT\reconcile\tables_agreed.md): each OLD replaced by its NEW where
#    the order names it (for the S3.23-S3.27 and S3.29 items, whose OLD and NEW start with "...", the changed tail).
# 2. Instantiates every changed printed text of TABLE_SPEC.md: the fenced blocks (header comment, Table 9, S3.18
#    caption, panel b label, panel b table and notes, S3.19 caption and notes, S3.29 caption); the S3.23-S3.27 caption
#    template with its placeholder values from the version-3 bullets (and nn, Problem, p read off the version-2
#    captions with the version-2 template); the NDVI footnote template (its data placeholders read off the version-2
#    line with the version-2 template); the constant cells outside fenced blocks (S3.18 a and S3.20 skill-guard cells,
#    the random-forest constant, the S3.21 rows, the S3.22 row label) and the Link cell rule of 4.7 applied to the
#    source labels. Each must equal the expected line, and together they must cover every expected changed line.
# 3. Lists the number tokens that each changed line adds or removes (each must sit inside a text the order quotes) and
#    checks the cells.json entries (OUT\reconcile\cells.json) against the expected version 3.
# Prints only. Run from this folder: py -3.9 -I -B s14_check_new_texts.py
import collections
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)


def rd(*parts):
    with open(os.path.join(OUT, *parts), encoding="utf-8") as fh:
        return fh.read()


order = rd("_brief", "fix_order_v3.md")
agreed = rd("reconcile", "tables_agreed.md").split("\n")[:-1]
S2 = rd("spec", "TABLE_SPEC_v2.md").split("\n")
S3 = rd("spec", "TABLE_SPEC.md").split("\n")
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
anchor = norm(re.search(r"directly after `(.*?)`", order, re.S).group(1))
print("order: {} OLD texts, {} NEW texts, and the anchor of the new Table 9 sentence".format(len(OLD), len(NEW)))
NAMES = ["V3-1 Table 9 importance sentence (new)", "V3-1 Table 9 RBO", "V3-1 Table 9 own-history share",
         "V3-1 S3.19 J", "V3-1 S3.23/S3.24/S3.26 shares tail", "V3-1 S3.25/S3.27 shares tail", "V3-1 S3.29 tail",
         "V3-2 S3.18 caption", "V3-2 panel b label", "V3-2 baselines row", "V3-2 panel b note line",
         "V3-2 S3.18 source comment", "V3-3 count clause", "V3-3 S3.24 extra_src", "V3-4 BARDL footnote",
         "V3-5 S3.22 row label", "V3-6 adopted arm (S3.18 a, S3.20)", "V3-6 S3.21 first row label",
         "V3-6 random forest constant", "V3-6 S3.19 note c", "V3-6 E10", "V3-6 S3.25 pair labels", "V3-6 E3a",
         "V3-6 E3m", "V3-6 E3", "V3-6 E6", "V3-7 header, versions", "V3-7 header, cells.json"]
KEYS = ["A variable's importance", "RBO: rank-biased", "Own-history share:", "J: the players", "...the sum of its",
        "...the sum of its", "...a family's", "The models explained", "**b. Rivals and", "| All five |",
        "Panel b lists", "engine/PENDING_PARTS.md", "with the number of finite", "(the spreads", "Beyond its three",
        "Rivals in another link", "passed (the adopted arm)", "Adopted arm", "random forest, rebuilt",
        "coral bleaching: the survey", "on one sampled", "; raw model, declined by its skill", "inputs, before",
        "a moved dataset", "dataset package fingerprint", "c and the identity", "Version 2 (2026-11-17",
        "every printed data number"]
if len(NEW) != 28 or len(OLD) != 27:
    fail("expected 27 OLD and 28 NEW texts")
ITEMS = []  # (name, old or None, new)
for i, name in enumerate(NAMES):
    o = None if i == 0 else OLD[i - 1]
    n = NEW[i]
    if not n.startswith(KEYS[i]):
        fail("order text {} ({}) does not start with {!r}: {!r}".format(i, name, KEYS[i], n[:50]))
    ITEMS.append((name, o, n))
it = {name: (o, n) for name, o, n in ITEMS}


def tail(s):
    return s[3:] if s.startswith("...") else s


# ---- 2. Expected version 3 of tables.md.
exp = list(agreed)
if len(exp) != 785:
    fail("tables_agreed.md has {} lines, not 785".format(len(exp)))
table_of = []
cur = None
for ln in exp:
    m = re.match(r"\*\*Table (S?[0-9.]+)", ln)
    if m:
        cur = m.group(1)
    table_of.append(cur)
where = collections.defaultdict(list)  # item name -> line indices changed


def rep(name, i, o, n, times=1):
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
       for t in ["9", "S3.18", "S3.19", "S3.23", "S3.24", "S3.25", "S3.26", "S3.27", "S3.29"]}
name = "V3-1 Table 9 importance sentence (new)"
rep(name, cap["9"], anchor + " ", anchor + " " + it[name][1] + " ")
for name in ("V3-1 Table 9 RBO", "V3-1 Table 9 own-history share"):
    rep(name, cap["9"], *it[name])
rep("V3-1 S3.19 J", cap["S3.19"], *it["V3-1 S3.19 J"])
for t in ("S3.23", "S3.24", "S3.26"):
    o, n = it["V3-1 S3.23/S3.24/S3.26 shares tail"]
    rep("V3-1 S3.23/S3.24/S3.26 shares tail", cap[t], tail(o), tail(n))
for t in ("S3.25", "S3.27"):
    o, n = it["V3-1 S3.25/S3.27 shares tail"]
    rep("V3-1 S3.25/S3.27 shares tail", cap[t], tail(o), tail(n))
o, n = it["V3-1 S3.29 tail"]
rep("V3-1 S3.29 tail", cap["S3.29"], tail(o), tail(n))
rep("V3-2 S3.18 caption", cap["S3.18"], *it["V3-2 S3.18 caption"])
rep("V3-2 S3.18 source comment", cap["S3.18"], *it["V3-2 S3.18 source comment"])
for name in ("V3-2 panel b label", "V3-2 baselines row", "V3-2 panel b note line"):
    o, n = it[name]
    i = one(lambda ln, o=o: ln == o, name)
    if i is not None:
        rep(name, i, o, n)
for t in ("S3.23", "S3.24", "S3.25", "S3.26", "S3.27"):
    rep("V3-3 count clause", cap[t], *it["V3-3 count clause"])
rep("V3-3 S3.24 extra_src", cap["S3.24"], *it["V3-3 S3.24 extra_src"])
i = one(lambda ln: ln.startswith("‡ BARDL reads"), "the NDVI footnote")
rep("V3-4 BARDL footnote", i, *it["V3-4 BARDL footnote"])
o, n = it["V3-5 S3.22 row label"]
i = one(lambda ln: ln.startswith("| " + o + " |"), "S3.22 row")
rep("V3-5 S3.22 row label", i, "| " + o + " |", "| " + n + " |")
o, n = it["V3-6 adopted arm (S3.18 a, S3.20)"]
hits = lines_where(lambda ln: "| " + o + " |" in ln)
print("  '{}' cells: {} lines, tables {}".format(o, len(hits), collections.Counter(table_of[i] for i in hits)))
if len(hits) != 10 or collections.Counter(table_of[i] for i in hits) != {"S3.18": 5, "S3.20": 5}:
    fail("the kept-arm cells are not the 5 + 5 treeroute rows of S3.18 a and S3.20")
for i in hits:
    rep("V3-6 adopted arm (S3.18 a, S3.20)", i, "| " + o + " |", "| " + n + " |")
o, n = it["V3-6 S3.21 first row label"]
i = one(lambda ln: ln.startswith("| " + o + " | "), "S3.21 first row")
rep("V3-6 S3.21 first row label", i, "| " + o + " | ", "| " + n + " | ")
o, n = it["V3-6 random forest constant"]
hits = lines_where(lambda ln: o in ln)
if len(hits) != 5 or any(table_of[i] != "S3.18" for i in hits):
    fail("the random-forest constant is not on the 5 rows of S3.18 a")
for i in hits:
    rep("V3-6 random forest constant", i, o, n)
i = one(lambda ln: ln.startswith("ᶜ Background (B2)"), "S3.19 note c")
rep("V3-6 S3.19 note c", i, *it["V3-6 S3.19 note c"])
i = one(lambda ln: ln.startswith("| E10 | "), "E10 row")
rep("V3-6 E10", i, *it["V3-6 E10"])
o, n = it["V3-6 S3.25 pair labels"]
hits = lines_where(lambda ln: o in ln)
print("  '{}' pair labels: {} lines, tables {}".format(o, len(hits), collections.Counter(table_of[i] for i in hits)))
if len(hits) != 8 or any(table_of[i] != "S3.25" for i in hits):
    fail("the declined-by-guard labels are not the 8 Ridge pairs of S3.25")
for i in hits:
    rep("V3-6 S3.25 pair labels", i, o, n)
for g, name in (("E3a", "V3-6 E3a"), ("E3m", "V3-6 E3m"), ("E3", "V3-6 E3"), ("E6", "V3-6 E6")):
    i = one(lambda ln, g=g: ln.startswith("| " + g + " | "), g + " row")
    rep(name, i, "| " + g + " | " + it[name][0] + " |", "| " + g + " | " + it[name][1] + " |")
rep("V3-7 header, versions", 0, *it["V3-7 header, versions"])
rep("V3-7 header, cells.json", 0, *it["V3-7 header, cells.json"])
changed = sorted(i for i in range(len(exp)) if exp[i] != agreed[i])
print("expected version 3 of tables.md: {} lines (version 2: {}); {} lines differ from version 2 (1-based): {}".format(
    len(exp), len(agreed), len(changed), [i + 1 for i in changed]))
for name, o, n in ITEMS:
    if not where[name]:
        fail(name + ": not applied")


# ---- 3. The version-3 spec's texts.
def blocks(lines):
    out, inside, cur = [], False, None
    for k, ln in enumerate(lines):
        if ln.startswith("```"):
            if inside:
                out.append(cur)
                inside = False
            else:
                inside, cur = True, {"at": k, "lines": []}
        elif inside:
            cur["lines"].append(ln)
    return out


B2, B3 = blocks(S2), blocks(S3)
covered = set()


def block_by_first(blist, prefix):
    hits = [(k, b) for k, b in enumerate(blist) if b["lines"] and b["lines"][0].startswith(prefix)]
    if len(hits) != 1:
        fail("block starting {!r} found {} times".format(prefix, len(hits)))
        return None, None
    return hits[0]


def check_block_lines(prefix, v2prefix):
    k3, b3 = block_by_first(B3, prefix)
    k2, b2 = block_by_first(B2, v2prefix)
    if b3 is None or b2 is None:
        return
    if k3 != k2:
        fail("block {!r} is at position {} in version 3 and {} in version 2".format(prefix, k3 + 1, k2 + 1))
    first = b3["lines"][0]
    starts = [i for i, ln in enumerate(exp) if ln == first]
    if len(starts) != 1:
        fail("block {!r}: its first line is {} times in the expected tables".format(prefix, len(starts)))
        return
    s = starts[0]
    for d, ln in enumerate(b3["lines"]):
        if exp[s + d] != ln:
            fail("block {!r}, line {}: differs from the expected line {}".format(prefix, d + 1, s + d + 1))
        covered.add(s + d)
    print("  block {:2d} {!r}: {} lines = expected lines {}-{}".format(k3 + 1, prefix[:30], len(b3["lines"]), s + 1,
                                                                       s + len(b3["lines"])))


print("fenced blocks: version 2 {}, version 3 {}".format(len(B2), len(B3)))
for p3, p2 in (("<!-- Draft tables", "<!-- Draft tables"), ("**Table 9.**", "**Table 9.**"),
               ("**Table S3.18 (post hoc).**", "**Table S3.18 (post hoc).**"),
               ("**b. Rivals and naive baselines left out.**", "**b. Rivals left out.**"),
               ("| Problem | Rival |", "| Problem | Rival |"), ("Panel b lists", "Panel b lists"),
               ("**Table S3.19 (post hoc).**", "**Table S3.19 (post hoc).**"), ("ᵃ Frame:", "ᵃ Frame:"),
               ("**Table S3.29", "**Table S3.29")):
    check_block_lines(p3, p2)


def to_regex(template):
    seen, out, pos = set(), [], 0
    for m in re.finditer(r"\{([A-Za-z][A-Za-z0-9_]*)\}", template):
        out.append(re.escape(template[pos:m.start()]))
        nm = m.group(1)
        out.append("(?P={})".format(nm) if nm in seen else "(?P<{}>.*?)".format(nm))
        seen.add(nm)
        pos = m.end()
    out.append(re.escape(template[pos:]))
    return re.compile("^" + "".join(out) + "$")


def fill(template, values):
    return re.sub(r"\{([A-Za-z][A-Za-z0-9_]*)\}", lambda m: values[m.group(1)], template)


# 3a. The S3.23-S3.27 caption template and its placeholder values (version-3 bullets).
_, t2b = block_by_first(B2, "**Table S3.{nn}")
k3, t3b = block_by_first(B3, "**Table S3.{nn}")
t2, t3 = t2b["lines"][0], t3b["lines"][0]
gl = [ln for ln in S3 if ln.startswith("- `{g_clause}`: ")]
xs = [ln for ln in S3 if ln.startswith("- `{extra_src}`: ")]
xr = [ln for ln in S3 if ln.startswith("- `{extra_rulings}`: ")]
sb = [i for i, ln in enumerate(S3) if ln.startswith("- `{shares_sentence}` ")]
if not (len(gl) == len(xs) == len(xr) == len(sb) == 1):
    fail("the four placeholder bullets of 4.7 not found once each")
g_val = re.match(r"^- `\{g_clause\}`: fire and coral `(.*)`;$", gl[0]).group(1)
x_val = re.match(r"^- `\{extra_src\}`: ndvi `(.*)`;$", xs[0]).group(1)
mr = re.match(r"^- `\{extra_rulings\}`: ndvi `(.*?)`; defo and coral `(.*?)`; else empty\.$", xr[0])
ss = re.findall(r"^  `(.*)`;?$", "\n".join(S3[sb[0] + 1:sb[0] + 5]), re.M)
if len(ss) != 2:
    fail("the two {shares_sentence} values not found")
o, n = it["V3-3 S3.24 extra_src"]
if not x_val.endswith(n):
    fail("{extra_src} does not end with the order's NEW text")
o, n = it["V3-1 S3.25/S3.27 shares tail"]
if not ss[0].endswith(tail(n)) or tail(o) in ss[0]:
    fail("{shares_sentence} (d, e, g) value: wrong tail")
o, n = it["V3-1 S3.23/S3.24/S3.26 shares tail"]
if not ss[1].endswith(tail(n)) or tail(o) in ss[1]:
    fail("{shares_sentence} (d, e) value: wrong tail")
o, n = it["V3-3 count clause"]
if n not in t3 or o in t3:
    fail("the caption template does not hold the NEW count clause")
rx2 = to_regex(t2)
n_cap = 0
for ln in agreed:
    m = rx2.match(ln)
    if not m:
        continue
    n_cap += 1
    d = m.groupdict()
    p = d["p"]
    d["g_clause"] = g_val if p in ("fire", "coral") else ""
    d["extra_src"] = x_val if p == "ndvi" else ""
    d["extra_rulings"] = mr.group(1) if p == "ndvi" else (mr.group(2) if p in ("defo", "coral") else "")
    d["shares_sentence"] = ss[0] if p in ("fire", "coral") else ss[1]
    got = fill(t3, d)
    i = cap["S3." + d["nn"]]
    if got != exp[i]:
        fail("caption S3.{}: the instantiated version-3 template differs from the expected line".format(d["nn"]))
    else:
        covered.add(i)
        print("  caption S3.{} ({}): template = expected line {}".format(d["nn"], p, i + 1))
if n_cap != 5:
    fail("the version-2 template matched {} version-2 captions, not 5".format(n_cap))

# 3b. The NDVI footnote (data placeholders read off the version-2 line with the version-2 template).
_, f2 = block_by_first(B2, "‡ BARDL reads")
_, f3 = block_by_first(B3, "‡ BARDL reads")
rx = to_regex(f2["lines"][0])
hits = [ln for ln in agreed if rx.match(ln)]
if len(hits) != 1:
    fail("the version-2 footnote template matched {} lines".format(len(hits)))
else:
    got = fill(f3["lines"][0], rx.match(hits[0]).groupdict())
    i = one(lambda ln: ln.startswith("‡ BARDL reads"), "the NDVI footnote")
    if got != exp[i]:
        fail("NDVI footnote: the instantiated version-3 text differs from the expected line")
    else:
        covered.add(i)
        print("  NDVI footnote: template = expected line {}".format(i + 1))
    if it["V3-4 BARDL footnote"][1] not in got:
        fail("NDVI footnote: NEW text missing")


# 3c. Constant cells outside fenced blocks.
def spec_line(prefix):
    hits = [ln for ln in S3 if ln.startswith(prefix)]
    if len(hits) != 1:
        fail("spec line starting {!r} found {} times".format(prefix, len(hits)))
        return ""
    return hits[0]


for prefix, tbl, nm in (("| Skill guard at the nowcast | treeroute: `", "S3.18", "4.2"),
                        ("| Skill guard | treeroute: `", "S3.20", "4.4")):
    v = spec_line(prefix)[len(prefix):].split("`")[0]
    if v != it["V3-6 adopted arm (S3.18 a, S3.20)"][1]:
        fail(nm + " skill-guard cell for treeroute is not the order's NEW text")
    rows = [i for i in range(len(exp)) if table_of[i] == tbl and "| treeroute v1 " in exp[i] and "| " + v + " |" in exp[i]]
    covered.update(rows)
    print("  {} skill-guard cell {!r}: on {} expected treeroute rows of {}".format(nm, v, len(rows), tbl))
rf = spec_line("| rival_rf | `random forest, rebuilt").split("`")[1]  # 4.2's constant (2.2 has another rival_rf row)
if it["V3-6 random forest constant"][1] not in rf:
    fail("random-forest constant lacks the NEW text")
rows = [i for i in range(len(exp)) if table_of[i] == "S3.18" and "| " + rf + " |" in exp[i]]
covered.update(rows)
print("  4.2 random-forest constant: on {} expected rows of S3.18 a".format(len(rows)))
gates = {}
for ln in S3:
    m = re.match(r"^\| `([^`]+)` \| `([^`]+)` \| ", ln)
    if m:
        gates[m.group(1)] = m.group(2)
for g, name in (("Adopted arm", None), ("E3a", "V3-6 E3a"), ("E3m", "V3-6 E3m"), ("E3", "V3-6 E3"),
                ("E6", "V3-6 E6"), ("E10", "V3-6 E10")):
    if g not in gates:
        fail("S3.21 row {} not in the spec".format(g))
        continue
    if name is not None and not gates[g].endswith(it[name][1]):
        fail("S3.21 {}: 'What it checks' does not end with the order's NEW text".format(g))
    if g == "Adopted arm" and g != it["V3-6 S3.21 first row label"][1]:
        fail("S3.21 first row label is not the order's NEW text")
    i = one(lambda ln, g=g: ln.startswith("| " + g + " | " + gates[g] + " | "), "S3.21 row " + g)
    if i is not None:
        covered.add(i)
lab = spec_line("| `Rivals in another link").split("`")[1]
if lab != it["V3-5 S3.22 row label"][1]:
    fail("S3.22 row label is not the order's NEW text")
i = one(lambda ln: ln.startswith("| " + lab + " | "), "S3.22 row")
if i is not None:
    covered.add(i)
print("  S3.21 rows Adopted arm, E3a, E3m, E3, E6, E10 and the S3.22 row label: on their expected lines")

# 3d. The Link cell rule of 4.7, applied to the source labels.
rule = spec_line("| Link | - | from the pair's `pair_label`")
m = re.search(r'with M = "(.*?)" \(the source label\'s words, check 3\.3\) and P = "(.*?)" \(the printed words; '
              r'version 3, V3-6\), if the label holds M, the text before M \+ P \+ the inline names', rule)
inline = {}
for ln in S3:
    mm = re.match(r"^\| (treeroute|rival_[a-z0-9_]+) \| `([^`]+)` \| `([^`]+)` \|$", ln)
    if mm:
        inline[mm.group(1)] = mm.group(2)
data_of = {v: k for k, v in inline.items()}
if not m:
    fail("the Link cell rule's M and P not found")
else:
    M, P = m.group(1), m.group(2)
    if M != it["V3-6 S3.25 pair labels"][0] or P != it["V3-6 S3.25 pair labels"][1]:
        fail("the rule's M and P are not the order's OLD and NEW")

    def link_cell(label):
        if M in label:
            before, after = label.split(M, 1)
            return before + P + ", ".join(inline[x] for x in after.split(", "))
        return label

    ex = re.search(r"So `(.*?)` prints `(.*?)` \|$", rule)
    if not ex or link_cell(ex.group(1)) != ex.group(2):
        fail("the rule's example does not follow from the rule")
    n_lab = 0
    for i in range(len(exp)):
        if table_of[i] != "S3.25" or not agreed[i].startswith("| "):
            continue
        c2 = agreed[i].split(" | ")
        if len(c2) < 3 or M not in c2[1]:
            continue
        before, after = c2[1].split(M, 1)
        source = before + M + ", ".join(data_of[x] for x in after.split(", "))  # the label as pairs.parquet holds it
        if exp[i].split(" | ")[1] != link_cell(source):
            fail("line {}: the rule gives {!r}".format(i + 1, link_cell(source)))
        else:
            n_lab += 1
            covered.add(i)
    print("  4.7 Link cell rule (M -> P): {} S3.25 pair labels = expected".format(n_lab))

missing = [i + 1 for i in changed if i not in covered]
print("changed lines covered by an instantiated spec text: {} of {}; not covered: {}".format(
    len([i for i in changed if i in covered]), len(changed), missing))
if missing:
    fail("changed lines not produced by a checked spec text")

# ---- 4. Number tokens of the changed lines (regex of OUT\skeptic\k09_number_tokens.py).
NUM = re.compile(r"[−\-]?\d+(?:[.,]\d+)*%?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+|[ᵃᵇᶜᵈ†‡§×<]")
quoted = [t for _, o, n in ITEMS for t in (o, n) if t] + [anchor]
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

# ---- 5. cells.json entries against the expected version 3.
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
        if exp[i].count(e["printed"]) != agreed[i].count(e["printed"]):
            fail("line {}: token {!r} occurs a different number of times".format(e["line"], e["printed"]))
    else:
        fail("entry on line {}: its cell is not on the expected version-3 line".format(e["line"]))
on_changed = collections.Counter(e["line"] for e in E if e["line"] - 1 in changed)
print("cells.json: {} entries; on changed lines: {}; entries whose cell (a whole note line) changes: {}".format(
    len(E), dict(on_changed), dict(moved)))
print("RESULT:", "every NEW text of the order is what the version-3 spec prints" if ok else "FAILED")
sys.exit(0 if ok else 1)
