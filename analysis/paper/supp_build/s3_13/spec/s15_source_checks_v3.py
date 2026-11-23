# s15_source_checks_v3.py - version 3 of TABLE_SPEC.md (2026-11-17): cheap read-only checks of the claims of the
# change order OUT\_brief\fix_order_v3.md against the sources it names. Prints the source lines with their line
# numbers; writes nothing; runs no script of SHAP, V or the engine (tr_rebuild.py and stages.py are read as text).
# Run from this folder: py -3.9 -I -B s15_source_checks_v3.py
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                                  # ROOT\paper\supp_build\s3_13
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = "D:/treeroute/analysis/shap_v1"
V = SHAP + "/verify_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def lines_of(path, enc="utf-8"):
    with open(path, encoding=enc) as fh:
        return fh.read().split("\n")


def show(label, L, nums):
    print("--", label)
    for n in nums:
        print("   L{}: {}".format(n, L[n - 1]))


print("== 1. SHAP\\PROTOCOL.md")
P = lines_of(SHAP + "/PROTOCOL.md")
show("E3a, E3m, E3 (gates, section 4.1)", P, [175, 176, 177, 178, 179, 180])
show("section 8: families, J, I_m(j)", P, [491, 492, 493, 494, 495, 496, 497])
show("section 8: pairwise statistics and tie rules", P, [505, 506, 507, 508, 509, 510])

print()
print("== 2. ROOT\\paper\\draft\\GLOSSARY.md (rows by paper term)")
G = lines_of(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"))
TERMS = ["naive baseline", "best naive baseline", "trees-off fit", "reference", "training median",
         "own-history features", "router fit rows", "survey visit", "skill guard", "adopted arm", "rival board",
         "lock", "written rules", "identity tolerance", "region"]
for t in TERMS:
    hits = [i for i, ln in enumerate(G, 1) if re.match(r"^\| \*\*" + re.escape(t) + r"\*\*", ln)]
    if len(hits) != 1:
        print("   {}: found {} rows".format(t, len(hits)))
    for i in hits:
        print("   L{}: {}".format(i, G[i - 1]))
kept = [i for i, ln in enumerate(G, 1) if "kept arm" in ln.lower()]
print("   rows that hold 'kept arm':", kept)

print()
print("== 3. what gate E6 compares")
T = lines_of(SHAP + "/scripts/tr_rebuild.py")
show("SHAP\\scripts\\tr_rebuild.py", T, [702, 744, 745, 746])
S = lines_of(os.path.join(ROOT, "engine", "treeroute", "pipeline", "stages.py"))
show("ROOT\\engine\\treeroute\\pipeline\\stages.py", S, list(range(173, 197)))

print()
print("== 4. V\\_lead\\outputs\\bardl_ties.txt (BOM read off; CRLF to LF)")
B = lines_of(V + "/_lead/outputs/bardl_ties.txt", "utf-8-sig")
show("variable level, LightGBM vs BARDL", B, [1, 2, 3, 4, 5, 6, 7])
show("variable level, treeroute vs BARDL", B, [22, 23, 24, 25, 26, 27, 28])
show("largest spread per statistic", B, [58, 59, 60, 61, 62, 63, 64])
ch = {}
for i, ln in enumerate(B, 1):
    m = re.match(r"^== (\w+)/(\w+)/(\S+) \|", ln)
    if m:
        cur = (m.group(2), m.group(3))
        ch[cur] = {}
    m = re.match(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+(\S+) / (\S+) / (\S+)$", ln)
    if m and i < 57:
        ch[cur][m.group(1)] = (m.group(2), m.group(3), m.group(4))
print("   pair-levels:", len(ch))
for stat in ("jaccard_top5", "jaccard_top10", "jaccard_top20", "rho20", "rbo090", "rbo095"):
    moved = [k for k, d in ch.items() if stat in d and d[stat][0] != "None" and len(set(d[stat])) > 1]
    print("   {:13s} values differ across the three orders on {} of 8 pair-levels".format(stat, len(moved)))

print()
print("== 5. SHAP\\rebuild\\<p>\\lead_0\\gates.json: E10 and E6 values")
for p in PROBLEMS:
    with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
        g = json.load(fh)
    gates = g["gates"]
    for k in sorted(gates):
        if k.startswith("E10") or k.startswith("E6"):
            print("   {} {} pass={} values={}".format(p, k, gates[k].get("pass"),
                                                    json.dumps(gates[k].get("values"), ensure_ascii=False)))
    print("   {} result={}".format(p, json.dumps(g.get("result"), ensure_ascii=False)))

print()
print("== 6. tables.md files (V3-7: tables_agreed.md a byte copy of the builders' tables.md)")
for rel in ("reconcile/tables_agreed.md", "A/tables.md", "B/tables.md", "reconcile/tables_agreed_v1.md",
            "A/tables_v1.md", "B/tables_v1.md"):
    with open(os.path.join(OUT, *rel.split("/")), "rb") as fh:
        raw = fh.read()
    print("   {:30s} sha256 {}  lines {}".format(rel, hashlib.sha256(raw).hexdigest(), raw.count(b"\n")))
with open(os.path.join(OUT, "reconcile", "cells.json"), encoding="utf-8") as fh:
    cj = json.load(fh)
print("   reconcile/cells.json tables_file = {!r}; spec = {!r}; entries {}".format(
    cj.get("tables_file"), cj.get("spec"), len(cj.get("entries", []))))
