# -*- coding: utf-8 -*-
# Builder A's check that every hand-copied constant and template of build_tables.py occurs verbatim in the spec
# (fenced lines, or backticked texts of the spec's tables). Prints only.
# Run as: py -3.9 -I -B <this script>

import sys
import os
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
          "Main set", "Rivals in another link", "Rivals declined by their skill guard",
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
          "Same rows / players / variables", "passed (the kept arm)", "failedᵃ", "failedᵈ", "treeroute v1 onlyᵃ",
          "undefinedᵃ", "bit-identical", "all passed", "differs (informational)", "not applicable",
          "not used (no moved file)", "passed (warning overridden)", "another link", "skill guard failed",
          "Stability under region resampling: "]:
    if ("`" + x + "`") not in spec and ("`" + x + "`") not in flat and ('"' + x + '"') not in flat:
        problems.append("constant not found in the spec: %r" % x)
print("problems: %d" % len(problems))
for p in problems:
    print("  " + p)
