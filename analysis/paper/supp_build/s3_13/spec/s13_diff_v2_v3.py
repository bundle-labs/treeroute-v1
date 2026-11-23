# s13_diff_v2_v3.py - version 3 of TABLE_SPEC.md (2026-11-17). Diffs TABLE_SPEC_v2.md (version 2, kept byte for
# byte) with TABLE_SPEC.md (version 3) and confirms that every changed line belongs to a listed change of
# OUT\_brief\fix_order_v3.md (V3-1 to V3-7) or to the new section 10 and its entry in the contents line (S10).
# How (as s07_diff_v1_v2.py did for version 2): the edits of version 3 are listed below as (change id, old text, new
# text). The script applies them to version 2 (each old text must occur exactly once there, and no two may overlap)
# and requires the result, followed by section 10, to equal version 3 byte for byte. It then lists every changed line
# (difflib) with the change it belongs to, checks the fenced-block structure (same number of blocks; which blocks
# changed and whether their first line changed), and lists the digits and placeholders each change removes or adds.
# Read-only; prints only. Run from this folder: py -3.9 -I -B s13_diff_v2_v3.py
import collections
import difflib
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
V2_PATH = os.path.join(HERE, "TABLE_SPEC_v2.md")
V3_PATH = os.path.join(HERE, "TABLE_SPEC.md")
V2_SHA256 = "2046c58a7aa787c15d6cd90b1353a513f6ef28dbff517a4531fa58b09ad30f02"  # TABLE_SPEC.md before any v3 edit
S10_HEAD = "\n---\n\n## 10. Version 3 (2026-11-17)\n"
LISTED = ["V3-1", "V3-2", "V3-3", "V3-4", "V3-5", "V3-6", "V3-7", "S10"]

