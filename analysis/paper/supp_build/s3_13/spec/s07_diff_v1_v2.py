# s07_diff_v1_v2.py - version 2 of TABLE_SPEC.md (2026-11-17). Diffs TABLE_SPEC_v1.md (version 1, kept byte for
# byte) with TABLE_SPEC.md (version 2) and confirms that every changed line belongs to a listed change of
# OUT\_brief\fix_order_v2.md (C1-C9, G1-G4) or to the new section 9 (S9).
# How: the edits of version 2 are listed below as (change id, old text, new text). The script applies them to
# version 1 (each old text must occur exactly once there, and no two may overlap) and requires the result, followed by
# section 9, to equal version 2 byte for byte. It then lists every changed line (difflib) with the change it belongs
# to, checks the fenced-block structure, and lists the digits and placeholders each change removes or adds.
# Read-only; prints only. Run from this folder: py -3.9 -I -B s07_diff_v1_v2.py
import collections
import difflib
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
V1_PATH = os.path.join(HERE, "TABLE_SPEC_v1.md")
V2_PATH = os.path.join(HERE, "TABLE_SPEC.md")
V1_SHA256 = "979be5ed64b908402b8c69ad60eb0b07e48f1b10b8cacaadb7049fefff7cf9fb"  # TABLE_SPEC.md before any v2 edit
S9_HEAD = "\n---\n\n## 9. Version 2 (2026-11-17)\n"
LISTED = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "G1", "G2", "G3", "G4", "S9"]

