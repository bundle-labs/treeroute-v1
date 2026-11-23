# s22_diff_v4_v5.py - version 5 of TABLE_SPEC.md (2026-11-17). Diffs TABLE_SPEC_v4.md (version 4, kept byte for
# byte) with TABLE_SPEC.md (version 5) and confirms that every changed line belongs to a listed change of
# OUT\_brief\fix_order_v5.md (V5-1 to V5-5) or to the new section 12 and its entry in the contents line (S12).
# How (as s18_diff_v3_v4.py did for version 4): the edits of version 5 are listed below as (change id, old text, new
# text). The script ties each edit to the order: its old text must hold one of the order's OLD code spans and its new
# text must be the old text with that span replaced by the order's NEW span (V5-5: the sentence the order adds,
# inserted after the Version 4 sentence); every OLD/NEW pair of the order must be used. It then applies the edits to
# version 4 (each old text must occur exactly once there, and no two may overlap) and requires the result, followed by
# section 12, to equal version 5 byte for byte. It lists every changed line (difflib) with the change it belongs to,
# checks that no line of sections 0 to 11 was added or dropped, checks the fenced-block structure (same number of
# blocks; which blocks changed and whether the first 24 characters of their first line changed), lists the digits and
# placeholders each change removes or adds, and checks that the copies of versions 1 to 4 are intact.
# Read-only; prints only. Run from this folder: py -3.9 -I -B s22_diff_v4_v5.py
import collections
import difflib
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
V4_PATH = os.path.join(HERE, "TABLE_SPEC_v4.md")
V5_PATH = os.path.join(HERE, "TABLE_SPEC.md")
ORDER_PATH = os.path.join(OUT, "_brief", "fix_order_v5.md")
KEPT = {"TABLE_SPEC_v1.md": "979be5ed64b908402b8c69ad60eb0b07e48f1b10b8cacaadb7049fefff7cf9fb",
        "TABLE_SPEC_v2.md": "2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02",
        "TABLE_SPEC_v3.md": "573cc04e149d8d921e41aff285938ecb8a3b819f2d1c020b1f8ad816ead8da31",
        "TABLE_SPEC_v4.md": "8697d7a7f3d01743d1061c1c006c3a9107284cd50695d4f8f695a331a3984885"}
S12_HEAD = "\n---\n\n## 12. Version 5 (2026-11-17)\n"
LISTED = ["V5-1", "V5-2", "V5-3", "V5-4", "V5-5", "S12"]
V4_SENTENCE_END = "as paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed."

