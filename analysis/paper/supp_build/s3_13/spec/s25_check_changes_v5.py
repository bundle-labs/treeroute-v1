# s25_check_changes_v5.py - version 5 of TABLE_SPEC.md (2026-11-17). Read-only check of CHANGES_v5.md (as
# s21_check_changes_v4.py did for CHANGES_v4.md): every fenced text in it is labelled by the paragraph before it and
# is found where its label says:
#   "OLD printed text": in OUT\reconcile\tables_agreed.md (version 4 of tables.md) and in TABLE_SPEC_v4.md, and no
#       longer in TABLE_SPEC.md (version 5);
#   "NEW printed text": in TABLE_SPEC.md and in neither tables_agreed.md nor TABLE_SPEC_v4.md;
#   "v4 spec text": in TABLE_SPEC_v4.md and not in TABLE_SPEC.md;   "v5 spec text": the reverse.
# Every OLD and NEW text of the order OUT\_brief\fix_order_v5.md (and the sentence V5-5 adds) must be quoted under the
# matching label. Also checks: the encoding of CHANGES_v5.md; the SHA-256 and line counts it states; the spec lines it
# names for each NEW text; the table of changed fenced blocks; and the quotes of its last two sections against their
# sources (whitespace runs read as one space, since the sources wrap lines). Prints only.
# Run from this folder: py -3.9 -I -B s25_check_changes_v5.py
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = "D:/treeroute/analysis/shap_v1"