EDITS = [
    ("S9", r"""8 What the spec writer opened.""",
     r"""8 What the spec writer opened - 9 Version 2 (2026-11-17)."""),
    ("G2", r"""missing there or appears twice in it).
""",
     r"""missing there or appears twice in it).

Text formats (version 2, G2): `SHAP\SAMPLE_REGISTER.txt` and the logs `SHAP\logs\tr_shap_<p>_lead0.log` have CRLF
line ends; `V\_lead\outputs\bardl_maxima.txt` has a UTF-8 byte-order mark and CRLF line ends. Read each of them as text
with universal newlines and encoding `utf-8-sig` (`open(path, encoding="utf-8-sig")`, whose default `newline=None`
turns every `\r\n` into `\n`), and split the text on `\n`. Line numbers (the selectors of section 5) count from 1 on
the lines so read; the register's fields, the maxima regex above and the two log regexes of section 4.10 (the "done
in" regex ends in `$`) are applied to a line without its line end.
"""),
    ("C3", r"""(footnote with the collation moves)""",
     r"""(footnote with the spreads over the three collations)"""),
    ("C2", r"""`exactness.json` (the comparison
   script's own row-by-row check""",
     r"""`exactness.json` (the rivals' SHAP
   script's own row-by-row check"""),
    ("C9", r"""the nowcast of each problem. Built from the stored values""",
     r"""the nowcast of each problem. Version 2 (2026-11-17, after the first check): ten captions and notes reworded, one row of Table S3.18 b dropped and one note line added; no number changed. Built from the stored values"""),
    ("C1", r""" Own-history share: the share of a model's total mean absolute SHAP value that goes to the location's own lagged labels.""",
     r""" Own-history share: the share of the own-history family (the location's own lagged labels) in the sum of the model's five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; it is not the sum of the own-history variables' shares."""),
    ("C1", r"""+ `†`; `–`.

Notes (exact, in this order):""",
     r"""+ `†`; `–`.

The two share bases (PROTOCOL section 8; version 2, C1). A player's share (importance.parquet `share`, the top-k
shares) is its mean absolute SHAP value divided by the model's total mean absolute SHAP value over J. A family share
(families.parquet `share`) is the family's mean absolute attribution divided by the sum of the model's five families'
mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values on that row.
The own-history shares of Table 9 (AW4 `own_history_share_treeroute` and `own_history_share_median_rival`; A's
`problems.fire.main_row.own_history_share_treeroute`) are family shares, not the sum of the own-history variables'
shares, as the caption says.

Notes (exact, in this order):"""),
    ("C4", r"""| Coral bleaching | CRW Outlook | One-input linear map on anomalies; it could instead be shown as a labelled reference row (decision D15, left at its default). |
| All five | The baselines: the seasonal normal, the last-5-years normal, predict-zero, persistence and damped persistence; on coral bleaching the training median and the last visit | No input feature: there is no SHAP value to compute. |""",
     r"""| All five | The naive baselines at the nowcast: the arithmetic and last-5-years normals and predict-zero; on coral bleaching, which has no per-location normal, the training median and predict-zero | No input feature: there is no SHAP value to compute. |"""),
    ("C4", r"""```
ᵃ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).
Links:""",
     r"""```
Panel b lists the rivals of the nowcast; rivals that run only at forecast leads (Table 7), among them the CRW Outlook, are outside this comparison, which explains the nowcast only.
ᵃ Failed: the raw model is explained, labelled, and kept out of Kendall's W, the consensus and the main-text row (decision D6).
Links:"""),
    ("C2", r"""The comparison script checks a rival's pre-clip column only (–: not read).
ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. The comparison script's own check of its row-by-row copy of the design,""",
     r"""The rivals' SHAP script (rival_shap.py) checks a rival's pre-clip column only (–: not read).
ᵇ Ridge outside coral bleaching is explained by a loader that repeats the rival board's own block-wise scoring, which reproduces every saved prediction. The rivals' SHAP script's own check of its row-by-row copy of the design,"""),
    ("C6", r"""| `E10` | `exported trees and evaluator reproduce the engine's tree answers bit for bit` |""",
     r"""| `E10` | `exported trees and evaluator reproduce the engine's tree answers bit for bit, on one sampled location's fit and test rows (forest loss: every sampled location; coral bleaching: one visit's pool and test row)` |"""),
    ("C6", r"""while every checked prediction matches (E5a, E8, E10); the cause is not established.""",
     r"""while every checked tree answer and prediction matches: bit for bit (E5a, E10, and E8 on the identity and log(y + c) arms), and within the D8 tolerance on the arcsine arms (E8); the cause is not established."""),
    ("G3", r"""problem; parts: E3m `files`; E4 `rows`;""",
     r"""problem; parts: E3m `files` (version 2, G3: its selector is `len(gates.E3m_recorded_path_map.values.files)` and its
stored value the list's length); E4 `rows`;"""),
    ("C5", r"""| `Rivals in another link` |""",
     r"""| `Guard-passing rivals in another link` |"""),
    ("G4", r"""joined by "; ", on coral + " (no own-history input)" (fire: `–`) |""",
     r"""joined by "; "; on coral the label " (no own-history input)" is appended once, at the end of the joined cell, not after each rival's share (version 2, G4) (fire: `–`) |"""),
    ("C8", r"""was read by an agent on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6).""",
     r"""was read on 2026-11-13 at about 15:31, before the independent re-computation; the re-computation's implementers A and B never opened it (ruling BB6; Supplement S1.7 records who read it)."""),
    ("C1", r"""not comparable in scale or rank. Shares are of a model's total mean absolute SHAP value over J, without intervals, as in the comparison's files. <!--""",
     r"""not comparable in scale or rank. {shares_sentence} <!--"""),
    ("C1", r"""- `{extra_rulings}`: ndvi `, BB3`; defo and coral `, BB4`; else empty.
""",
     r"""- `{extra_rulings}`: ndvi `, BB3`; defo and coral `, BB4`; else empty.
- `{shares_sentence}` (version 2, C1): fire and coral (the tables with panel g)
  `Top-10 shares (d, e, g) are of a model's total mean absolute SHAP value over J (g: on its rows with a forecast above 0); family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; none has an interval, as in the comparison's files.`;
  else (pm25, ndvi, defo)
  `Top-10 shares (d, e) are of a model's total mean absolute SHAP value over J; family shares (f) are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values; neither has an interval, as in the comparison's files.`

The two share bases (version 2, C1; as in 4.1): the top-10 shares of panels d and e (importance.parquet `share`) and
of panel g (PL `nonzero_forecast_rows`, on the model's rows with a forecast above 0) are of the model's total mean
absolute SHAP value over J; the family shares of panel f (families.parquet `share`) are of the sum of the model's five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
`{shares_sentence}` states both in the caption.
"""),
    ("C7", r"""and, where fewer than 2,000, the number of draws on which the statistic is defined. Undefined: no player qualifies on the full sample.""",
     r"""and, where the statistic is defined on 1 to 1,999 of the 2,000 draws, that number of draws. Undefined: no player qualifies on the full sample; printed without an interval, it is undefined on every draw."""),
    ("C3", r"""Its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, at both levels, and the cells of its pairs that use those sets depend on that order. Under the other two orders tried (case-insensitive ascending, and descending), the largest move of each statistic""",
     r"""Beyond its three variables (variable level) and nine columns (feature level), its top-5, top-10 and top-20 sets are therefore filled by name order, the tie rule applied in code-point ascending order, and the cells of its pairs that use those sets depend on that order. Across the three orders tried (code-point ascending, as printed; case-insensitive ascending; and descending), the largest spread (highest minus lowest value) of each statistic"""),
    ("G1", r"""Panel f: row = family name (as in families.parquet), column = model. Note numbers (ndvi):""",
     r"""Panel f: row = family name (as in families.parquet), column = model, part `share` (version
2, G1: as the other shares printed without an interval). Note numbers (ndvi):"""),
    ("C1", r"""Shares are of the B1 run's total mean absolute SHAP value over the pair's J.""",
     r"""Top-3 and top-10 shares are of the B1 run's total mean absolute SHAP value over the pair's J; family shares and the own-history share are of the sum of its five families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values."""),
    ("C1", r"""First header cell `Rank`. Rows `1` to `10`: TOP(A `b1.{p}.{L}.top10[k-1]`).
""",
     r"""First header cell `Rank`. Rows `1` to `10`: TOP(A `b1.{p}.{L}.top10[k-1]`).

The two share bases (version 2, C1; as in 4.1): B1's top-3 and top-10 shares (A `b1.{p}.variable.top3`,
`b1.{p}.{L}.top10`) are of the B1 run's total mean absolute SHAP value over the pair's J; its family shares and its
own-history share (A `b1.{p}.variable.families`, `b1.{p}.variable.own_history_share`) are of the sum of its five
families' mean absolute attributions, a family's attribution on a row being the sum of its variables' SHAP values.
"""),
    ("G2", r"""The B1 block of a log: split the file on `\n`; the set-up lines match""",
     r"""The B1 block of a log: read the file as section 1's text formats say
(universal newlines, encoding `utf-8-sig`; version 2, G2) and split the text on `\n`; the set-up lines match"""),
    ("G2", r"""first line after it that matches
""",
     r"""first line after it that matches, as a line without its line end (G2),
"""),
    ("C4", r"""Coral bleaching: B1 is not defined (its router reads a pool of other sites' survey visits), so it has no B1 run.""",
     r"""Coral bleaching: B1 is not defined, so it has no B1 run."""),
    ("G1", r"""`count`, `share`, ...) |""",
     r"""`count`, `share`, ...). Where section 4 names no part (version 2, G1): a cell that prints one number uses `value`; the family shares of panel f in Tables S3.23-S3.27 use `share`, as the other shares printed without an interval (panels d, e and g; Table S3.29 c and d); an interval cell uses `value`, `ci_low`, `ci_high`, and `n_finite` when it is printed |"""),
    ("G2", r"""with the 1-based line number in that file and the field name""",
     r"""with the 1-based line number in that file (counted on the lines read
  as section 1's text formats say: universal newlines, `utf-8-sig`; version 2, G2) and the field name"""),
    ("C3", r"""and the six largest moves and the example from
    bardl_maxima.txt, each""",
     r"""and the six largest spreads over the three collations and
    the example from bardl_maxima.txt, each"""),
    ("C1", r"""the captions say "without intervals, as
    in the comparison's files". B1's family shares and own-history share keep their intervals; no top-k list has one.""",
     r"""the captions say so ("neither has an
    interval, as in the comparison's files", or "none has an interval" in the two tables with panel g). B1's family
    shares and own-history share keep their intervals; no top-k list has one."""),
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


raw1, t1 = read(V1_PATH)
raw2, t2 = read(V2_PATH)
print("TABLE_SPEC_v1.md sha256", hashlib.sha256(raw1).hexdigest())
print("TABLE_SPEC.md    sha256", hashlib.sha256(raw2).hexdigest())
if hashlib.sha256(raw1).hexdigest() != V1_SHA256:
    fail("TABLE_SPEC_v1.md is not the version-1 file")
for name, raw in (("v1", raw1), ("v2", raw2)):
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        fail(name + ": not UTF-8 without BOM, LF only, one final LF")

# 1. Replay the listed edits on version 1.
spans = []
for cid, old, new in EDITS:
    if cid not in LISTED:
        fail("edit with an unlisted id " + cid)
    n = t1.count(old)
    if n != 1:
        fail("{}: the old text occurs {} times in version 1: {!r}".format(cid, n, old[:70]))
        continue
    s = t1.index(old)
    spans.append((s, s + len(old), cid, old, new))
spans.sort()
for a, b in zip(spans, spans[1:]):
    if a[1] > b[0]:
        fail("overlapping edits {} and {}".format(a[2], b[2]))
parts, pos, v1spans, v2spans = [], 0, [], []
for s, e, cid, old, new in spans:
    parts.append(t1[pos:s])
    start2 = sum(len(x) for x in parts)
    parts.append(new)
    v1spans.append((s, e, cid))
    v2spans.append((start2, start2 + len(new), cid))
    pos = e
parts.append(t1[pos:])
expected = "".join(parts)
if not t2.startswith(expected):
    k = next((i for i, (x, y) in enumerate(zip(expected, t2)) if x != y), min(len(expected), len(t2)))
    fail("version 2 is not version 1 with the listed edits; first difference at character {}: v2 has {!r}".format(
        k, t2[max(0, k - 40):k + 40]))
tail = t2[len(expected):]
if not tail.startswith(S9_HEAD):
    fail("the text after the listed edits does not start with section 9's heading")
v2spans.append((len(expected), len(t2), "S9"))
print("replay: {} edits applied to version 1; version 2 = that text + section 9 ({} characters): {}".format(
    len(spans), len(tail), "yes" if ok else "NO"))

# 2. Every changed line (difflib) belongs to a listed change.
def line_starts(text):
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())
    return starts


