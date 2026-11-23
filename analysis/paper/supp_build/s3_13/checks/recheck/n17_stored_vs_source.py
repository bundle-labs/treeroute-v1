# n17: every "stored" double printed in facts A12, A16-A22 compared with the named source file's value (not cells.json):
# AW4_main_row.json, results.json, families.parquet, gates.json. Read-only.
import json
import os
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
S = r"D:\treeroute\analysis\shap_v1"
facts = open(os.path.join(ROOT, r"paper\supp_build\s3_13\stage\paper\PAPER_FACTS.md"), "rb").read().decode("utf-8")
src_vals = {}


def add(label, v):
    src_vals.setdefault(repr(float(v)), []).append(label)


for p in ("pm25", "ndvi", "defo", "coral", "fire"):
    a = json.load(open(os.path.join(S, "out", p, "lead_0", "compare", "AW4_main_row.json"), encoding="utf-8"))
    for k in ("kendall_w", "treeroute_vs_same_link_rivals_median_spearman_top20_union", "rbo_vs_consensus_p0.9",
              "own_history_share_treeroute", "own_history_share_median_rival"):
        if k in a and a[k].get("value") is not None:
            add("%s AW4 %s value" % (p, k), a[k]["value"])
            for i in (0, 1):
                add("%s AW4 %s ci%d" % (p, k, i), a[k]["ci"][i])
    fam = pd.read_parquet(os.path.join(S, "out", p, "lead_0", "compare", "families.parquet"))
    for _, r in fam.iterrows():
        add("%s families %s %s" % (p, r["model"], r["family"]), r["share"])
R = json.load(open(os.path.join(S, r"verify_v1\A\results.json"), encoding="utf-8"))
o = R["problems"]["fire"]["main_row"]["own_history_share_treeroute"]
for k in ("value", "ci_low", "ci_high"):
    add("fire results own_history_share_treeroute " + k, o[k])
for p in ("pm25", "ndvi", "fire"):
    sn = R["b1"][p]["variable"]["families"]["seasonal_normal"]
    for k in ("value", "ci_low", "ci_high"):
        add("%s results b1 seasonal_normal %s" % (p, k), sn[k])
    add("%s results b1 top3[0]" % p, R["b1"][p]["variable"]["top3"][0][1])
for p in ("fire", "coral"):
    g = json.load(open(os.path.join(S, "rebuild", p, "lead_0", "gates.json"), encoding="utf-8"))
    add("%s gates E8 max_rel_pre" % p, g["gates"]["E8_predictions"]["values"]["max_rel_pre"])
n = bad = 0
for fid in ("A12", "A16", "A17", "A18", "A20", "A21", "A22"):
    t = re.search(r"^- \*\*%s .*$" % fid, facts, flags=re.M).group(0)
    blocks = re.findall(r"stored ([^)]*)\)", t)
    for b in blocks:
        for s in re.findall(r"-?\d+\.\d+(?:e-?\d+)?", b):
            n += 1
            labs = src_vals.get(repr(float(s)))
            if repr(float(s)) != s and float(s) != 0.0:
                print("   %s: text %s differs from repr %s" % (fid, s, repr(float(s))))
            if not labs and float(s) != 0.0:
                bad += 1
                print("NOT IN SOURCE %s %s" % (fid, s))
            elif float(s) == 0.0:
                pass
print("stored doubles checked:", n, "not found in the named sources:", bad)