EDITS = [
    ("S12", r"""8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17).""",
     r"""8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17) - 11 Version 4 (2026-11-17) - 12 Version 5 (2026-11-17)."""),
    ("V5-5", r"""as paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed. Built from the stored values""",
     r"""as paper/supp_build/s3_13/spec/CHANGES_v4.md lists; no number changed. Version 5 (2026-11-17, after the fourth check): three untrue texts corrected and one wording made exact, as paper/supp_build/s3_13/spec/CHANGES_v5.md lists; no number changed. Built from the stored values"""),
    ("V5-2", r"""(forest loss, annual: all of them; coral bleaching: survey visits at other locations).""",
     r"""(forest loss, annual: all of them; coral bleaching: a pool of earlier nearby survey visits)."""),
    ("V5-1", r"""local drivers, context and calendar (the router context), and the seasonal normal.""",
     r"""local drivers, context and calendar (the router-context columns that copy no tree input), and the seasonal normal."""),
    ("V5-2", r"""coral bleaching: the survey visit's saved router fit rows, a pool of survey visits at other locations.""",
     r"""coral bleaching: the survey visit's saved router fit rows, a pool of earlier nearby survey visits."""),
    ("V5-4", r"""| `E3m` | `a moved dataset package file has the content, size and modification time that every lock recording it at its old path holds (path map)` |""",
     r"""| `E3m` | `a moved dataset package file has the content SHA-256, size and modification time that every lock recording it at its old path holds (path map)` |"""),
    ("V5-3", r"""| `E5ᵃ` | `tree-bank fingerprint over every tree array (informational)` |""",
     r"""| `E5ᵃ` | `fingerprint of the tree bank, the correctors and the placebos, over every node array (informational)` |"""),
    ("V5-3", r"""ᵃ E5 is informational: the rebuilt tree bank's fingerprint differs from the run's""",
     r"""ᵃ E5 is informational: the rebuilt fingerprint of the tree bank, correctors and placebos differs from the run's"""),
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
raw4, t4 = read(V4_PATH)
raw5, t5 = read(V5_PATH)
print("TABLE_SPEC.md     sha256", hashlib.sha256(raw5).hexdigest())
for name, raw in (("v4", raw4), ("v5", raw5)):
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\t" in raw or not raw.endswith(b"\n") \
            or raw.endswith(b"\n\n"):
        fail(name + ": not UTF-8 without BOM, LF only, no tab, one final LF")
    if re.search(rb" \n", raw):
        fail(name + ": a line ends with a space")

# 0. The order's OLD and NEW code spans (wrapped lines joined by one space) and the sentence V5-5 adds.
_, order = read(ORDER_PATH)


def norm(s):
    return re.sub(r"[ \t]*\n[ \t]*", " ", s)


spans_o = [(m.group(1), norm(m.group(2))) for m in re.finditer(r"(OLD|NEW)[^`:\n]*:\s+`(.*?)`", order, re.S)]
OLD = [t for k, t in spans_o if k == "OLD"]
NEW = [t for k, t in spans_o if k == "NEW"]
ADDS = [norm(m.group(1)) for m in re.finditer(r"after the Version 4 sentence, add `(.*?)`", order, re.S)]
print("order: {} OLD spans, {} NEW spans, {} added sentence".format(len(OLD), len(NEW), len(ADDS)))
if len(OLD) != 6 or len(NEW) != 6 or len(ADDS) != 1 or [k for k, _ in spans_o] != ["OLD", "NEW"] * 6:
    fail("the order should give 6 OLD/NEW pairs, in that alternation, and one added sentence")
PAIRS = list(zip(OLD, NEW))
used = collections.Counter()
for cid, old, new in EDITS:
    if cid == "S12":
        continue
    if cid == "V5-5":
        if ADDS and new != old.replace(V4_SENTENCE_END, V4_SENTENCE_END + " " + ADDS[0], 1):
            fail("V5-5: the edit is not the order's sentence inserted after the Version 4 sentence")
        continue
    hits = [k for k, (o, n) in enumerate(PAIRS) if o in old and old.replace(o, n, 1) == new]
    if len(hits) != 1:
        fail("{}: the edit matches {} OLD/NEW pairs of the order, not 1: {!r}".format(cid, len(hits), old[:60]))
    for k in hits:
        used[k] += 1
for k, (o, n) in enumerate(PAIRS):
    if used[k] != 1:
        fail("order pair {} ({!r}) is used by {} edits, not 1".format(k + 1, o[:50], used[k]))
print("edits tied to the order: {} of {} OLD/NEW pairs used once each; V5-5 inserts the order's sentence".format(
    sum(1 for k in range(len(PAIRS)) if used[k] == 1), len(PAIRS)))

# 1. Replay the listed edits on version 4.
spans = []
for cid, old, new in EDITS:
    if cid not in LISTED:
        fail("edit with an unlisted id " + cid)
    if "\n" in old or "\n" in new:
        fail(cid + ": an edit spans lines (version 5 changes text inside lines only)")
    n = t4.count(old)
    if n != 1:
        fail("{}: the old text occurs {} times in version 4: {!r}".format(cid, n, old[:70]))
        continue
    s = t4.index(old)
    spans.append((s, s + len(old), cid, old, new))
spans.sort()
for a, b in zip(spans, spans[1:]):
    if a[1] > b[0]:
        fail("overlapping edits {} and {}".format(a[2], b[2]))
parts, pos, v4spans, v5spans = [], 0, [], []
for s, e, cid, old, new in spans:
    parts.append(t4[pos:s])
    start5 = sum(len(x) for x in parts)
    parts.append(new)
    v4spans.append((s, e, cid))
    v5spans.append((start5, start5 + len(new), cid))
    pos = e
parts.append(t4[pos:])
expected = "".join(parts)
replay_ok = len(spans) == len(EDITS)
if not t5.startswith(expected):
    replay_ok = False
    k = next((i for i, (x, y) in enumerate(zip(expected, t5)) if x != y), min(len(expected), len(t5)))
    fail("version 5 is not version 4 with the listed edits; first difference at character {}: v5 has {!r}".format(
        k, t5[max(0, k - 40):k + 40]))
tail = t5[len(expected):]
if not tail.startswith(S12_HEAD):
    replay_ok = False
    fail("the text after the listed edits does not start with section 12's heading")
v5spans.append((len(expected), len(t5), "S12"))
print("replay: {} edits applied to version 4; version 5 = that text + section 12 ({} characters): {}".format(
    len(spans), len(tail), "yes" if replay_ok else "NO"))


# 2. Every changed line (difflib) belongs to a listed change.
def line_starts(text):
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return starts


L4, L5 = t4.split("\n")[:-1], t5.split("\n")[:-1]  # both end with one "\n": no empty last line
n_body = expected.count("\n")
print("lines: version 4 {}, version 5 {} (sections 0-11: {}, section 12 with its rule: {}, lines {}-{})".format(
    len(L4), len(L5), n_body, len(L5) - n_body, n_body + 1, len(L5)))
if n_body != len(L4):
    fail("sections 0 to 11 gained or lost lines")
st4, st5 = line_starts(t4), line_starts(t5)


def owner(spans_, starts, lineno, text_len):
    a = starts[lineno - 1]
    b = starts[lineno] if lineno < len(starts) else text_len
    hit = [cid for (s, e, cid) in spans_ if s < b and e > a or (s == e == a)]
    if not hit and b - a <= 1:
        # a blank line next to an edit: difflib may pair the edit's own blank line with the old one
        hit = [cid for (s, e, cid) in spans_ if s <= b and e >= a]
    return sorted(set(hit))


per = collections.OrderedDict((c, {"v4": [], "v5": []}) for c in LISTED)
sm = difflib.SequenceMatcher(a=L4, b=L5, autojunk=False)
n_changed4 = n_changed5 = 0
same_index = True
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    for i in range(i1, i2):
        n_changed4 += 1
        who = owner(v4spans, st4, i + 1, len(t4))
        if not who:
            fail("version-4 line {} changed and belongs to no listed change: {!r}".format(i + 1, L4[i][:80]))
        if len(who) > 1:
            print("  version-4 line {} holds {} changes: {}".format(i + 1, len(who), who))
        for c in who:
            per[c]["v4"].append(i + 1)
    for j in range(j1, j2):
        n_changed5 += 1
        who = owner(v5spans, st5, j + 1, len(t5))
        if not who:
            fail("version-5 line {} changed and belongs to no listed change: {!r}".format(j + 1, L5[j][:80]))
        if len(who) > 1:
            print("  version-5 line {} holds {} changes: {}".format(j + 1, len(who), who))
        for c in who:
            per[c]["v5"].append(j + 1)
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


print("changed lines: {} of version 4 (replaced), {} of version 5 (replacing or new)".format(n_changed4, n_changed5))
for cid, d in per.items():
    print("  {:5s} version-4 lines {}".format(cid, ranges(d["v4"])))
    print("  {:5s} version-5 lines {}".format("", ranges(d["v5"])))
    if not d["v4"] and not d["v5"]:
        fail(cid + " is listed but changed no line")
body4 = sorted(set(ln for d in per.values() for ln in d["v4"]))
body5 = sorted(set([ln for c, d in per.items() if c != "S12" for ln in d["v5"]]
                   + [ln for ln in per["S12"]["v5"] if ln <= n_body]))
if body4 != body5 or not same_index:
    fail("a changed line of sections 0 to 11 moved")
else:
    print("sections 0 to 11: every changed line keeps its line number ({} lines: {})".format(
        len(body4), ranges(sorted(body4))))


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


B4, B5 = blocks(L4), blocks(L5)
print("fenced blocks: version 4 {}, version 5 {}".format(len(B4), len(B5)))
if len(B4) != len(B5):
    fail("the number of fenced blocks changed")
fenced5 = set()
for k, (x, y) in enumerate(zip(B4, B5), 1):
    fenced5.update(range(y["open"] + 1, y["open"] + 1 + len(y["lines"])))
    if x["open"] != y["open"]:
        fail("block {} moved from line {} to line {}".format(k, x["open"], y["open"]))
    if x["lines"] != y["lines"]:
        f4 = x["lines"][0] if x["lines"] else ""
        f5 = y["lines"][0] if y["lines"] else ""
        if len(x["lines"]) != len(y["lines"]):
            fail("block {} changed its number of lines".format(k))
        same24 = f4[:24] == f5[:24]
        if not same24:
            fail("block {}: the first 24 characters of its first line changed".format(k))
        changed_in = [d + 1 for d, (a, b) in enumerate(zip(x["lines"], y["lines"])) if a != b]
        print("  block {:2d} (line {}): {} lines, lines {} of it changed; first line {}; first 24 characters {}".format(
            k, y["open"], len(y["lines"]), changed_in, "unchanged" if f4 == f5 else "CHANGED",
            "same" if same24 else "DIFFER: {!r} -> {!r}".format(f4[:44], f5[:44])))
outside = sorted(ln for ln in body4 if ln not in fenced5)
print("changed lines outside fenced blocks (rules, constant cells, prose): {}".format(ranges(outside)))

# 4. Digits and placeholders removed or added by each change.
NUM = re.compile(r"\d[\d,.]*\d|\d")
PH = re.compile(r"\{[a-z][a-z0-9_]*\}")
for cid in LISTED:
    olds = [old for (c, old, new) in EDITS if c == cid]
    news = [new for (c, old, new) in EDITS if c == cid]
    if cid == "S12":
        print("  S12   adds section 12 (its numbers are line and block numbers, ids and hashes) and its contents entry")
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
