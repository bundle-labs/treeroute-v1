"""Build the B1 tables for report.md A6 straight from A's results.json (one rounding step), checking B equal.

Usage: py -3.12 -X utf8 -I b1_tables.py <A results.json> <B results.json> <out .md>
Every value is printed with 3 decimals by one format() call on the stored double. An interval is printed as
[low, high]; its finite count is printed when it is not 2,000. A and B must agree within 1e-12 on every number
printed (the feature-level family-share distance, where A has none by choice C15, is printed from B and marked).
"""
import json
import math
import sys

TOL = 1e-12
PROBLEMS = ["fire", "pm25", "ndvi"]
LEVELS = ["feature", "variable"]
STATS = [("spearman_J", "Spearman over J"), ("spearman_top20_union", "top-20-union Spearman"),
         ("kendall_tau_b", "Kendall tau-b"), ("jaccard_top5", "Jaccard top 5"), ("jaccard_top10", "Jaccard top 10"),
         ("jaccard_top20", "Jaccard top 20"), ("rbo_p090", "RBO p 0.9"), ("rbo_p095", "RBO p 0.95"),
         ("tv_shares", "share distance (TV)"), ("tv_family_shares", "family-share distance (TV)"),
         ("sign_agreement", "sign agreement")]
FAMILIES = [("own_history", "own history"), ("global_indices", "global indices"), ("local_drivers", "local drivers"),
            ("context_and_calendar", "context and calendar"), ("seasonal_normal", "seasonal normal")]
problems_found = []


def f3(x):
    return "%.3f" % x


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isnan(a) or math.isnan(b):
            return math.isnan(a) and math.isnan(b)
        return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))
    return a == b


def check(tag, ea, eb):
    if isinstance(ea, dict) and isinstance(eb, dict):
        for k in ("value", "ci_low", "ci_high", "n_finite"):
            if not close(ea.get(k), eb.get(k)):
                problems_found.append("%s %s: A %r B %r" % (tag, k, ea.get(k), eb.get(k)))
    elif not close(ea, eb):
        problems_found.append("%s: A %r B %r" % (tag, ea, eb))


def cell(e):
    if e is None:
        return "none"
    v, lo, hi, n = e.get("value"), e.get("ci_low"), e.get("ci_high"), e.get("n_finite")
    s = "undefined" if v is None else f3(v)
    if lo is not None and hi is not None:
        s += " [%s, %s]" % (f3(lo), f3(hi))
    if n is not None and n != 2000:
        s += " (%s finite)" % format(int(n), ",")
    return s


