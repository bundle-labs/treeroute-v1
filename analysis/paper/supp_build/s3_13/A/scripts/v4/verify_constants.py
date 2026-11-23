# -*- coding: utf-8 -*-
# Builder A's check that every hand-copied constant and template of build_tables.py occurs verbatim in the spec
# (fenced lines, or backticked texts of the spec's tables). Prints only.
# Version 2 (2026-11-17): the S3.22 row label of C5 in the list of constant cells, and the two values of the
# caption template's new placeholder {shares_sentence} (C1) as backticked spec texts.
# Version 3 (2026-11-17): the list of constant cells holds the version-3 texts of treeroute's skill-guard cell
# (V3-6) and of the S3.22 row label (V3-5); two checks added for what version 3 changed: the S3.22 row labels of the
# script against the first cells of the spec's row table of 4.6, in order (the version-2 label is still quoted in the
# spec's section 9, so "found in the spec" cannot tell it from the new one), and the Link cell of 4.7 (the rule's M
# and P, and its example composed by pair_link_text).
# Version 4 (2026-11-17): the list of constant cells holds the version-4 S3.22 row label (V4-8); one check added
# for what version 4 changed: the answer-type words of the rule of S3.21's Adopted arm row (V4-5), which no check
# read before.
# Run as: py -3.9 -I -B <this script>

import sys
import os
import re
import ast
import importlib.util

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(os.path.dirname(HERE))
spec_path = os.path.join(OUT, "spec", "TABLE_SPEC.md")
with open(spec_path, "r", encoding="utf-8") as f:
    spec = f.read()
fenced = set()
inb = False
for line in spec.split("\n"):
    if line.startswith("```"):
        inb = not inb
        continue
    if inb:
        fenced.add(line)
flat = spec.replace("\n", " ")

s = importlib.util.spec_from_file_location("bt", os.path.join(HERE, "build_tables.py"))
bt = importlib.util.module_from_spec(s)
s.loader.exec_module(bt)

problems = []


def fence(x, what):
    if x not in fenced:
        problems.append("not a fenced spec line: %s: %r" % (what, x[:120]))


def tick(x, what):
    if ("`" + x + "`") not in spec and ("`" + x + "`") not in flat:
        problems.append("not a backticked spec text: %s: %r" % (what, x))


for name in ["HEADER_COMMENT", "HEADING1", "HEADING2", "HEADING3", "CAP9", "HDR9", "CAP18", "LAB18A", "HDR18A",
             "LAB18B", "CAP19", "HDR19", "CAP20", "HDR20", "NOTE20A", "NOTE20C", "NOTE20D", "CAP21", "HDR21", "CAP22",
             "HDR22", "CAP_AW3", "LAB_A", "LAB_B", "LAB_C", "HDR_C", "LAB_D", "LAB_E", "LAB_F", "LAB_G",
             "NOTE_AW3_FIRE", "NOTE_AW3_G", "CAP28", "LAB28A", "LAB28B", "HDR_B1", "CAP29", "LAB29A", "LAB29B",
             "LAB29C", "LAB29D", "CAP30", "LAB30A", "HDR30A", "LAB30B", "HDR30B"]:
    fence(getattr(bt, name), name)
for name in ["NOTES9", "TAB18B", "NOTES18", "NOTES19", "NOTES21", "NOTES22", "NOTES_AW3_ALL1", "NOTES_AW3_ALL2",
             "NOTES28", "NOTES29", "NOTES30"]:
    for i, x in enumerate(getattr(bt, name)):
        fence(x, "%s[%d]" % (name, i))
fence("| " + " | ".join(bt.HDR_A) + " |", "HDR_A")
# templates with placeholders
n20 = bt.NOTE20B_PARTS[0]
for p, mid, tail in bt.NOTE20B_PARTS[1:]:
    n20 += "{bit_%s}" % p + mid + "{rows_%s}" % p + tail
fence(n20, "NOTE20B template")
nd = "".join(("{" + x + "}") if x in bt.NOTE_NDVI_SLOTS else x for x in bt.NOTE_NDVI_PARTS)
fence(nd, "ndvi note template")
fence("{Problem}: variable level ({nv}) {names_v}; feature level ({nf}) {names_f}.", "S3.19 line template")
tick(bt.G_CLAUSE, "g_clause")
tick(bt.EXTRA_SRC_NDVI, "extra_src")
tick(bt.SHARES_DEG, "shares_sentence (fire, coral)")
tick(bt.SHARES_DE, "shares_sentence (pm25, ndvi, defo)")
if bt.SHARES_DEG == bt.SHARES_DE:
    problems.append("the two values of {shares_sentence} are equal")
# names and constant cells
for d, what in ((bt.P_DISP, "P_DISP"), (bt.P_INL, "P_INL"), (bt.M_INL, "M_INL"), (bt.M_HDR, "M_HDR"),
                (bt.LINK_DISP, "LINK_DISP"), (bt.FAM_LABEL, "FAM_LABEL"), (bt.SHAP_METHOD, "SHAP_METHOD"),
                (bt.FAM_ROW, "FAM_ROW")):
    for k, v in d.items():
        tick(v, "%s[%s]" % (what, k))
for key, gcell, what in bt.GATE_ROWS:
    tick(gcell, "gate cell")
    tick(what, "gate what")