L1, L2 = t1.split("\n")[:-1], t2.split("\n")[:-1]  # both end with one "\n": no empty last line
print("lines: version 1 {}, version 2 {}".format(len(L1), len(L2)))
st1, st2 = line_starts(t1), line_starts(t2)


def owner(spans_, starts, lineno, text_len):
    a = starts[lineno - 1]
    b = starts[lineno] if lineno < len(starts) else text_len
    hit = [cid for (s, e, cid) in spans_ if s < b and e > a or (s == e == a)]
    if not hit and b - a <= 1:
        # a blank line next to an edit: difflib may pair the edit's own blank line with the old one
        hit = [cid for (s, e, cid) in spans_ if s <= b and e >= a]
    return sorted(set(hit))


per = collections.OrderedDict((c, {"v1": [], "v2": []}) for c in LISTED)
sm = difflib.SequenceMatcher(a=L1, b=L2, autojunk=False)
n_changed1 = n_changed2 = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        continue
    for i in range(i1, i2):
        n_changed1 += 1
        who = owner(v1spans, st1, i + 1, len(t1))
        if len(who) != 1:
            fail("version-1 line {} changed and belongs to {}: {!r}".format(i + 1, who or "no listed change", L1[i][:80]))
        else:
            per[who[0]]["v1"].append(i + 1)
    for j in range(j1, j2):
        n_changed2 += 1
        who = owner(v2spans, st2, j + 1, len(t2))
        if len(who) != 1:
            fail("version-2 line {} changed and belongs to {}: {!r}".format(j + 1, who or "no listed change", L2[j][:80]))
        else:
            per[who[0]]["v2"].append(j + 1)


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


