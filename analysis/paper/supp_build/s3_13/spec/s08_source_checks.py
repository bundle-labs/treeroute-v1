# s08_source_checks.py - version-2 maintenance of TABLE_SPEC.md: cheap read-only checks of the
# change order's claims (fix_order_v2.md) against the sources it names. Prints only; writes nothing.
# Run: py -3.9 -I -B s08_source_checks.py
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

SHAP = "D:/treeroute/analysis/shap_v1"
V = SHAP + "/verify_v1"
PROBLEMS = ["pm25", "ndvi", "fire", "defo", "coral"]


def short(x, n=300):
    s = json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + " ...(" + str(len(s)) + " chars)"


print("== 1. gates.json: E10, E5, E8, E3m, E5a per problem")
for p in PROBLEMS:
    with open(SHAP + "/rebuild/" + p + "/lead_0/gates.json", encoding="utf-8") as fh:
        g = json.load(fh)
    gates = g["gates"]
    print("--", p, "result:", short(g.get("result")))
    for k in sorted(gates):
        if k.startswith("E10") or k.startswith("E5") or k.startswith("E8") or k.startswith("E3m"):
            gk = gates[k]
            vals = gk.get("values", {})
            print("  ", k, "pass=", gk.get("pass"), "value keys=", sorted(vals) if isinstance(vals, dict) else type(vals))
            if k.startswith("E10"):
                for vk in sorted(vals):
                    print("      E10", vk, "=", short(vals[vk], 400))
            if k.startswith("E8"):
                for vk in ("bit_identical", "within_relative_tolerance", "rows_checked", "pre_bit_equal",
                           "arm_bit_equal", "max_abs_pre", "max_rel_pre", "rows_outside_tolerance"):
                    if vk in vals:
                        print("      E8", vk, "=", short(vals[vk]))
            if k.startswith("E3m"):
                fl = vals.get("files")
                print("      E3m files type", type(fl).__name__, "len", len(fl) if isinstance(fl, list) else None)

print()
print("== 2. families.parquet sums, and own-history family share vs the sum of hist_* importance shares")
import pandas as pd

for p in PROBLEMS:
    c = SHAP + "/out/" + p + "/lead_0/compare/"
    fam = pd.read_parquet(c + "families.parquet")
    imp = pd.read_parquet(c + "importance.parquet")
    with open(c + "per_lead.json", encoding="utf-8") as fh:
        pl = json.load(fh)
    fammap = pl["families"]
    for m in sorted(fam["model"].unique()):
        fm = fam[fam["model"] == m]
        tot = float(fm["share"].sum())
        oh = float(fm.loc[fm["family"] == "own history", "share"].iloc[0])
        iv = imp[(imp["level"] == "variable") & (imp["model"] == m)]
        # variables mapped to the own-history family by per_lead.json families
        if isinstance(fammap, dict):
            ohv = fammap.get("own history")
            if ohv is None:
                ohv = [v for v, f in fammap.items() if f == "own history"]
        else:
            ohv = []
        ohv = list(ohv) if ohv is not None else []
        s_imp = float(iv[iv["player"].isin(ohv)]["share"].sum())
        print("  {:5s} {:20s} family-share sum {:.15f}  own-history family {:.6f}  sum of own-history variables' "
              "importance shares {:.6f}  ({} variables)".format(p, m, tot, oh, s_imp, len(ohv)))
    if p == "pm25":
        print("   per_lead.json families type:", type(fammap).__name__, short(fammap, 200))

print()
print("== 3. text formats (G2): BOM, CRLF")
files = [SHAP + "/SAMPLE_REGISTER.txt"] + [SHAP + "/logs/tr_shap_" + p + "_lead0.log" for p in PROBLEMS] + [
    V + "/_lead/outputs/bardl_maxima.txt"]
for f in files:
    try:
        with open(f, "rb") as fh:
            b = fh.read()
    except FileNotFoundError:
        print("  missing:", f)
        continue
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    print("  {}: bytes {}, BOM {}, CRLF {}, LF {}, bare CR {}".format(
        f.replace(SHAP, "SHAP"), len(b), b[:3] == b"\xef\xbb\xbf", crlf, lf, b.count(b"\r") - crlf))

print()
print("== 4. rival_ridge exactness.json keys (which script wrote it), pm25")
with open(SHAP + "/out/pm25/lead_0/rival_ridge/exactness.json", encoding="utf-8") as fh:
    ex = json.load(fh)
print("  keys:", sorted(ex))
for k in ("script", "writer", "tool", "check", "note", "stage", "pass"):
    if k in ex:
        print("  ", k, "=", short(ex[k]))
with open(SHAP + "/out/pm25/lead_0/rival_ridge/ridge_shap_exactness.json", encoding="utf-8") as fh:
    rx = json.load(fh)
print("  ridge_shap_exactness keys:", sorted(rx))
for k in ("script", "writer", "tool", "stage", "pass", "rival_shap_exactness_json", "row_by_row_copy"):
    if k in rx:
        print("  ", k, "=", short(rx[k]))

print()
print("== 5. bardl_maxima.txt first block: is 'spread' = highest minus lowest of the three values? (C3)")
import re

PAT = re.compile(r"^\s+(jaccard_top5|jaccard_top10|jaccard_top20|rho20|rbo090|rbo095)\s+spread ([0-9.]+) -> \S+ "
                 r"\(3 sig\. \S+\) at (\w+)/(\w+)/(\S+); values ([0-9.\-]+) / ([0-9.\-]+) / ([0-9.\-]+)$")
with open(V + "/_lead/outputs/bardl_maxima.txt", encoding="utf-8-sig") as fh:
    lines = fh.read().split("\n")
print("  line 1:", lines[0])
for n in range(2, 8):
    m = PAT.match(lines[n - 1])
    if not m:
        print("  line", n, "NO MATCH:", lines[n - 1])
        continue
    vals = [float(m.group(i)) for i in (6, 7, 8)]
    spread = float(m.group(2))
    move = max(abs(vals[1] - vals[0]), abs(vals[2] - vals[0]))
    print("  line {} {:14s} spread {!r}  max-min {!r}  largest move from value 1 {!r}  values {}".format(
        n, m.group(1), spread, max(vals) - min(vals), move, vals))
