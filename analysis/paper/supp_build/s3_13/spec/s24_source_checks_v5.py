# s24_source_checks_v5.py - version 5 of TABLE_SPEC.md (2026-11-17): cheap read-only checks of the claims of the
# change order OUT\_brief\fix_order_v5.md against the sources it names:
#   1. SHAP\PROTOCOL.md lines 182, 375, 381-382, 393-397 and 487-488;
#   2. each model's SHAP\out\<p>\lead_0\<model>\meta.json `duplicates_merged` on all five problems (the models of
#      per_lead.json `models`, and treeroute_B1 where it exists), NDVI's context players and the variables and
#      families (per_lead.json `families`) of the merged columns, and each problem's context-and-calendar family;
#   3. coral's SHAP\out\coral\lead_0\treeroute\background_keys.parquet against rows.parquet: the same reef site (the
#      part of the unit key before "|") and the dates (`time`, a day ordinal, and the date after "|");
#   4. the GLOSSARY rows neighbour router, tree bank, corrector, placebo (and router context);
#   5. the E3m `values.rule` of the rebuild records SHAP\rebuild\<p>\lead_0\gates.json that have E3m (and, for V5-3,
#      the keys, tree count and role of E5's values on all five);
#   6. SHAP\scripts\tr_rebuild.py lines 736-740 (read as text, not run).
# Prints only; writes nothing; runs no script of SHAP, V or the engine. Any string that holds a user folder is masked
# before printing. Run from this folder: py -3.9 -I -B s24_source_checks_v5.py
import datetime
import json
import math
import os
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)                                  # ROOT\paper\supp_build\s3_13
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = "D:/treeroute/analysis/shap_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def mask(s):
    return re.sub(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\"']+", "<user folder>", s)