print("changed lines: {} of version 1 (removed or replaced), {} of version 2 (new or replacing)".format(
    n_changed1, n_changed2))
for cid, d in per.items():
    print("  {:3s} version-1 lines {:28s} version-2 lines {}".format(cid, ranges(d["v1"]), ranges(d["v2"])))
    if not d["v1"] and not d["v2"]:
        fail(cid + " is listed but changed no line")

# 3. Fenced blocks: same number; which first lines changed.
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
    return out


B1, B2 = blocks(L1), blocks(L2)
print("fenced blocks: version 1 {}, version 2 {}".format(len(B1), len(B2)))
if len(B1) != len(B2):
    fail("the number of fenced blocks changed")
for k, (x, y) in enumerate(zip(B1, B2), 1):
    if x["lines"] != y["lines"]:
        f1 = x["lines"][0] if x["lines"] else ""
        f2 = y["lines"][0] if y["lines"] else ""
        print("  block {:2d} (v1 line {}, v2 line {}): {} lines -> {} lines; first line {}; first 24 characters {}".format(
            k, x["open"], y["open"], len(x["lines"]), len(y["lines"]),
            "unchanged" if f1 == f2 else "CHANGED", "same" if f1[:24] == f2[:24] else "DIFFER: {!r} -> {!r}".format(
                f1[:40], f2[:40])))

# 4. Digits and placeholders removed or added by each change.
NUM = re.compile(r"\d[\d,.]*\d|\d")
PH = re.compile(r"\{[a-z][a-z0-9_]*\}")
for cid in LISTED:
    olds = [old for (c, old, new) in EDITS if c == cid]
    news = [new for (c, old, new) in EDITS if c == cid]
    if cid == "S9":
        news.append(tail)
    o, n = collections.Counter(), collections.Counter()
    po, pn = collections.Counter(), collections.Counter()
    for x in olds:
        o.update(NUM.findall(x))
        po.update(PH.findall(x))
    for x in news:
        n.update(NUM.findall(x))
        pn.update(PH.findall(x))
    if cid == "S9":
        print("  S9 adds section 9 only (its numbers are line numbers and change ids)")
        continue
    print("  {:3s} digits removed {} added {}; placeholders removed {} added {}".format(
        cid, dict(o - n), dict(n - o), dict(po - pn), dict(pn - po)))

print("RESULT:", "every changed line belongs to a listed change" if ok else "FAILED")
sys.exit(0 if ok else 1)
