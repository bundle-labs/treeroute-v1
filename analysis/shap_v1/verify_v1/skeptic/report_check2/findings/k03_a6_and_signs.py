# Read-only. (1) Rebuild every A6 cell of report.md v2 independently from A's and B's results.json (one
# rounding step) and compare with the printed text. (2) List every main-pair sign-agreement interval with
# fewer than 2,000 finite replicates, all problems and levels, in A and B. (3) Print the B1 records that
# summary.json keeps side by side (status, run facts, identity) and whether A's equal B's.
import json
import math
import re

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
REPORT = V + r"\reconcile\report.md"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))


def r3(x):
    # round once, half-even on the exact binary value as Python's format does
    return format(x, ".3f")


def cell(e):
    if e is None:
        return "none"
    v, lo, hi, n = e.get("value"), e.get("ci_low"), e.get("ci_high"), e.get("n_finite")
    s = "undefined" if v is None else r3(v)
    if lo is not None and hi is not None:
        s += " [%s, %s]" % (r3(lo), r3(hi))
    if n is not None and n != 2000:
        s += " (%s finite)" % format(int(n), ",")
    return s


lines = open(REPORT, encoding="utf-8").read().split("\n")
s = next(i for i, l in enumerate(lines) if l.startswith("### A6."))
e = next(i for i, l in enumerate(lines) if l.startswith("### A7."))
a6 = lines[s:e]

# parse tables: map (table title, row label) -> [cells]
tables = {}
title = None
for l in a6:
    if l.startswith("**") and l.endswith("**"):
        title = l.strip("*")
        tables[title] = {}
    elif l.startswith("|") and title and not l.startswith("|---"):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        tables[title][cells[0]] = cells[1:]
print("A6 tables:", list(tables))

P = ["fire", "pm25", "ndvi"]
STATS = [("spearman_J", "Spearman over J"), ("spearman_top20_union", "top-20-union Spearman"),
         ("kendall_tau_b", "Kendall tau-b"), ("jaccard_top5", "Jaccard top 5"), ("jaccard_top10", "Jaccard top 10"),
         ("jaccard_top20", "Jaccard top 20"), ("rbo_p090", "RBO p 0.9"), ("rbo_p095", "RBO p 0.95"),
         ("tv_shares", "share distance (TV)"), ("tv_family_shares", "family-share distance (TV)"),
         ("sign_agreement", "sign agreement")]
bad = 0
ncells = 0
for lev, tt in (("feature", "Feature level: the pair (main run, B1 run)"),
                ("variable", "Variable level: the pair (main run, B1 run)")):
    T = tables[tt]
    for key, label in STATS:
        for j, p in enumerate(P):
            ea = A["b1"][p][lev]["pair_main_b1"].get(key)
            eb = B["b1"][p][lev]["pair_main_b1"].get(key)
            printed = T[label][j]
            if key == "tv_family_shares" and lev == "feature":
                exp = "A none (C15); B %s" % cell(eb)
                assert ea is None, (p, lev, key, ea)
            elif key == "jaccard_top20" and ea is None:
                exp = "not defined (J < 200)"
            else:
                exp = cell(ea)
                # B equal?
                if cell(eb) != exp:
                    print("  A/B text differs", p, lev, key, cell(ea), cell(eb))
            ncells += 1
            if printed != exp:
                bad += 1
                print("MISMATCH", lev, label, p, "printed", printed, "expected", exp)
    # n_J
    row = T["pair J (players)" if lev == "feature" else "pair J (variables)"]
    for j, p in enumerate(P):
        v = A["b1"][p][lev]["pair_main_b1"]["n_J"]["value"]
        ncells += 1
        if row[j] != format(int(v), ","):
            bad += 1
            print("MISMATCH n_J", lev, p, row[j], v)
    row = T["signs determined in both / agreeing"]
    for j, p in enumerate(P):
        pa = A["b1"][p][lev]["pair_main_b1"]
        nd = pa.get("sign_n_determined") or {}
        na = pa.get("sign_n_agree") or {}
        exp = "%s / %s" % (nd.get("value"), na.get("value"))
        ncells += 1
        if row[j] != exp:
            bad += 1
            print("MISMATCH signs", lev, p, row[j], exp)
        # intervals of counts exist?
        print("  counts", lev, p, "n_determined", nd, "n_agree", na)

T = tables["Variable level: the B1 run's family shares, top 3 and own-history share"]
FAM = [("own_history", "own history"), ("global_indices", "global indices"), ("local_drivers", "local drivers"),
       ("context_and_calendar", "context and calendar"), ("seasonal_normal", "seasonal normal")]
for key, label in FAM:
    for j, p in enumerate(P):
        exp = cell(A["b1"][p]["variable"]["families"][key])
        ncells += 1
        if T[label][j] != exp:
            bad += 1
            print("MISMATCH family", key, p, T[label][j], exp)
for j, p in enumerate(P):
    exp = cell(A["b1"][p]["variable"]["own_history_share"])
    ncells += 1
    if T["own-history share (as a number of its own)"][j] != exp:
        bad += 1
        print("MISMATCH ohs", p)
    exp = ", ".join("%s %s" % (n, r3(v)) for n, v in A["b1"][p]["variable"]["top3"])
    ncells += 1
    if T["top 3 variables (share)"][j] != exp:
        bad += 1
        print("MISMATCH top3", p, T["top 3 variables (share)"][j], exp)

for lev, tt in (("feature", "Feature level: the B1 run's top 10 (share; no interval for a top-k list)"),
                ("variable", "Variable level: the B1 run's top 10 (share; no interval for a top-k list)")):
    T = tables[tt]
    for i in range(10):
        for j, p in enumerate(P):
            n, v = A["b1"][p][lev]["top10"][i][0], A["b1"][p][lev]["top10"][i][1]
            exp = "%s %s" % (n, r3(v))
            ncells += 1
            if T[str(i + 1)][j] != exp:
                bad += 1
                print("MISMATCH top10", lev, i + 1, p, T[str(i + 1)][j], exp)
print("A6 cells checked:", ncells, "mismatches:", bad)

# rounding-boundary report: values within 5e-7 of a 3-decimal half-way point
def near_half(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return False
    y = abs(x) * 1000
    return abs((y - math.floor(y)) - 0.5) < 5e-4
for p in P:
    for lev in ("feature", "variable"):
        for key, _ in STATS:
            ea = A["b1"][p][lev]["pair_main_b1"].get(key)
            if isinstance(ea, dict):
                for k in ("value", "ci_low", "ci_high"):
                    if near_half(ea.get(k)):
                        print("  near half-way:", p, lev, key, k, repr(ea.get(k)))

# (2) main-pair sign agreement with n_finite < 2000
print("=== main-pair sign agreement with n_finite != 2000 (A; B compared) ===")
for p, pd in A["problems"].items():
    for lev, ld in pd["levels"].items():
        for pair, st in ld["pairs"].items():
            sa = st.get("sign_agreement")
            if not isinstance(sa, dict):
                continue
            n = sa.get("n_finite")
            if n != 2000:
                sb = B["problems"][p]["levels"][lev]["pairs"][pair].get("sign_agreement")
                same = all((sa.get(k) == sb.get(k)) or (isinstance(sa.get(k), float) and isinstance(sb.get(k), float)
                           and abs(sa.get(k) - sb.get(k)) < 1e-12) for k in ("value", "ci_low", "ci_high", "n_finite"))
                print("  %s %s %s: value %r [%r, %r] n_finite %r | B same %s" % (
                    p, lev, pair, sa.get("value"), sa.get("ci_low"), sa.get("ci_high"), n, same))
