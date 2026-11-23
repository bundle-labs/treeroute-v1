"""Read-only: rebuild report.md section 6's B1 pair table from A's results.json (3 decimals, correct rounding of the
stored binary value) and compare it cell by cell with the report's rows."""
import json
import re
from decimal import Decimal, ROUND_HALF_UP

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))
REP = open(V + r"\reconcile\report.md", encoding="utf-8").read().split("\n")


def r3(x):
    return "%.3f" % x


def r3_double(x):
    # rounding first to 4 decimals and then to 3 (a common hand-rounding path)
    y = float("%.4f" % x)
    return str(Decimal(repr(y)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def cell(o, with_ci=True):
    v = o["value"]
    if v is None:
        return "None"
    s = r3(v)
    if with_ci and o.get("ci_low") is not None:
        s += " [%s, %s]" % (r3(o["ci_low"]), r3(o["ci_high"]))
    return s


rows = {}
for line in REP:
    m = re.match(r"\| (fire|pm25|ndvi), (feature|variable) \|", line)
    if m:
        rows[(m.group(1), m.group(2))] = [c.strip() for c in line.strip().strip("|").split("|")]

bad = 0
for (p, lev), cells in rows.items():
    pr = A["b1"][p][lev]["pair_main_b1"]
    prB = B["b1"][p][lev]["pair_main_b1"]
    exp = {
        "pair J": str(int(pr["n_J"]["value"])),
        "Spearman over J": cell(pr["spearman_J"]),
        "top-20-union Spearman": cell(pr["spearman_top20_union"]),
        "Kendall tau-b": cell(pr["kendall_tau_b"]),
        "share distance": cell(pr["tv_shares"]),
    }
    got = {
        "pair J": cells[1], "Spearman over J": cells[2], "top-20-union Spearman": cells[3], "Kendall tau-b": cells[4],
        "share distance": cells[7],
    }
    for k in exp:
        ok = exp[k] == got[k]
        if not ok:
            bad += 1
        print("%-6s %-9s %-22s report=%-26s A=%-26s %s" % (p, lev, k, got[k], exp[k], "ok" if ok else "DIFF"))
        if not ok and k != "pair J":
            nm = {"Spearman over J": "spearman_J", "top-20-union Spearman": "spearman_top20_union",
                  "Kendall tau-b": "kendall_tau_b", "share distance": "tv_shares"}[k]
            o = pr[nm]
            print("        exact A:", repr(o["value"]), repr(o["ci_low"]), repr(o["ci_high"]),
                  "| double-rounded:", r3_double(o["value"]), r3_double(o["ci_low"]), r3_double(o["ci_high"]))
    jac = "%s / %s" % (r3(pr["jaccard_top5"]["value"]), r3(pr["jaccard_top10"]["value"]))
    if pr.get("jaccard_top20") and pr["jaccard_top20"].get("value") is not None:
        jac += " (%s)" % r3(pr["jaccard_top20"]["value"])
    rbo = "%s / %s" % (r3(pr["rbo_p090"]["value"]), r3(pr["rbo_p095"]["value"]))
    for k, e, g in (("Jaccard", jac, cells[5]), ("RBO", rbo, cells[6])):
        ok = e == g
        bad += (not ok)
        print("%-6s %-9s %-22s report=%-26s A=%-26s %s" % (p, lev, k, g, e, "ok" if ok else "DIFF"))
    fam = pr.get("tv_family_shares")
    famB = prB.get("tv_family_shares")
    print("%-6s %-9s %-22s report=%-26s A=%s B=%s" % (p, lev, "family-share distance", cells[8],
                                                       cell(fam) if fam else "none", cell(famB) if famB else "none"))
    sa = pr["sign_agreement"]
    print("%-6s %-9s %-22s report=%-26s A=%s n_det=%s n_finite=%s" % (p, lev, "sign agreement", cells[9],
                                                                       cell(sa), pr["sign_n_determined"]["value"],
                                                                       sa.get("n_finite")))
print("cells differing:", bad)

# the main-row table of section 3 against A (4 decimals)
print()
print("main-row table (section 3) against A's main_row, 4 decimals")
for p in ("coral", "defo", "fire", "pm25", "ndvi"):
    mr = A["problems"][p]["main_row"]
    keys = list(mr.keys())
    print(p, "main_row keys:", keys)
    for k in ("kendall_w", "spearman_top20_union_median", "spearman_top20_union_min", "spearman_top20_union_max",
              "rbo_p090_vs_consensus", "own_history_share_treeroute", "own_history_share_median_rival"):
        o = mr.get(k)
        if isinstance(o, dict) and "value" in o:
            v = o["value"]
            s = ("%.4f" % v) if isinstance(v, float) else str(v)
            if o.get("ci_low") is not None:
                s += " [%.4f, %.4f]" % (o["ci_low"], o["ci_high"])
            print("   %-32s %s n=%s" % (k, s, o.get("n_finite")))
        else:
            print("   %-32s %s" % (k, json.dumps(o)[:150]))
    for k in ("treeroute_top3", "consensus_top3"):
        print("   %-32s %s" % (k, json.dumps(mr.get(k))[:250]))