def rd(p):
    with open(p, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8")


rc, ch = rd(os.path.join(HERE, "CHANGES_v5.md"))
r4, s4 = rd(os.path.join(HERE, "TABLE_SPEC_v4.md"))
r5, s5 = rd(os.path.join(HERE, "TABLE_SPEC.md"))
ra, ag = rd(os.path.join(OUT, "reconcile", "tables_agreed.md"))
_, order = rd(os.path.join(OUT, "_brief", "fix_order_v5.md"))
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


def ws(s):
    return re.sub(r"\s+", " ", s)


if rc.startswith(b"\xef\xbb\xbf") or b"\r" in rc or b"\t" in rc or not rc.endswith(b"\n") \
        or rc.endswith(b"\n\n") or re.search(rb" \n", rc):
    fail("CHANGES_v5.md: not UTF-8 without BOM, LF only, no tab, no trailing space, one final LF")
flat = ws(ch)

# 1. Hashes and line counts.
for raw, name in ((r4, "version 4 (TABLE_SPEC_v4.md)"), (r5, "version 5 (TABLE_SPEC.md)")):
    h, n = hashlib.sha256(raw).hexdigest(), raw.count(b"\n")
    if h not in flat:
        fail(name + " SHA-256 not stated in CHANGES_v5.md: " + h)
    if "{:,} lines".format(n) not in flat:
        fail(name + " line count {} not stated".format(n))
    print("{}: sha256 {}..., {} lines".format(name, h[:12], n))
if hashlib.sha256(r4).hexdigest() != "8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885":
    fail("TABLE_SPEC_v4.md is not the version 4 that CHANGES_v4.md states")
ha = hashlib.sha256(ra).hexdigest()
if ha not in flat or "{} lines".format(ra.count(b"\n")) not in flat:
    fail("tables_agreed.md SHA-256 or line count not stated")
print("tables_agreed.md: sha256 {}..., {} lines".format(ha[:12], ra.count(b"\n")))
for name, short in (("TABLE_SPEC_v1.md", "979be5ed...7cf9fb"), ("TABLE_SPEC_v2.md", "2046c58a...ad30f02"),
                    ("TABLE_SPEC_v3.md", "573cc04e...ead8da31")):
    h = hashlib.sha256(rd(os.path.join(HERE, name))[0]).hexdigest()
    a, b = short.split("...")
    if not (h.startswith(a) and h.endswith(b)) or short not in flat:
        fail(name + ": short hash {} not stated or not the file's".format(short))
L5 = s5.split("\n")[:-1]
L4n = s4.count("\n")
if L5[L4n + 3] != "## 12. Version 5 (2026-11-17)" or L5[L4n] != "" or L5[L4n + 1] != "---" \
        or s5.count("\n## 12. ") != 1:
    fail("section 12 does not start right after the 1,423 lines of sections 0 to 11")
for t in ("section 12 is new (v5 L{}-{})".format(L4n + 1, len(L5)), "new L{}-{} (section 12".format(L4n + 1, len(L5))):
    if t not in flat:
        fail("CHANGES_v5.md does not state {!r}".format(t))
print("section 12: v5 L{}-{} (heading at L{})".format(L4n + 1, len(L5), L4n + 4))

# 2. Fenced texts by label.
KINDS = ["OLD printed text", "NEW printed text", "v4 spec text", "v5 spec text"]
lines = ch.split("\n")
blocks, i = [], 0
while i < len(lines):
    if lines[i].startswith("```"):
        j = i + 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        k = i - 1
        while k >= 0 and not lines[k].strip():
            k -= 1
        para = []
        while k >= 0 and lines[k].strip() and not lines[k].startswith("```"):
            para.insert(0, lines[k])
            k -= 1
        blocks.append((i + 1, ws(" ".join(para)), "\n".join(lines[i + 1:j])))
        i = j + 1
    else:
        i += 1
counts, quoted = {}, {"OLD printed text": [], "NEW printed text": []}
for at, label, text in blocks:
    found = [(label.rfind(x), x) for x in KINDS if x in label]
    if not found:
        fail("line {}: block without a label: {!r}".format(at, label[-80:]))
        continue
    kind = max(found)[1]
    counts[kind] = counts.get(kind, 0) + 1
    if kind == "OLD printed text":
        good = text in ag and text in s4 and text not in s5
    elif kind == "NEW printed text":
        good = text in s5 and text not in ag and text not in s4
    elif kind == "v4 spec text":
        good = text in s4 and text not in s5
    else:
        good = text in s5 and text not in s4
    if kind in quoted:
        quoted[kind].append(text)
    if not good:
        fail("line {}: {} not found where it should be: {!r}".format(at, kind, text[:80]))
print("fenced texts in CHANGES_v5.md:", len(blocks), counts)


def norm(s):
    return re.sub(r"[ \t]*\n[ \t]*", " ", s)


spans = [(m.group(1), norm(m.group(2))) for m in re.finditer(r"(OLD|NEW)[^`:\n]*:\s+`(.*?)`", order, re.S)]
adds = [norm(m.group(1)) for m in re.finditer(r"after the Version 4 sentence, add `(.*?)`", order, re.S)]
if len(spans) != 12 or len(adds) != 1:
    fail("the order's 6 OLD/NEW pairs and one added sentence not found")
for kind, t in spans + [("NEW", a) for a in adds]:
    lab = kind + " printed text"
    if quoted[lab].count(t) != 1:
        fail("the order's {} text is quoted {} times under '{}': {!r}".format(kind, quoted[lab].count(t), lab, t[:60]))
print("order texts quoted once each under the matching label: {}".format(
    all(quoted[k + " printed text"].count(t) == 1 for k, t in spans + [("NEW", a) for a in adds])))

# 3. The spec lines named for each NEW text (v5 line numbers; sections 0 to 11 keep the v4 numbers).
NEW_AT = {15: ["- 12 Version 5 (2026-11-17)."], 309: adds, 417: [spans[1][1], spans[3][1]], 580: [spans[5][1]],
          679: [spans[11][1]], 682: [spans[7][1]], 693: [spans[9][1]]}
for ln, texts in NEW_AT.items():
    if "L{}".format(ln) not in flat:
        fail("CHANGES_v5.md does not name spec line L{}".format(ln))
    for t in texts:
        if t not in L5[ln - 1]:
            fail("spec line {} does not hold {!r}".format(ln, t[:60]))
print("spec lines named for the NEW texts:", sorted(NEW_AT))


# 4. The table of changed fenced blocks.
def fence_blocks(text):
    out, inside, cur = [], False, None
    for k, ln in enumerate(text.split("\n"), 1):
        if ln.startswith("```"):
            if inside:
                out.append(cur)
                inside = False
            else:
                inside, cur = True, {"open": k, "lines": []}
        elif inside:
            cur["lines"].append(ln)
    return out


F4, F5 = fence_blocks(s4), fence_blocks(s5)
rows = [m.groups() for m in re.finditer(r"^\| (\d+) \| (\d+) \| [^|]+ \| [^|]+ \| ([^|]+) \|$", ch, re.M)]
changed = [k + 1 for k, (x, y) in enumerate(zip(F4, F5)) if x["lines"] != y["lines"]]
if len(F4) != 63 or len(F5) != 63:
    fail("not 63 fenced blocks in both versions")
if sorted(int(b) for b, _, _ in rows) != changed:
    fail("the block table lists {} but the changed blocks are {}".format([b for b, _, _ in rows], changed))
for b, L, first in rows:
    x, y = F4[int(b) - 1], F5[int(b) - 1]
    if not (x["open"] == y["open"] == int(L)):
        fail("block {}: not at line {} in both versions".format(b, L))
    same_first = x["lines"][0] == y["lines"][0]
    if (first.strip() == "unchanged") != same_first or x["lines"][0][:24] != y["lines"][0][:24]:
        fail("block {}: the first-line column {!r} does not fit".format(b, first))
print("block table: blocks {} at lines {}; 63 blocks in both versions".format(
    [int(b) for b, _, _ in rows], [int(L) for _, L, _ in rows]))

# 5. Quotes of the last two sections against their sources.
P = ws(rd(SHAP + "/PROTOCOL.md")[1])
G = ws(rd(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"))[1])
T = ws(rd(SHAP + "/scripts/tr_rebuild.py")[1])
C4 = ws(rd(os.path.join(HERE, "CHANGES_v4.md"))[1])
S5 = ws(s5)
rules = []
for p in ("pm25", "ndvi", "fire"):
    with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
        rules.append(json.load(fh)["gates"]["E3m_recorded_path_map"]["values"]["rule"])
QUOTES = [
    ("PROTOCOL", P, "A context column that is an exact copy of a tree column (the name rule `c__ctx:top5:<v>` -> "
                    "`x__<v>`, then bitwise equality on every explained and background row) is the SAME player"),
    ("PROTOCOL", P, "a duplicate context column is its tree column's variable"),
    ("PROTOCOL", P, "other sites' visits."),
    ("PROTOCOL", P, "its background is a pool of other sites"),
    ("PROTOCOL", P, "E5, informational only: the bank fingerprint (SHA-256 over every node array of every tree, "
                    "corrector and placebo)."),
    ("GLOSSARY", G, "A ridge on a pool of earlier nearby survey visits (coral); it has no normal."),
    ("GLOSSARY", G, "The union of all regions' specialist trees (4,000 to 13,300 trees per problem)."),
    ("tr_rebuild.py", T, "the fingerprint hashes every node array of every tree, corrector and placebo"),
    ("gates.json E3m rule", " | ".join(rules), "content SHA-256, size and mtime equal every freeze-lock record of the "
                                                "recorded path"),
    ("TABLE_SPEC.md", S5, "each problem's tree bank and the sampled locations' routers were rebuilt"),
    ("CHANGES_v4.md", C4, "Version 4: `OUT\\spec\\TABLE_SPEC.md`"),
    ("CHANGES_v4.md", C4, "other sites' visits."),
]
if len(set(rules)) != 1:
    fail("the three E3m rules differ")
for src, text, q in QUOTES:
    if q not in text:
        fail("quote not in {}: {!r}".format(src, q[:70]))
    if q not in flat:
        fail("quote not in CHANGES_v5.md: {!r}".format(q[:70]))
print("source quotes found in their sources and in CHANGES_v5.md: {} of {}".format(
    sum(1 for s, t, q in QUOTES if q in t and q in flat), len(QUOTES)))
print("RESULT:", "every quoted text is where its label says" if ok else "FAILED")
sys.exit(0 if ok else 1)
