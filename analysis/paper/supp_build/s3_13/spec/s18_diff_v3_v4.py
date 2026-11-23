# s18_diff_v3_v4.py - version 4 of TABLE_SPEC.md (2026-11-17). Diffs TABLE_SPEC_v3.md (version 3, kept byte for
# byte) with TABLE_SPEC.md (version 4) and confirms that every changed line belongs to a listed change of
# OUT\_brief\fix_order_v4.md (V4-1 to V4-13) or to the new section 11 and its entry in the contents line (S11).
# How (as s13_diff_v2_v3.py did for version 3): the edits of version 4 are listed below as (change id, old text, new
# text). The script applies them to version 3 (each old text must occur exactly once there, and no two may overlap)
# and requires the result, followed by section 11, to equal version 4 byte for byte. It then lists every changed line
# (difflib) with the change it belongs to, checks that no line of sections 0 to 10 was added or dropped, checks the
# fenced-block structure (same number of blocks; which blocks changed and whether their first line changed), lists
# the digits and placeholders each change removes or adds, and checks that the copies of versions 1 to 3 are intact.
# Read-only; prints only. Run from this folder: py -3.9 -I -B s18_diff_v3_v4.py
import collections
import difflib
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
V3_PATH = os.path.join(HERE, "TABLE_SPEC_v3.md")
V4_PATH = os.path.join(HERE, "TABLE_SPEC.md")
KEPT = {"TABLE_SPEC_v1.md": "979be5ed64b908402b8c69ad60eb0b07e48f1b10b8cacaadb7049fefff7cf9fb",
        "TABLE_SPEC_v2.md": "2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02",
        "TABLE_SPEC_v3.md": "573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31"}
S11_HEAD = "\n---\n\n## 11. Version 4 (2026-11-17)\n"
LISTED = ["V4-1", "V4-2", "V4-3", "V4-4", "V4-5", "V4-6", "V4-7", "V4-8", "V4-9", "V4-10", "V4-11", "V4-12",
          "V4-13", "S11"]  # V4-13 also corrects CHANGES_v3.md, outside this file (checked by s21)

EDITS = [
    ("S11", r"""8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17).""",
     r"""8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17)."""),
    ("V4-13", r"""as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed. Built from the stored values""",
     r"""as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed. Version 4 (2026-11-17, after the third check): captions, notes, a column header, a row label, cells and a source comment reworded, as paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed. Built from the stored values"""),
    ("V4-3", r"""(forest loss, annual: all of them; coral bleaching: other sites' survey visits).""",
     r"""(forest loss, annual: all of them; coral bleaching: survey visits at other locations)."""),
    ("V4-4", r"""local drivers, context and calendar, and the seasonal normal.""",
     r"""local drivers, context and calendar (the router context), and the seasonal normal."""),
    ("V4-12", r"""paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d""",
     r"""paper/draft/03_protocol.md Sections 3.3 and 3.4, paper/draft/tables/table_3.md note d"""),
    ("V4-7", r"""| Problem | Rival | Why it has no SHAP value |""",
     r"""| Problem | Rival or naive baseline | Why it has no SHAP value |"""),
    ("V4-3", r"""ᵇ Coral bleaching: a location is a survey visit.""",
     r"""ᵇ Coral bleaching: the column counts survey visits, the engine's unit there; a location is a reef site."""),
    ("V4-3", r"""a pool of other sites' survey visits.""",
     r"""a pool of survey visits at other locations."""),
    ("V4-5", r"""("plain answers" if R `table_kind` == plain,""",
     r"""("plain tree answers" if R `table_kind` == plain,"""),
    ("V4-2", r"""| `E3a` | `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)` | `passed` |""",
     r"""| `E3a` | `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists (coral bleaching: the static file list only), tree inputs)` | `passed` |"""),
    ("V4-1", r"""| `E3m` | `a moved dataset package file has the content, size and time that the run's locks record (path map)` |""",
     r"""| `E3m` | `a moved dataset package file has the content, size and modification time that every lock recording it at its old path holds (path map)` |"""),
    ("V4-10", r"""| `E3` | `dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied` | `passed` |""",
     r"""| `E3` | `the dataset package fingerprint, the settings that the written rules set and the run fingerprint equal the manifest's, after the written rules are applied` | `passed` |"""),
    ("V4-6", r"""| `E5ᵃ` | `bank fingerprint over every tree array (informational)` |""",
     r"""| `E5ᵃ` | `tree-bank fingerprint over every tree array (informational)` |"""),
    ("V4-11", r"""| `E8` | `kept predictions, pre-clip and clipped, on every test row of every sampled location` |""",
     r"""| `E8` | `the adopted arm's saved predictions, pre-clip and clipped, on every test row of every sampled location (coral bleaching: every test survey visit)` |"""),
    ("V4-6", r"""ᵃ E5 is informational: the rebuilt bank's fingerprint differs from the run's""",
     r"""ᵃ E5 is informational: the rebuilt tree bank's fingerprint differs from the run's"""),
    ("V4-8", r"""| `Rivals in another link that passed their skill guard` | AW4 `cross_link_models` as a model list |""",
     r"""| `Rivals that explain in another link and passed their skill guard` | AW4 `cross_link_models` as a model list |"""),
    ("V4-9", r"""(the players to which either run gives more than 10⁻¹² of its total)""",
     r"""(the players to which either run gives more than 10⁻¹² of its total mean absolute SHAP value, with each region weighted equally)"""),
]