def main():
    pa, pb, outp = sys.argv[1:4]
    with open(pa, encoding="utf-8") as f:
        A = json.load(f)["b1"]
    with open(pb, encoding="utf-8") as f:
        B = json.load(f)["b1"]
    L = []
    L.append("Every value below is A's (= B's) number from `results.json` under `b1`, rounded once to three decimals;")
    L.append("an interval is the percentile 95% interval over the 2,000 saved draws, and its number of finite")
    L.append("replicates is shown only where it is not 2,000. The pair is (the main run, the B1 run), with the pair's own J.")
    L.append("")
    for lev in LEVELS:
        L.append("**%s level: the pair (main run, B1 run)**" % lev.capitalize())
        L.append("")
        hdr = ["statistic"] + PROBLEMS
        L.append("| " + " | ".join(hdr) + " |")
        L.append("|" + "---|" * len(hdr))
        nj = ["pair J (players)" if lev == "feature" else "pair J (variables)"]
        for p in PROBLEMS:
            ea, eb = A[p][lev]["pair_main_b1"]["n_J"], B[p][lev]["pair_main_b1"]["n_J"]
            check("%s/%s/n_J" % (p, lev), ea.get("value"), eb.get("value"))
            nj.append(format(int(ea["value"]), ","))
        L.append("| " + " | ".join(nj) + " |")
        for key, label in STATS:
            row = [label]
            for p in PROBLEMS:
                ea = A[p][lev]["pair_main_b1"].get(key)
                eb = B[p][lev]["pair_main_b1"].get(key)
                if key == "tv_family_shares" and lev == "feature":
                    row.append("A none (C15); B %s" % cell(eb))
                    continue
                if key == "jaccard_top20" and ea is None:
                    check("%s/%s/%s" % (p, lev, key), ea, eb)
                    row.append("not defined (J < 200)")
                    continue
                check("%s/%s/%s" % (p, lev, key), ea, eb)
                row.append(cell(ea))
            L.append("| " + " | ".join(row) + " |")
        row = ["signs determined in both / agreeing"]
        for p in PROBLEMS:
            pa_ = A[p][lev]["pair_main_b1"]
            pb_ = B[p][lev]["pair_main_b1"]
            nd = pa_.get("sign_n_determined")
            na = pa_.get("sign_n_agree")
            check("%s/%s/sign_n_determined" % (p, lev), (nd or {}).get("value"),
                  (pb_.get("sign_n_determined") or {}).get("value"))
            if na is not None:
                check("%s/%s/sign_n_agree" % (p, lev), na.get("value"), (pb_.get("sign_n_agree") or {}).get("value"))
            nds = "%d" % nd["value"] if nd and nd.get("value") is not None else "-"
            nas = "%d" % na["value"] if na and na.get("value") is not None else "-"
            row.append("%s / %s" % (nds, nas))
        L.append("| " + " | ".join(row) + " |")
        L.append("")
    L.append("**Variable level: the B1 run's family shares, top 3 and own-history share**")
    L.append("")
    L.append("| family share | " + " | ".join(PROBLEMS) + " |")
    L.append("|---|" + "---|" * len(PROBLEMS))
    for key, label in FAMILIES:
        row = [label]
        for p in PROBLEMS:
            ea, eb = A[p]["variable"]["families"][key], B[p]["variable"]["families"][key]
            check("%s/families/%s" % (p, key), ea, eb)
            row.append(cell(ea))
        L.append("| " + " | ".join(row) + " |")
    row = ["own-history share (as a number of its own)"]
    for p in PROBLEMS:
        ea, eb = A[p]["variable"]["own_history_share"], B[p]["variable"]["own_history_share"]
        check("%s/own_history_share" % p, ea, eb)
        row.append(cell(ea))
    L.append("| " + " | ".join(row) + " |")
    row = ["top 3 variables (share)"]
    for p in PROBLEMS:
        ta, tb = A[p]["variable"]["top3"], B[p]["variable"]["top3"]
        if [t[0] for t in ta] != [t[0] for t in tb]:
            problems_found.append("%s top3 names differ" % p)
        for x, y in zip(ta, tb):
            check("%s/top3/%s" % (p, x[0]), x[1], y[1])
        row.append(", ".join("%s %s" % (n, f3(s)) for n, s in ta))
    L.append("| " + " | ".join(row) + " |")
    L.append("")
    for lev in LEVELS:
        L.append("**%s level: the B1 run's top 10 (share; no interval for a top-k list)**" % lev.capitalize())
        L.append("")
        L.append("| rank | " + " | ".join(PROBLEMS) + " |")
        L.append("|---|" + "---|" * len(PROBLEMS))
        for i in range(10):
            row = [str(i + 1)]
            for p in PROBLEMS:
                ta, tb = A[p][lev]["top10"], B[p][lev]["top10"]
                if ta[i][0] != tb[i][0]:
                    problems_found.append("%s/%s top10 rank %d names differ" % (p, lev, i + 1))
                check("%s/%s/top10/%d" % (p, lev, i + 1), ta[i][1], tb[i][1])
                row.append("%s %s" % (ta[i][0], f3(ta[i][1])))
            L.append("| " + " | ".join(row) + " |")
        L.append("")
    L.append("Each B1 player's I, share and signed mean, with its interval, is in A's and B's `results.json` under")
    L.append("`b1/<problem>/<level>/importance/players`.")
    with open(outp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", outp)
    print("A-vs-B problems:", len(problems_found))
    for x in problems_found[:40]:
        print("  ", x)
    for p in PROBLEMS:
        for lev in LEVELS:
            pr = A[p][lev]["pair_main_b1"]
            print("check %s %s: tau-b %r | top20u hi %r | spearmanJ %r" % (
                p, lev, pr["kendall_tau_b"]["value"], pr["spearman_top20_union"]["ci_high"], pr["spearman_J"]["value"]))


if __name__ == "__main__":
    main()