EDITS = [
    ("S10", r"""8 What the spec writer opened - 9 Version 2 (2026-11-17).""",
     r"""8 What the spec writer opened - 9 Version 2 (2026-11-17) - 10 Version 3 (2026-11-17)."""),
    ("V3-4", r"""| `‡` | BARDL's top-k sets are filled by name order (footnote with the spreads over the three collations) | BB3 |""",
     r"""| `‡` | BARDL's ranking beyond its three variables (nine columns) is filled by name order, and so are its top-k sets where they reach that far (footnote with the spreads over the three collations) | BB3 |"""),
    ("V3-7", r"""Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one row of Table S3.18 b dropped and one note line added; no number changed. Built from""",
     r"""Version 2 (2026-11-17, after the first check): ten captions and notes and three table cells reworded, one row of Table S3.18 b dropped and one note line added; no number changed. Version 3 (2026-11-17, after the second check): captions, notes, labels, cells and source comments reworded, as paper/supp_build/s3_13/spec/CHANGES_v3.md lists; no number changed. Built from"""),
    ("V3-7", r"""every printed number is listed in cells.json beside this file.""",
     r"""every printed data number is listed in cells.json beside this file (the constants of the fixed texts, such as 1,000 and 2,000, are not)."""),
    ("V3-6", r"""   `declined_by_guard`, `<names>` being those models' data names joined by `, `.
4. Per pair and level, sign agreement:""",
     r"""   `declined_by_guard`, `<names>` being those models' data names joined by `, ` (the source label's own words; the
   Link cell of 4.7 prints "declined by its skill guard" in their place, version 3, V3-6).
4. Per pair and level, sign agreement:"""),
    ("V3-1", r"""(forest loss, annual: all of them; coral bleaching: other sites' survey visits). Main set: treeroute v1""",
     r"""(forest loss, annual: all of them; coral bleaching: other sites' survey visits). A variable's importance to a model is its mean absolute SHAP value over the sample, with each region weighted equally; rankings order the variables by importance. Main set: treeroute v1"""),
    ("V3-1", r"""with the rivals' consensus (the mean of their shares).""",
     r"""with the rivals' consensus (the mean of their importance shares)."""),
    ("V3-1", r"""Own-history share: the share of the own-history family (the location's own lagged labels) in the sum of the model's five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares.""",
     r"""Own-history share: the share of the own-history family in the sum of the mean absolute attributions of the model's five families (with each region weighted equally), a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares. The five families are own history (the lags and trailing means of the location's own labels), global indices, local drivers, context and calendar, and the seasonal normal."""),
    ("V3-1", r"""`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says.
""",
     r"""`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says. The region weighting (version 3, V3-1): every mean absolute value in the two bases
weights each region equally. A player's importance (importance.parquet `mean_abs`, by which check 3.5 ranks the
players) is the region-weighted mean of its absolute SHAP values over the sample rows, as PROTOCOL section 8 defines
it ("I_m(j): the region-weighted mean |phi_ij| (each region weighs 1)"), and the model's total is the sum of these
over J; a family's mean absolute attribution is weighted the same way (the second check,
`OUT\skeptic\k08_share_bases.py`, found this for families.parquet, panel g and A's B1 values). The captions of
Table 9 and of Tables S3.19, S3.23 to S3.27 and S3.29 state it.
"""),
    ("V3-2", r"""The models explained at the nowcast (a), and the rivals left out, with the reason (b).""",
     r"""The models explained at the nowcast (a), and the rivals and naive baselines left out, with the reason (b)."""),
    ("V3-2", r"""engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); rulings AW2, AY1, BA1 -->""",
     r"""engine/PENDING_PARTS.md Part 628 (methods; rivals left out and why); paper/draft/03_protocol.md Section 3.3, paper/draft/tables/table_3.md note d and paper/draft/GLOSSARY.md (naive baseline, trees-off fit, reference) for the naive baselines; paper/draft/tables/table_6.md (Table 7) for the rivals at forecast leads only; rulings AW2, AY1, BA1 -->"""),
    ("V3-6", r"""| Skill guard at the nowcast | treeroute: `passed (the kept arm)`;""",
     r"""| Skill guard at the nowcast | treeroute: `passed (the adopted arm)`;"""),
    ("V3-6", r"""| rival_rf | `random forest, rebuilt from the board's records; exact interventional TreeSHAP` |""",
     r"""| rival_rf | `random forest, rebuilt from the rival board's records; exact interventional TreeSHAP` |"""),
    ("V3-2", r"""```
**b. Rivals left out.**
```""",
     r"""```
**b. Rivals and naive baselines left out.**
```"""),
    ("V3-2", r"""| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals and predict-zero; on coral bleaching, which has no per-location normal, the training median and predict-zero | No input feature: there is no SHAP value to compute. |""",
     r"""| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals, predict-zero and each link's trees-off fit, which equals that link's normal exactly and is the reference of the arms in that link; on coral bleaching, which has no per-location normal, the training median (its reference) and predict-zero | No input feature: there is no SHAP value to compute. |"""),
    ("V3-2", r"""Panel b lists the rivals of the nowcast; rivals that run only at forecast leads""",
     r"""Panel b lists the nowcast's rivals and naive baselines that have no SHAP value; rivals that run only at forecast leads"""),
    ("V3-1", r"""of its total mean absolute SHAP value; the others are structural zeros.""",
     r"""of its total mean absolute SHAP value (with each region weighted equally); the others are structural zeros."""),
    ("V3-6", r"""coral bleaching: the visit's saved pool of other sites' visits.""",
     r"""coral bleaching: the survey visit's saved router fit rows, a pool of other sites' survey visits."""),
    ("V3-6", r"""| Skill guard | treeroute: `passed (the kept arm)`;""",
     r"""| Skill guard | treeroute: `passed (the adopted arm)`;"""),
    ("V3-6", r"""| `Kept arm` | `link, answer type and weighting; router type` |""",
     r"""| `Adopted arm` | `link, answer type and weighting; router type` |"""),
    ("V3-6", r"""| `E3a` | `inputs before the read equal the manifest's (package, groups, constants, file lists, features)` |""",
     r"""| `E3a` | `inputs, before the labels are read, equal the manifest's (dataset package, regions, constants, file lists, features)` |"""),
    ("V3-6", r"""| `E3m` | `a moved package file has the content, size and time that the freeze locks record (path map)` |""",
     r"""| `E3m` | `a moved dataset package file has the content, size and time that the run's locks record (path map)` |"""),
    ("V3-6", r"""| `E3` | `package fingerprint, derived settings and run fingerprint after the derive` |""",
     r"""| `E3` | `dataset package fingerprint, the settings that the written rules set, and run fingerprint, after the written rules are applied` |"""),
    ("V3-6", r"""| `E6` | `c and the guard tolerances equal the run's records` |""",
     r"""| `E6` | `c and the identity tolerances (one per link) equal the run's records` |"""),
    ("V3-6", r"""on one sampled location's fit and test rows (forest loss: every sampled location; coral bleaching: one visit's pool and test row)` |""",
     r"""on one sampled location's router fit rows and test rows (forest loss: every sampled location; coral bleaching: one survey visit's router fit rows and test row)` |"""),
    ("V3-5", r"""| `Guard-passing rivals in another link` |""",
     r"""| `Rivals in another link that passed their skill guard` |"""),
    ("V3-3", r"""with the number of finite draws where a statistic is defined on fewer of them. Same-link pairs""",
     r"""with the number of finite draws where a statistic is defined on 1 to 1,999 of them. Same-link pairs"""),
    ("V3-3", r"""bardl_maxima.txt (the collation moves of the footnote, ruling BB3)`;""",
     r"""bardl_maxima.txt (the spreads of the footnote, ruling BB3)`;"""),
    ("V3-1", r"""- `{shares_sentence}` (version 2, C1): fire and coral (the tables with panel g)
  `Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; none has an interval, as in the comparison's files.`;
  else (pm25, ndvi, defo)
  `Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; neither has an interval, as in the comparison's files.`""",
     r"""- `{shares_sentence}` (version 2, C1; version 3, V3-1): fire and coral (the tables with panel g)
  `Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally, and no share has an interval, as in the comparison's files.`;
  else (pm25, ndvi, defo)
  `Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; both means weight each region equally, and neither share has an interval, as in the comparison's files.`"""),
    ("V3-1", r"""families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
`{shares_sentence}` states both in the caption.""",
     r"""families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, panel g's included (version 3, V3-1; PROTOCOL section 8, as in 4.1).
`{shares_sentence}` states both bases and the weighting in the caption."""),
    ("V3-6", r"""with M = "; raw model, declined by its guard: ", if the label holds M, the text before M + M + the inline names (2.2) of the data names after M (split on ", ") joined by ", "; else the label as it stands. So `cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge` prints `cross-link (not comparable in scale or rank); raw model, declined by its guard: Ridge` |""",
     r"""with M = "; raw model, declined by its guard: " (the source label's words, check 3.3) and P = "; raw model, declined by its skill guard: " (the printed words; version 3, V3-6), if the label holds M, the text before M + P + the inline names (2.2) of the data names after M (split on ", ") joined by ", "; else the label as it stands. So `cross-link (not comparable in scale or rank); raw model, declined by its guard: rival_ridge` prints `cross-link (not comparable in scale or rank); raw model, declined by its skill guard: Ridge` |"""),
    ("V3-4", r"""Beyond its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its pairs that use those sets depend on that order.""",
     r"""Beyond its three variables (variable level) and nine columns (feature level), its ranking is therefore filled by name order, the tie rule applied in code-point ascending order, and so are its top-5, top-10 and top-20 sets where they reach that far; the cells of its pairs that read that part of its ranking (the Jaccard similarities, the top-20-union Spearman and the RBO) depend on that order."""),
    ("V3-1", r"""SHAP values. From the independent re-computation (two implementations that agree). <!--""",
     r"""SHAP values; both means weight each region equally. From the independent re-computation (two implementations that agree). <!--"""),
    ("V3-1", r"""own-history share (A `b1.{p}.variable.families`, `b1.{p}.variable.own_history_share`) are of the sum of its five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
""",
     r"""own-history share (A `b1.{p}.variable.families`, `b1.{p}.variable.own_history_share`) are of the sum of its five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
Both means weight each region equally, as in the main runs (version 3, V3-1; PROTOCOL section 8, as in 4.1); the
caption says so.
"""),
    ("V3-7", r"""below. It is written by `json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"` (UTF-8, no BOM; no
other formatting step).
""",
     r"""below. It is written by `json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n"` (UTF-8, no BOM; no
other formatting step). `tables_file` names the builders' `tables.md` (`OUT\<X>\tables.md`, beside cells.json), of
which `OUT\reconcile\tables_agreed.md` is a byte copy with the same lines, so an entry's `line` is the same line in
both files (version 3, V3-7).
"""),
    ("V3-1", r"""12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither has an
    interval, as in the comparison's files", or "none has an interval" in the two tables with panel g). B1's family
    shares and own-history share keep their intervals; no top-k list has one.""",
     r"""12. **BB5.** No interval for the main models' top-10 shares and family shares; the captions say so ("neither share
    has an interval, as in the comparison's files", or "no share has an interval" in the two tables with panel g;
    version 3, V3-1). B1's family shares and own-history share keep their intervals; no top-k list has one."""),
    ("V3-6", r"""S3.21 per gate, in the protocol's running order, with the kept arm
    as the first row.""",
     r"""S3.21 per gate, in the protocol's running order, with the adopted
    arm as the first row."""),
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


raw2, t2 = read(V2_PATH)
raw3, t3 = read(V3_PATH)
print("TABLE_SPEC_v2.md sha256", hashlib.sha256(raw2).hexdigest())
print("TABLE_SPEC.md    sha256", hashlib.sha256(raw3).hexdigest())
if hashlib.sha256(raw2).hexdigest() != V2_SHA256:
    fail("TABLE_SPEC_v2.md is not the version-2 file")
for name, raw in (("v2", raw2), ("v3", raw3)):
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or b"\t" in raw or not raw.endswith(b"\n") \
            or raw.endswith(b"\n\n"):
        fail(name + ": not UTF-8 without BOM, LF only, no tab, one final LF")
    if re.search(rb" \n", raw):
        fail(name + ": a line ends with a space")

# 1. Replay the listed edits on version 2.
spans = []
for cid, old, new in EDITS:
    if cid not in LISTED:
        fail("edit with an unlisted id " + cid)
    n = t2.count(old)
    if n != 1:
        fail("{}: the old text occurs {} times in version 2: {!r}".format(cid, n, old[:70]))
        continue
    s = t2.index(old)
    spans.append((s, s + len(old), cid, old, new))
spans.sort()
for a, b in zip(spans, spans[1:]):
    if a[1] > b[0]:
        fail("overlapping edits {} and {}".format(a[2], b[2]))
parts, pos, v2spans, v3spans = [], 0, [], []
for s, e, cid, old, new in spans:
    parts.append(t2[pos:s])
    start3 = sum(len(x) for x in parts)
    parts.append(new)
    v2spans.append((s, e, cid))
    v3spans.append((start3, start3 + len(new), cid))
    pos = e
parts.append(t2[pos:])
expected = "".join(parts)
if not t3.startswith(expected):
    k = next((i for i, (x, y) in enumerate(zip(expected, t3)) if x != y), min(len(expected), len(t3)))
    fail("version 3 is not version 2 with the listed edits; first difference at character {}: v3 has {!r}".format(
        k, t3[max(0, k - 40):k + 40]))
tail = t3[len(expected):]
if not tail.startswith(S10_HEAD):
    fail("the text after the listed edits does not start with section 10's heading")
v3spans.append((len(expected), len(t3), "S10"))
print("replay: {} edits applied to version 2; version 3 = that text + section 10 ({} characters): {}".format(
    len(spans), len(tail), "yes" if ok else "NO"))


# 2. Every changed line (difflib) belongs to a listed change.
def line_starts(text):
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return starts


L2, L3 = t2.split("\n")[:-1], t3.split("\n")[:-1]  # both end with one "\n": no empty last line
print("lines: version 2 {}, version 3 {}".format(len(L2), len(L3)))
st2, st3 = line_starts(t2), line_starts(t3)


def owner(spans_, starts, lineno, text_len):
    a = starts[lineno - 1]
    b = starts[lineno] if lineno < len(starts) else text_len
    hit = [cid for (s, e, cid) in spans_ if s < b and e > a or (s == e == a)]
    if not hit and b - a <= 1:
        # a blank line next to an edit: difflib may pair the edit's own blank line with the old one
        hit = [cid for (s, e, cid) in spans_ if s <= b and e >= a]
    return sorted(set(hit))


per = collections.OrderedDict((c, {"v2": [], "v3": []}) for c in LISTED)
sm = difflib.SequenceMatcher(a=L2, b=L3, autojunk=False)
n_changed2 = n_changed3 = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    for i in range(i1, i2):
        n_changed2 += 1
        who = owner(v2spans, st2, i + 1, len(t2))
        if len(who) != 1:
            fail("version-2 line {} changed and belongs to {}: {!r}".format(i + 1, who or "no listed change", L2[i][:80]))
        else:
            per[who[0]]["v2"].append(i + 1)
    for j in range(j1, j2):
        n_changed3 += 1
        who = owner(v3spans, st3, j + 1, len(t3))
        if len(who) != 1:
            fail("version-3 line {} changed and belongs to {}: {!r}".format(j + 1, who or "no listed change", L3[j][:80]))
        else:
            per[who[0]]["v3"].append(j + 1)


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


print("changed lines: {} of version 2 (removed or replaced), {} of version 3 (new or replacing)".format(
    n_changed2, n_changed3))
for cid, d in per.items():
    print("  {:4s} version-2 lines {}".format(cid, ranges(d["v2"])))
    print("  {:4s} version-3 lines {}".format("", ranges(d["v3"])))
    if not d["v2"] and not d["v3"]:
        fail(cid + " is listed but changed no line")


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


B2, B3 = blocks(L2), blocks(L3)
print("fenced blocks: version 2 {}, version 3 {}".format(len(B2), len(B3)))
if len(B2) != len(B3):
    fail("the number of fenced blocks changed")
for k, (x, y) in enumerate(zip(B2, B3), 1):
    if x["lines"] != y["lines"]:
        f2 = x["lines"][0] if x["lines"] else ""
        f3 = y["lines"][0] if y["lines"] else ""
        if len(x["lines"]) != len(y["lines"]):
            fail("block {} changed its number of lines".format(k))
        same24 = f2[:24] == f3[:24]
        print("  block {:2d} (v2 line {}, v3 line {}): {} lines; first line {}; first 24 characters {}".format(
            k, x["open"], y["open"], len(y["lines"]), "unchanged" if f2 == f3 else "CHANGED",
            "same" if same24 else "DIFFER: {!r} -> {!r}".format(f2[:44], f3[:44])))

# 4. Digits and placeholders removed or added by each change.
NUM = re.compile(r"\d[\d,.]*\d|\d")
PH = re.compile(r"\{[a-z][a-z0-9_]*\}")
for cid in LISTED:
    olds = [old for (c, old, new) in EDITS if c == cid]
    news = [new for (c, old, new) in EDITS if c == cid]
    if cid == "S10":
        print("  S10  adds section 10 (its numbers are line numbers, ids and hashes) and its contents entry")
        continue
    o, n = collections.Counter(), collections.Counter()
    po, pn = collections.Counter(), collections.Counter()
    for x in olds:
        o.update(NUM.findall(x))
        po.update(PH.findall(x))
    for x in news:
        n.update(NUM.findall(x))
        pn.update(PH.findall(x))
    print("  {:4s} digits removed {} added {}; placeholders removed {} added {}".format(
        cid, dict(o - n), dict(n - o), dict(po - pn), dict(pn - po)))

print("RESULT:", "every changed line belongs to a listed change" if ok else "FAILED")
sys.exit(0 if ok else 1)