ok = True


def fail(msg):
    global ok
    ok = False
    print("FAIL:", msg)


def read(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, raw.decode("utf-8")


for name, want in KEPT.items():
    raw, _ = read(os.path.join(HERE, name))
    got = hashlib.sha256(raw).hexdigest()
    print("{:17s} sha256 {} ({})".format(name, got, "as kept" if got == want else "CHANGED"))
    if got != want:
        fail(name + " is not the kept copy")
raw3, t3 = read(V3_PATH)
raw4, t4 = read(V4_PATH)
print("TABLE_SPEC.md     sha256", hashlib.sha256(raw4).hexdigest())
for name, raw in (("v3", raw3), ("v4", raw4)):
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\t" in raw or not raw.endswith(b"\n") \
            or raw.endswith(b"\n\n"):
        fail(name + ": not UTF-8 without BOM, LF only, no tab, one final LF")
    if re.search(rb" \n", raw):
        fail(name + ": a line ends with a space")

# 1. Replay the listed edits on version 3.
spans = []
for cid, old, new in EDITS:
    if cid not in LISTED:
        fail("edit with an unlisted id " + cid)
    if "\n" in old or "\n" in new:
        fail(cid + ": an edit spans lines (version 4 changes text inside lines only)")
    n = t3.count(old)
    if n != 1:
        fail("{}: the old text occurs {} times in version 3: {!r}".format(cid, n, old[:70]))
        continue
    s = t3.index(old)
    spans.append((s, s + len(old), cid, old, new))
spans.sort()
for a, b in zip(spans, spans[1:]):
    if a[1] > b[0]:
        fail("overlapping edits {} and {}".format(a[2], b[2]))
parts, pos, v3spans, v4spans = [], 0, [], []
for s, e, cid, old, new in spans:
    parts.append(t3[pos:s])
    start4 = sum(len(x) for x in parts)
    parts.append(new)
    v3spans.append((s, e, cid))
    v4spans.append((start4, start4 + len(new), cid))
    pos = e
parts.append(t3[pos:])
expected = "".join(parts)
replay_ok = len(spans) == len(EDITS)
if not t4.startswith(expected):
    replay_ok = False
    k = next((i for i, (x, y) in enumerate(zip(expected, t4)) if x != y), min(len(expected), len(t4)))
    fail("version 4 is not version 3 with the listed edits; first difference at character {}: v4 has {!r}".format(
        k, t4[max(0, k - 40):k + 40]))
tail = t4[len(expected):]
if not tail.startswith(S11_HEAD):
    replay_ok = False
    fail("the text after the listed edits does not start with section 11's heading")
v4spans.append((len(expected), len(t4), "S11"))
print("replay: {} edits applied to version 3; version 4 = that text + section 11 ({} characters): {}".format(
    len(spans), len(tail), "yes" if replay_ok else "NO"))


# 2. Every changed line (difflib) belongs to a listed change.
def line_starts(text):
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return starts


L3, L4 = t3.split("\n")[:-1], t4.split("\n")[:-1]  # both end with one "\n": no empty last line
n_body = expected.count("\n")
print("lines: version 3 {}, version 4 {} (sections 0-10: {}, section 11 with its rule: {})".format(
    len(L3), len(L4), n_body, len(L4) - n_body))
if n_body != len(L3):
    fail("sections 0 to 10 gained or lost lines")
st3, st4 = line_starts(t3), line_starts(t4)


def owner(spans_, starts, lineno, text_len):
    a = starts[lineno - 1]
    b = starts[lineno] if lineno < len(starts) else text_len
    hit = [cid for (s, e, cid) in spans_ if s < b and e > a or (s == e == a)]
    if not hit and b - a <= 1:
        # a blank line next to an edit: difflib may pair the edit's own blank line with the old one
        hit = [cid for (s, e, cid) in spans_ if s <= b and e >= a]
    return sorted(set(hit))


per = collections.OrderedDict((c, {"v3": [], "v4": []}) for c in LISTED)
sm = difflib.SequenceMatcher(a=L3, b=L4, autojunk=False)
n_changed3 = n_changed4 = 0
same_index = True
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    for i in range(i1, i2):
        n_changed3 += 1
        who = owner(v3spans, st3, i + 1, len(t3))
        if not who:
            fail("version-3 line {} changed and belongs to no listed change: {!r}".format(i + 1, L3[i][:80]))
        if len(who) > 1:
            print("  version-3 line {} holds {} changes: {}".format(i + 1, len(who), who))
        for c in who:
            per[c]["v3"].append(i + 1)
    for j in range(j1, j2):
        n_changed4 += 1
        who = owner(v4spans, st4, j + 1, len(t4))
        if not who:
            fail("version-4 line {} changed and belongs to no listed change: {!r}".format(j + 1, L4[j][:80]))
        if len(who) > 1:
            print("  version-4 line {} holds {} changes: {}".format(j + 1, len(who), who))
        for c in who:
            per[c]["v4"].append(j + 1)
    if tag == "replace" and (i1 != j1 or i2 - i1 != j2 - j1):
        same_index = False


def ranges(nums):
    out, run = [], []
    for n in nums:
        if run and n == run[-1] + 1:
            run.append(n)
        else:
            if run:
                out.append(run)
            run = [n]
    if run:
        out.append(run)
    return ", ".join(str(r[0]) if len(r) == 1 else "{}-{}".format(r[0], r[-1]) for r in out) or "-"


print("changed lines: {} of version 3 (replaced), {} of version 4 (replacing or new)".format(n_changed3, n_changed4))
for cid, d in per.items():
    print("  {:5s} version-3 lines {}".format(cid, ranges(d["v3"])))
    print("  {:5s} version-4 lines {}".format("", ranges(d["v4"])))
    if not d["v3"] and not d["v4"]:
        fail(cid + " is listed but changed no line")
body3 = sorted(set(ln for d in per.values() for ln in d["v3"]))
body4 = sorted(set([ln for c, d in per.items() if c != "S11" for ln in d["v4"]]
                   + [ln for ln in per["S11"]["v4"] if ln <= n_body]))
if body3 != body4 or not same_index:
    fail("a changed line of sections 0 to 10 moved")
else:
    print("sections 0 to 10: every changed line keeps its line number ({} lines: {})".format(
        len(body3), ranges(sorted(body3))))


# 3. Fenced blocks: same number; which blocks changed; whether their first line changed.
def blocks(lines):
    out, inside, cur = [], False, None
    for k, ln in enumerate(lines, 1):
        if ln.startswith("```"):
            if inside:
                out.append(cur)
                inside = False
            else:
                inside, cur = True, {"open": k, "lines": []}
        elif inside:
            cur["lines"].append(ln)
    if inside:
        fail("an unclosed fenced block")
    return out


B3, B4 = blocks(L3), blocks(L4)
print("fenced blocks: version 3 {}, version 4 {}".format(len(B3), len(B4)))
if len(B3) != len(B4):
    fail("the number of fenced blocks changed")
fenced4 = set()
for k, (x, y) in enumerate(zip(B3, B4), 1):
    fenced4.update(range(y["open"] + 1, y["open"] + 1 + len(y["lines"])))
    if x["open"] != y["open"]:
        fail("block {} moved from line {} to line {}".format(k, x["open"], y["open"]))
    if x["lines"] != y["lines"]:
        f3 = x["lines"][0] if x["lines"] else ""
        f4 = y["lines"][0] if y["lines"] else ""
        if len(x["lines"]) != len(y["lines"]):
            fail("block {} changed its number of lines".format(k))
        same24 = f3[:24] == f4[:24]
        changed_in = [d + 1 for d, (a, b) in enumerate(zip(x["lines"], y["lines"])) if a != b]
        print("  block {:2d} (line {}): {} lines, lines {} of it changed; first line {}; first 24 characters {}".format(
            k, y["open"], len(y["lines"]), changed_in, "unchanged" if f3 == f4 else "CHANGED",
            "same" if same24 else "DIFFER: {!r} -> {!r}".format(f3[:44], f4[:44])))
outside = sorted(ln for ln in body3 if ln not in fenced4)
print("changed lines outside fenced blocks (rules, constant cells, prose): {}".format(ranges(outside)))

# 4. Digits and placeholders removed or added by each change.
NUM = re.compile(r"\d[\d,.]*\d|\d")
PH = re.compile(r"\{[a-z][a-z0-9_]*\}")
for cid in LISTED:
    olds = [old for (c, old, new) in EDITS if c == cid]
    news = [new for (c, old, new) in EDITS if c == cid]
    if cid == "S11":
        print("  S11   adds section 11 (its numbers are line and block numbers, ids and hashes) and its contents entry")
        continue
    o, n = collections.Counter(), collections.Counter()
    po, pn = collections.Counter(), collections.Counter()
    for x in olds:
        o.update(NUM.findall(x))
        po.update(PH.findall(x))
    for x in news:
        n.update(NUM.findall(x))
        pn.update(PH.findall(x))
    print("  {:5s} digits removed {} added {}; placeholders removed {} added {}".format(
        cid, dict(o - n), dict(n - o), dict(po - pn), dict(pn - po)))

print("RESULT:", "every changed line belongs to a listed change" if ok else "FAILED")
sys.exit(0 if ok else 1)
