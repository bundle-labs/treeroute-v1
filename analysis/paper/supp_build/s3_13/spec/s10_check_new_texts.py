# s10_check_new_texts.py - version 2 of TABLE_SPEC.md (2026-11-17). Read-only check that a builder who follows the
# version-2 spec prints each NEW text of the change order exactly where the order says.
# 1. Builds the expected version-2 lines from the agreed version-1 tables (OUT\reconcile\tables_agreed.md) and the
#    OLD/NEW texts of OUT\_brief\fix_order_v2.md (parsed from its code spans; wrapped lines joined by one space).
# 2. Instantiates the changed fixed texts of TABLE_SPEC.md (fenced blocks; the S3.23-S3.27 caption template, whose
#    placeholders are read off the version-1 captions with the version-1 template; the two notes with data
#    placeholders, likewise; the E10 and S3.22 constant cells) and compares them with those expected lines.
# Prints only. Run from this folder: py -3.9 -I -B s10_check_new_texts.py
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
OUT = "../"


def rd(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


order = rd(OUT + "_brief/fix_order_v2.md")
agreed = rd(OUT + "reconcile/tables_agreed.md").split("\n")
S1 = rd("TABLE_SPEC_v1.md").split("\n")
S2 = rd("TABLE_SPEC.md").split("\n")
ok = True


def fail(m):
    global ok
    ok = False
    print("FAIL:", m)


def norm(s):
    return re.sub(r"[ \t]*\n[ \t]*", " ", s)


spans = [(m.group(1), norm(m.group(2))) for m in re.finditer(r"(OLD|NEW)[^`:\n]*:\s+`(.*?)`", order, re.S)]
old = [t for k, t in spans if k == "OLD"]
new = [t for k, t in spans if k == "NEW"]
c9 = norm(re.search(r"Add, after its first sentence: `(.*?)`", order, re.S).group(1))
c4note = norm(re.search(r"before the line that starts `ᵃ Failed`: `(.*?)`", order, re.S).group(1))
print("order: {} OLD texts, {} NEW texts, plus the C9 sentence and the C4 note line".format(len(old), len(new)))
# The order of the code spans in fix_order_v2.md:
# NEW: 0 T9 caption, 1 S3.23/24/26, 2 S3.25/27, 3 S3.29, 4 C2a, 5 C2b, 6 C3a, 7 C3b, 8 baselines row, 9 S3.30 note,
#      10 C5 label, 11 E10, 12 C6 note a, 13 C7, 14 C8
# OLD: 0 T9, 1 S3.23 sentence, 2 S3.29, 3 C2a, 4 C2b, 5 C3a, 6 C3b, 7 baselines, 8 S3.30, 9 C5, 10 E10, 11 C6a,
#      12 C7, 13 C8
if len(new) != 15 or len(old) != 14:
    fail("unexpected number of OLD/NEW texts")

# 1. Expected version-2 lines.
exp = list(agreed)
idx = {"S3.25": None, "S3.27": None}


def rep(i, o, n):
    if exp[i].count(o) != 1:
        fail("line {}: OLD text found {} times: {!r}".format(i + 1, exp[i].count(o), o[:60]))
    exp[i] = exp[i].replace(o, n)


def find(pred):
    return [i for i, ln in enumerate(exp) if pred(ln)]


first = "the nowcast of each problem."
rep(0, first + " ", first + " " + c9 + " ")
rep(find(lambda ln: ln.startswith("**Table 9.**"))[0], old[0], new[0])
for i in find(lambda ln: ln.startswith("**Table S3.2") and "(post hoc)." in ln and old[1] in ln):
    t = re.match(r"\*\*Table (S3\.\d+)", exp[i]).group(1)
    rep(i, old[1], new[2] if t in ("S3.25", "S3.27") else new[1])
rep(find(lambda ln: ln.startswith("**Table S3.29"))[0], old[2], new[3])
rep(find(lambda ln: old[3] in ln)[0], old[3], new[4])
rep(find(lambda ln: old[4] in ln)[0], old[4], new[5])
nd = find(lambda ln: ln.startswith("‡ BARDL reads"))[0]
rep(nd, old[5], new[6])
rep(nd, old[6], new[7])
rep(find(lambda ln: ln == old[7])[0], old[7], new[8])
rep(find(lambda ln: ln == old[8])[0], old[8], new[9])
rep(find(lambda ln: ln.startswith("| " + old[9] + " |"))[0], "| " + old[9] + " |", "| " + new[10] + " |")
rep(find(lambda ln: ln.startswith("| E10 | " + old[10] + " |"))[0], "| E10 | " + old[10] + " |", "| E10 | " + new[11] + " |")
rep(find(lambda ln: old[11] in ln)[0], old[11], new[12])
for i in find(lambda ln: old[12] in ln):
    rep(i, old[12], new[13])
rep(find(lambda ln: old[13] in ln)[0], old[13], new[14])
crw = find(lambda ln: ln.startswith("| Coral bleaching | CRW Outlook |"))
if len(crw) != 1:
    fail("CRW Outlook row not found once")
del exp[crw[0]]
fa = find(lambda ln: ln.startswith("ᵃ Failed: the raw model is explained") and "(decision D6)." in ln)[0]
exp.insert(fa, c4note)
changed = [i for i in range(max(len(exp), len(agreed))) if i >= len(agreed) or i >= len(exp) or exp[i] != agreed[i]]
print("expected version 2 of tables.md: {} lines (version 1: {}); lines that differ from version 1 (1-based): {}".format(
    len(exp), len(agreed), [i + 1 for i in changed]))
EXP = set(exp)


# 2. The spec's fenced blocks.
def blocks(lines):
    out, inside, cur = [], False, None
    for ln in lines:
        if ln.startswith("```"):
            if inside:
                out.append(cur)
                inside = False
            else:
                inside, cur = True, []
        elif inside:
            cur.append(ln)
    return out


B1, B2 = blocks(S1), blocks(S2)


def blk(blist, first_prefix):
    hits = [b for b in blist if b and b[0].startswith(first_prefix)]
    if len(hits) > 1:
        hits = [b for b in hits if b[0] == first_prefix and any(x.startswith("ᵈ Coral bleaching's table") for x in b)]
    if len(hits) != 1:
        fail("block starting {!r} found {} times".format(first_prefix, len(hits)))
        return []
    return hits[0]


checked = 0
for pre in ("<!-- Draft tables", "**Table 9.**", "| Problem | Rival |", "Panel b lists", "ᵃ E5 is informational",
            "ᵃ Burned fraction: every rival explains in another link (LightGBM, the random forest and Ridge in log(y + c), the Tweedie booster in log μ), and Ridge also failed its skill guard, so the main set is treeroute v1 alone. W needs two models and is undefined, and the cells that need a rival are empty (–): agreement between treeroute v1 and a rival cannot separate the link from the model there.",
            "Sign agreement: of the players", "**Table S3.29", "Coral bleaching: B1 is not defined"):
    for ln in blk(B2, pre):
        checked += 1
        if ln not in EXP:
            fail("spec v2 block line not in the expected version 2: {!r}".format(ln[:90]))


def to_regex(template):
    seen, out, pos = set(), [], 0
    for m in re.finditer(r"\{([A-Za-z][A-Za-z0-9_]*)\}", template):
        out.append(re.escape(template[pos:m.start()]))
        name = m.group(1)
        out.append("(?P={})".format(name) if name in seen else "(?P<{}>.*?)".format(name))
        seen.add(name)
        pos = m.end()
    out.append(re.escape(template[pos:]))
    return re.compile("^" + "".join(out) + "$")


def fill(template, values):
    return re.sub(r"\{([A-Za-z][A-Za-z0-9_]*)\}", lambda m: values[m.group(1)], template)


# 2a. S3.20 notes (note a constant, note b with data placeholders).
b1 = blk(B1, "ᵃ Rows checked")
b2 = blk(B2, "ᵃ Rows checked")
for t1, t2 in zip(b1, b2):
    rx = to_regex(t1)
    hits = [ln for ln in agreed if rx.match(ln)]
    if len(hits) != 1:
        fail("v1 template not matched once in the v1 tables: {!r}".format(t1[:60]))
        continue
    got = fill(t2, rx.match(hits[0]).groupdict())
    checked += 1
    if got not in EXP:
        fail("S3.20 note, instantiated v2 text not in the expected version 2: {!r}".format(got[:90]))
# 2b. The NDVI footnote.
t1, t2 = blk(B1, "‡ BARDL reads")[0], blk(B2, "‡ BARDL reads")[0]
rx = to_regex(t1)
hits = [ln for ln in agreed if rx.match(ln)]
got = fill(t2, rx.match(hits[0]).groupdict()) if len(hits) == 1 else None
checked += 1
if got not in EXP:
    fail("NDVI footnote: instantiated v2 text not in the expected version 2")
# 2c. The S3.23-S3.27 caption template and {shares_sentence}.
t1, t2 = blk(B1, "**Table S3.{nn}")[0], blk(B2, "**Table S3.{nn}")[0]
bul = [i for i, ln in enumerate(S2) if ln.startswith("- `{shares_sentence}`")][0]
vals = re.findall(r"^  `(.*)`;?$", "\n".join(S2[bul + 1:bul + 5]), re.M)
if len(vals) != 2:
    fail("the two {shares_sentence} values not found")
else:
    if vals[0] != new[2] or vals[1] != new[1]:
        fail("{shares_sentence} values differ from the order's NEW texts")
    rx = to_regex(t1)
    n_cap = 0
    for ln in agreed:
        m = rx.match(ln)
        if m:
            n_cap += 1
            d = m.groupdict()
            d["shares_sentence"] = vals[0] if d["nn"] in ("25", "27") else vals[1]
            got = fill(t2, d)
            checked += 1
            if got not in EXP:
                fail("caption of S3.{}: instantiated v2 text not in the expected version 2".format(d["nn"]))
            else:
                print("  caption S3.{} ok".format(d["nn"]))
    if n_cap != 5:
        fail("the version-1 caption template matched {} version-1 captions, not 5".format(n_cap))
# 2d. Constant cells outside fenced blocks: E10's "What it checks" and the S3.22 row label.
e10 = [ln for ln in S2 if ln.startswith("| `E10` | `")][0].split("` | `")[1].split("` |")[0]
lab = [ln for ln in S2 if ln.startswith("| `Guard-passing")][0].split("`")[1]
checked += 2
if e10 != new[11]:
    fail("E10 text differs from the order")
if lab != new[10]:
    fail("S3.22 row label differs from the order")
# 3. Every expected changed line is produced by a checked spec text (by membership).
print("spec texts checked against the expected version 2: {}".format(checked))
print("RESULT:", "every NEW text of the order is what the version-2 spec prints" if ok else "FAILED")
sys.exit(0 if ok else 1)
