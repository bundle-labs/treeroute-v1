# Skeptic (version 5 check, item 2): are the NEW texts of V5-1 to V5-4 true to their sources? Read-only; prints only
# (counts, names and short values; no path of a user folder).
#  V5-1  per problem and model (meta.json players, variable_map, duplicates_merged; per_lead.json families): the
#        family "context and calendar" must be exactly the variables of the router-context (c__) players that are not
#        merged with a tree input, and every merged context column must sit in its tree column's variable and family;
#        NDVI's router context counted (unmerged + merged); any x__ player whose name, after its prefix, equals a
#        context column's name (a copy by name that was not merged).
#  V5-2  coral (SHAP\out\coral\lead_0\treeroute\background_keys.parquet against rows.parquet): every background visit
#        dated strictly before the explained visit, by `time` and by the date after "|"; `time` as the date's day
#        ordinal on both files; the explained visit never in its own pool; the latest background date (the cut);
#        great-circle distances from the explained visit's reef site (the site key's two numbers read as latitude and
#        longitude); the engine's pool rule (route/neighbour.py, read only) printed from its source lines.
#  V5-3  the five rebuild gates.json E5 values (pass, trees, whether rebuilt == run); the engine's bank fingerprint
#        (fit/bank.py, read only): which arrays it hashes.
#  V5-4  the five rebuild gates.json E3m values.rule.
#  Quotes: PROTOCOL L182, L372-375, L381-382, L393-394, L487-488, L654; GLOSSARY rows tree bank, corrector, placebo,
#        neighbour router, router context, router fit rows.
import datetime as dt
import json, math, os, re, sys
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
SHAP = r"D:\treeroute\analysis\shap_v1"

print("#### V5-1")
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    base = SHAP + r"\out\%s\lead_0" % p
    PL = json.load(open(base + r"\compare\per_lead.json", encoding="utf-8"))
    fam = PL["families"]
    cc = sorted(v for v, f in fam.items() if f == "context and calendar")
    rows = []
    folders = list(PL["models"]) + (["treeroute_B1"] if os.path.isdir(os.path.join(base, "treeroute_B1")) else [])
    for m in folders:
        M = json.load(open(os.path.join(base, m, "meta.json"), encoding="utf-8"))
        pl = list(M["players"])
        vm = M["variable_map"]
        dm = M.get("duplicates_merged") or {}
        cpl = [x for x in pl if x.startswith("c__")]
        un_vars = sorted(set(vm[x] for x in cpl))
        un_fams = sorted(set(fam.get(v) for v in un_vars))
        ok_family = un_vars == [v for v in cc if any(vm.get(x) == v for x in cpl)] and set(un_fams) <= {"context and calendar"}
        merged = []
        for c, x in dm.items():
            merged.append((c, x, x in pl, c in pl, vm.get(x), fam.get(vm.get(x))))
        cnames = {re.sub(r"^c__ctx[:_]", "", x) for x in cpl} | {re.sub(r"^c__ctx[:_](top5:)?", "", c) for c in dm}
        xnames = {re.sub(r"^x__", "", x) for x in pl if x.startswith("x__")}
        same_name_unmerged = sorted(n for n in {re.sub(r"^c__ctx[:_]", "", x) for x in cpl} if n in xnames)
        rows.append((m, len(cpl), len(dm), un_vars, un_fams, ok_family, same_name_unmerged))
        if merged and m in ("treeroute", "treeroute_B1"):
            for t in merged:
                print("   %s %s: merged %s -> %s (tree player present %s, context player present %s) | variable %r | family %r" % (
                    p, m, t[0], t[1], t[2], t[3], t[4], t[5]))
    print("%-5s family 'context and calendar' = %s" % (p, cc))
    for m, nc, nd, uv, uf, ok, sn in rows:
        print("      %-18s unmerged c__ players %d, merged %d (router context %d) | their variables %s, families %s | family == their variables: %s | x__ named like an unmerged context column: %s" % (
            m, nc, nd, nc + nd, uv, uf, ok, sn))

print("#### V5-2")
base = SHAP + r"\out\coral\lead_0\treeroute"
B = pd.read_parquet(base + r"\background_keys.parquet")
R = pd.read_parquet(base + r"\rows.parquet", columns=["row", "unit", "time", "group"])
date = lambda u: str(u).split("|")[1]
site = lambda u: str(u).split("|")[0]
ordinal = lambda s: dt.date.fromisoformat(s).toordinal()
print("background rows %d (distinct rows %d, per row %s); sample rows %d (distinct units %d)" % (
    len(B), B.row.nunique(), sorted(set(B.groupby("row").size())), len(R), R.unit.nunique()))
print("`time` == ordinal of the date after '|': background %d mismatches, sample rows %d mismatches" % (
    int((B.unit.map(lambda u: ordinal(date(u))) != B.time).sum()), int((R.unit.map(lambda u: ordinal(date(u))) != R.time).sum())))
M = B.merge(R.rename(columns={"unit": "x_unit", "time": "x_time", "group": "x_group"}), on="row", how="left", validate="many_to_one")
print("every background row has its sample row: %s" % M.x_unit.notna().all())
gap = M.x_time - M.time
gd = M.x_unit.map(lambda u: dt.date.fromisoformat(date(u))) - M.unit.map(lambda u: dt.date.fromisoformat(date(u)))
print("dated on or after the explained visit: by time %d, by date string %d | the explained visit itself in its pool: %d" % (
    int((gap <= 0).sum()), int((gd.map(lambda d: d.days) <= 0).sum()), int((M.unit == M.x_unit).sum())))