def lines_of(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def show(label, L, nums):
    print("--", label)
    for n in nums:
        print("   L{}: {}".format(n, mask(L[n - 1])))


print("== 1. SHAP\\PROTOCOL.md")
P = lines_of(SHAP + "/PROTOCOL.md")
show("E5 (V5-3)", P, [182])
show("B2 on coral (V5-2)", P, [375])
show("what B2 means on coral (V5-2)", P, [381, 382])
show("feature level: a context copy of a tree column is the same player (V5-1)", P, [393, 394, 395, 396, 397])
show("variable level: context columns and duplicates (V5-1)", P, [487, 488])

print()
print("== 2. meta.json duplicates_merged (every model folder of per_lead.json models, and treeroute_B1)")
fam_cc = {}
for p in PROBLEMS:
    PL = jload(SHAP + "/out/" + p + "/lead_0/compare/per_lead.json")
    models = list(PL["models"])
    extra = ["treeroute_B1"] if os.path.isdir(SHAP + "/out/" + p + "/lead_0/treeroute_B1") else []
    fams = PL["families"]
    fam_cc[p] = sorted(v for v, f in fams.items() if f == "context and calendar")
    for m in models + extra:
        meta = jload(SHAP + "/out/" + p + "/lead_0/" + m + "/meta.json")
        dm = meta.get("duplicates_merged", "<no key>")
        ctx_players = [x for x in meta.get("players", []) if x.startswith("c__")]
        print("  {:5s} {:19s} duplicates_merged: {} entries {}; c__ players: {} {}".format(
            p, m, len(dm) if isinstance(dm, dict) else dm,
            "" if not dm else json.dumps(dm, ensure_ascii=False), len(ctx_players), ctx_players))
        if p == "ndvi" and m == "treeroute":
            vm = meta["variable_map"]
            for c, t in dm.items():
                v = vm.get(t)
                print("      {} -> {}: variable {!r} (meta variable_map), family {!r} (per_lead.json families);"
                      " the copy's own name in variable_map: {}".format(c, t, v, fams.get(v), c in vm))
            nine = [x for x in ctx_players] + list(dm)
            print("      router context of NDVI's treeroute: {} c__ players + {} merged c__ctx:top5 copies = {}"
                  " columns".format(len(ctx_players), len(dm), len(nine)))
    print("  {:5s} per_lead.json families, 'context and calendar': {}".format(p, fam_cc[p]))

print()
print("== 3. coral: background_keys.parquet against rows.parquet (SHAP\\out\\coral\\lead_0\\treeroute)")
base = SHAP + "/out/coral/lead_0/treeroute/"
bk = pd.read_parquet(base + "background_keys.parquet", columns=["row", "unit", "time"])
rw = pd.read_parquet(base + "rows.parquet", columns=["row", "unit", "time"])
print("  background_keys rows {}, sample rows {} (distinct row ids {})".format(len(bk), len(rw), rw["row"].nunique()))
per_row = bk.groupby("row").size()
print("  background visits per sample row: min {} max {}; sample rows with a background {}".format(
    int(per_row.min()), int(per_row.max()), len(per_row)))
j = bk.merge(rw, on="row", how="left", suffixes=("_b", "_x"), validate="many_to_one")
if j["unit_x"].isna().any():
    print("  FAIL: background rows whose sample row is not in rows.parquet:", int(j["unit_x"].isna().sum()))
site_b = j["unit_b"].str.split("|", n=1).str[0]
site_x = j["unit_x"].str.split("|", n=1).str[0]
date_b = j["unit_b"].str.split("|", n=1).str[1]
date_x = j["unit_x"].str.split("|", n=1).str[1]
bad_keys = int((j["unit_b"].str.count(r"\|") != 1).sum() + (j["unit_x"].str.count(r"\|") != 1).sum())
print("  unit keys without exactly one '|': {}".format(bad_keys))
ordd = lambda t: datetime.date.fromordinal(int(t)).isoformat()  # noqa: E731
mism_b = int((j["time_b"].map(ordd) != date_b).sum())
mism_x = int((rw["time"].map(ordd) != rw["unit"].str.split("|", n=1).str[1]).sum())
print("  `time` as a day ordinal equals the date after '|': background mismatches {}, sample-row mismatches {}".format(
    mism_b, mism_x))
same = site_b == site_x
print("  background visits at the explained visit's own reef site: {} of {}; in {} of {} sample rows".format(
    int(same.sum()), len(j), int(j.loc[same, "row"].nunique()), len(rw)))
print("  background visits dated on or after the explained visit (time): {}; the same site and on or after: {}; "
      "the explained visit itself (same unit key): {}".format(
          int((j["time_b"] >= j["time_x"]).sum()), int((same & (j["time_b"] >= j["time_x"])).sum()),
          int((j["unit_b"] == j["unit_x"]).sum())))
print("  ... by the date text after '|': on or after {}".format(int((date_b >= date_x).sum())))
gap = (j["time_x"] - j["time_b"])
print("  days from a background visit to the explained visit: min {}, median {}, max {}".format(
    int(gap.min()), float(gap.median()), int(gap.max())))


def latlon(site):
    parts = site.split("_")
    return float(parts[-2]), float(parts[-1])


def km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2, dl = math.radians(la1), math.radians(la2), math.radians(lo2 - lo1)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(min(1.0, math.sqrt(h)))


try:
    d = pd.Series([km(latlon(a), latlon(b)) for a, b in zip(site_x, site_b)])
    j["km"] = d.values
    mx = j.groupby("row")["km"].max()
    print("  site distance (haversine on the key's two numbers, read as latitude and longitude), km: per background"
          " visit median {:.1f}, max {:.1f}; per sample row, the farthest visit: median {:.1f}, max {:.1f}".format(
              float(d.median()), float(d.max()), float(mx.median()), float(mx.max())))
except (ValueError, IndexError) as exc:
    print("  site distance not computed:", exc)
print("  sample rows: {} reef sites (the part before '|')".format(rw["unit"].str.split("|", n=1).str[0].nunique()))

print()
print("== 4. ROOT\\paper\\draft\\GLOSSARY.md (rows by paper term)")
G = lines_of(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"))
for t in ["neighbour router", "tree bank", "corrector", "placebo", "router context"]:
    hits = [i for i, ln in enumerate(G, 1) if re.match(r"^\| \*\*" + re.escape(t) + r"\*\*", ln)]
    if len(hits) != 1:
        print("   {}: found {} rows".format(t, len(hits)))
    for i in hits:
        print("   L{}: {}".format(i, mask(G[i - 1])))

print()
print("== 5. SHAP\\rebuild\\<p>\\lead_0\\gates.json: E3m values.rule (and E5's value keys)")
for p in PROBLEMS:
    g = jload(SHAP + "/rebuild/" + p + "/lead_0/gates.json")["gates"]
    keys = [k for k in g if k.startswith("E3m")]
    if not keys:
        print("  {:5s} no E3m gate (E3a values.path_map = {})".format(
            p, g.get("E3a_inputs_before_read", {}).get("values", {}).get("path_map")))
    for k in keys:
        v = g[k]["values"]
        print("  {:5s} {} pass={} rule={!r} files={}".format(p, k, g[k].get("pass"), v.get("rule"),
                                                           len(v.get("files", []))))
    e5 = g.get("E5_bank_fingerprint", {})
    v5 = e5.get("values", {})
    print("  {:5s} E5_bank_fingerprint pass={} keys={} trees={} role={!r}".format(
        p, e5.get("pass"), list(v5), v5.get("trees"), v5.get("role")))

print()
print("== 6. SHAP\\scripts\\tr_rebuild.py (read as text, not run)")
T = lines_of(SHAP + "/scripts/tr_rebuild.py")
show("E5 fingerprint", T, [736, 737, 738, 739, 740])