for x in ["Kendall's W of the main set [95% CI]", "Mean pairwise Spearman of the main set [95% CI]",
          "Nonzero variables", "Nonzero players", "Rows with a forecast above 0", "Link of the main set",
          "Main set", "Rivals that explain in another link and passed their skill guard", "Rivals declined by their skill guard",
          "Spearman of treeroute v1 with each same-link rival", "Median of those [95% CI]",
          "Range (lowest to highest)", "RBO with the rivals' consensus, p = 0.9 [95% CI]", "treeroute v1's top 3",
          "Consensus top 3", "Own-history share, treeroute v1 [95% CI]", "Own-history share of each same-link rival",
          "Own-history share, median of the rivalsᶜ [95% CI]", "Variables in the pair's J", "Players in the pair's J",
          "Nonzero in the B1 run", "Spearman over J", "Spearman, top-20 union", "Kendall's tau-b", "Jaccard top 5",
          "Jaccard top 10", "Jaccard top 20", "RBO, p = 0.9", "RBO, p = 0.95", "Share distance (TV)",
          "Family-share distance (TV)", "Family-share distance (TV)§", "Sign agreement, top-10 union",
          "Signs determined in both runs / of those, agreeing", "Top 3 (share)", "Own-history share [95% CI]",
          "Largest absolute difference of the SHAP values, feature level (every row and player)",
          "Largest absolute difference of the SHAP values, variable level (every row and variable)",
          "Rows, main run / B1 run", "Players, main run / B1 run", "Variables, main run / B1 run",
          "Same rows / players / variables", "passed (the adopted arm)", "failedᵃ", "failedᵈ", "treeroute v1 onlyᵃ",
          "undefinedᵃ", "bit-identical", "all passed", "differs (informational)", "not applicable",
          "not used (no moved file)", "passed (warning overridden)", "another link", "skill guard failed",
          "Stability under region resampling: "]:
    if ("`" + x + "`") not in spec and ("`" + x + "`") not in flat and ('"' + x + '"') not in flat:
        problems.append("constant not found in the spec: %r" % x)

# version 3 (V3-5): the S3.22 row labels of build_s322, in its row order, against the spec's row table of 4.6
SL = spec.split("\n")
with open(os.path.join(HERE, "build_tables.py"), "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_s322"]
lits = {}
for node in (ast.walk(fn[0]) if len(fn) == 1 else []):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
            and node.targets[0].id in ("first", "spec_rows"):
        lits[node.targets[0].id] = ast.literal_eval(node.value)
hq = [i for i, x in enumerate(SL) if x == "| Quantity cell | Problem cell (fire's cell in brackets where it differs) |"]
spec22 = []
if len(hq) == 1 and SL[hq[0] + 1] == "|---|---|":
    i = hq[0] + 2
    while SL[i].startswith("| "):
        mo = re.match(r"^\| `([^`]+)` \| ", SL[i])
        spec22.append(mo.group(1) if mo else None)
        i += 1
if sorted(lits) != ["first", "spec_rows"] or not spec22:
    problems.append("S3.22 row labels: script dict or spec row table not found")
elif [lits["first"][k] for k in lits["spec_rows"]] != spec22:
    problems.append("S3.22 row labels differ from the spec's row table of 4.6: %r" % (
        [(a, b) for a, b in zip([lits["first"][k] for k in lits["spec_rows"]], spec22) if a != b],))
# version 3 (V3-6): the Link cell rule of 4.7, with M (the source label's words) and P (the printed words)
rl = [x for x in SL if x.startswith("| Link | - | from the pair's `pair_label` ")]
ms = re.findall(r'\bM = "([^"]*)"', rl[0]) if len(rl) == 1 else []
ps = re.findall(r'\bP = "([^"]*)"', rl[0]) if len(rl) == 1 else []
exs = re.findall(r"So `([^`]+)` prints `([^`]+)`", rl[0]) if len(rl) == 1 else []
if len(ms) != 1 or len(ps) != 1 or len(exs) != 1:
    problems.append("Link cell rule of 4.7: M, P or the example not found once")
else:
    if bt.pair_link_text(exs[0][0]) != exs[0][1]:
        problems.append("pair_link_text(%r) gives %r, the spec prints %r" % (exs[0][0], bt.pair_link_text(exs[0][0]),
                                                                          exs[0][1]))
    if exs[0][0].replace(ms[0], ps[0]).replace("rival_ridge", bt.M_INL["rival_ridge"]) != exs[0][1]:
        problems.append("the spec's Link example is not its M -> P composition")
    for lab in ("same-link", "cross-link (not comparable in scale or rank)"):
        if bt.pair_link_text(lab + ms[0] + "rival_ridge") != lab + ps[0] + bt.M_INL["rival_ridge"] \
                or bt.pair_link_text(lab) != lab:
            problems.append("pair_link_text: %r not composed with P" % lab)
# version 4 (V4-5): the answer-type words of build_s321 (its dict tk) against the rule of the Adopted arm row in the
# spec's row table of 4.5, ("..." if R `table_kind` == plain, "..." if corrector); no check read these words before
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_s321"]
tks = [ast.literal_eval(n.value) for n in (ast.walk(fn[0]) if len(fn) == 1 else [])
       if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
       and n.targets[0].id == "tk"]
ra = [x for x in SL if x.startswith("| `Adopted arm` | ")]
rw = re.findall(r'\("([^"]+)" if R `table_kind` == plain, "([^"]+)" if corrector\)', ra[0]) if len(ra) == 1 else []
if len(tks) != 1 or len(rw) != 1:
    problems.append("Adopted arm row of 4.5: the script's answer-type words or the spec's rule not found once")
elif tks[0] != {"plain": rw[0][0], "corrector": rw[0][1]}:
    problems.append("answer-type words: the script has %r, the spec's rule of 4.5 %r" % (tks[0], rw[0]))
print("problems: %d" % len(problems))
for p in problems:
    print("  " + p)