print("days before the explained visit: min %d, median %d, max %d" % (gap.min(), int(gap.median()), gap.max()))
print("background dates: earliest %s, latest %s | sample rows' dates: earliest %s, latest %s" % (
    min(M.unit.map(date)), max(M.unit.map(date)), min(R.unit.map(date)), max(R.unit.map(date))))
print("same reef site key: %d background visits in %d sample rows; distinct background visits %d; distinct sites: sample %d, background %d" % (
    int((M.unit.map(site) == M.x_unit.map(site)).sum()), int(M[M.unit.map(site) == M.x_unit.map(site)].row.nunique()),
    M.unit.nunique(), R.unit.map(site).nunique(), M.unit.map(site).nunique()))


def latlon(u):
    parts = site(u).split("_")
    return float(parts[-2]), float(parts[-1])


fmt_ok = all(re.fullmatch(r"\d{3}_-?\d+\.\d+_-?\d+\.\d+", site(u)) for u in pd.concat([M.unit, M.x_unit]).unique())
print("site keys all of the form <code>_<number>_<number>: %s" % fmt_ok)
a = np.array([latlon(u) for u in M.unit])
b = np.array([latlon(u) for u in M.x_unit])
p = math.pi / 180
h = np.sin((a[:, 0] - b[:, 0]) * p / 2) ** 2 + np.cos(a[:, 0] * p) * np.cos(b[:, 0] * p) * np.sin((a[:, 1] - b[:, 1]) * p / 2) ** 2
km = 2 * 6371.0088 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
M["km"] = km
far = M.groupby("row").km.max()
print("distance from the explained visit's site (km, Earth radius 6371.0088): median %.1f, 90%% %.1f, 99%% %.1f, max %.1f | zero distance %d | per sample row's farthest: median %.1f, max %.1f" % (
    np.median(km), np.quantile(km, 0.9), np.quantile(km, 0.99), km.max(), int((km == 0).sum()), far.median(), far.max()))
print("background visits in another region than the explained visit's (group code = site key's first part): %d of %d" % (
    int((M.unit.map(lambda u: site(u).split("_")[0]) != M.x_unit.map(lambda u: site(u).split("_")[0])).sum()), len(M)))
src = open(os.path.join(ROOT, "engine", "treeroute", "route", "neighbour.py"), encoding="utf-8").read().split("\n")
for k in (16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 365, 372, 374):
    print("   neighbour.py L%d: %s" % (k, src[k - 1].strip()[:150]))
K = open(os.path.join(ROOT, "engine", "treeroute", "engine_constants.py"), encoding="utf-8").read()
print("   engine_constants:", re.findall(r"NEIGHBOUR_POOL_\w+ = _c\(\"[^\"]+\", \d+\)", K))

print("#### V5-3 and V5-4")
for p in ["pm25", "ndvi", "fire", "defo", "coral"]:
    g = json.load(open(SHAP + r"\rebuild\%s\lead_0\gates.json" % p, encoding="utf-8"))
    G = g["gates"]
    e5 = G["E5_bank_fingerprint"]
    v = e5["values"]
    e3m = G.get("E3m_recorded_path_map")
    print("%-5s E5 pass %s | keys %s | rebuilt == run: %s | trees %s | role %r | E3m: %s" % (
        p, e5["pass"], sorted(v), v.get("rebuilt") == v.get("run"), v.get("trees"), v.get("role"),
        "pass %s, rule %r, files %d" % (e3m["pass"], e3m["values"].get("rule"), len(e3m["values"].get("files", []))) if e3m else "absent"))
bk = open(os.path.join(ROOT, "engine", "treeroute", "fit", "bank.py"), encoding="utf-8").read().split("\n")
for k in list(range(345, 347)) + [352, 354, 355] + list(range(368, 375)) + [716, 717, 733]:
    print("   bank.py L%d: %s" % (k, bk[k - 1].rstrip()[:150]))
tr = open(SHAP + r"\scripts\tr_rebuild.py", encoding="utf-8").read().split("\n")
for k in range(736, 744):
    print("   tr_rebuild.py L%d: %s" % (k, tr[k - 1].rstrip()[:150]))
print("   tr_rebuild.py: lines that read the run's fingerprint:", [(k + 1, x.strip()[:110]) for k, x in enumerate(tr) if "want_fp" in x][:4])

print("#### quotes")
P = open(SHAP + r"\PROTOCOL.md", encoding="utf-8").read().split("\n")
for k in (182, 372, 375, 381, 382, 393, 394, 487, 488, 654):
    print("   PROTOCOL L%d: %s" % (k, P[k - 1].rstrip()))
G = open(os.path.join(ROOT, "paper", "draft", "GLOSSARY.md"), encoding="utf-8").read().split("\n")
for k, x in enumerate(G, 1):
    if x.startswith(("| **tree bank**", "| **corrector**", "| **placebo**", "| **neighbour router**", "| **router context**",
                     "| **router fit rows**")):
        print("   GLOSSARY L%d: %s" % (k, re.sub(r"<!--.*?-->", "", x).rstrip()[:200]))
