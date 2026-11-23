"""Read-only: check every decimal number in report.md's main-row table (section 3) and B1 family table (section 6)
against A's results.json, by single correct rounding of the stored value."""
import json
import re

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
OFF = {}
for p in ("coral", "defo", "fire", "pm25", "ndvi"):
    OFF[p] = json.load(open(r"D:\treeroute\analysis\shap_v1\out\%s\lead_0\compare\AW4_main_row.json" % p, encoding="utf-8"))
REP = open(V + r"\reconcile\report.md", encoding="utf-8").read().split("\n")


def f4(x):
    return "%.4f" % x


def f3(x):
    return "%.3f" % x


def iv4(o):
    return "%s [%s, %s]" % (f4(o["value"]), f4(o["ci_low"]), f4(o["ci_high"]))


bad = 0
for p in ("coral", "defo", "pm25", "ndvi"):
    mr = A["problems"][p]["main_row"]
    exp = {
        "Kendall's W": iv4(mr["kendall_w"]),
        "median top-20-union Spearman vs rivals (range)": "%s (%s to %s)" % (
            iv4(mr["spearman_top20_union_median"]), f4(mr["spearman_top20_union_min"]["value"]),
            f4(mr["spearman_top20_union_max"]["value"])),
        "RBO (p 0.9) vs consensus": iv4(mr["rbo_p090_vs_consensus"]),
    }
    if p != "coral":
        exp["own-history share, treeroute / median rival"] = "%s / %s" % (iv4(mr["own_history_share_treeroute"]),
                                                                         iv4(mr["own_history_share_median_rival"]))
    t3 = ", ".join(n for n, s in mr["treeroute_top3"])
    c3 = ", ".join(n for n, s in mr["consensus_top3"])
    exp["treeroute top 3 / consensus top 3"] = "%s / %s" % (t3, c3)
    for line in REP:
        m = re.match(r"\| %s \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$" % p, line)
        if not m:
            continue
        name, off = m.group(1), m.group(2)
        if name in exp:
            ok = off == exp[name]
            bad += not ok
            print("%-6s %-48s %s" % (p, name, "ok" if ok else "DIFF report=%s A=%s" % (off, exp[name])))

# fire rows
mr = A["problems"]["fire"]["main_row"]
t3 = ", ".join("%s %s" % (n, f4(s)) for n, s in mr["treeroute_top3"])
oh = mr["own_history_share_treeroute"]
for line in REP:
    if line.startswith("| fire | treeroute top 3 |"):
        print("fire top3 report:", line.split("|")[4].strip(), "| A:", t3)
    if line.startswith("| fire | own-history share, treeroute |"):
        print("fire own report:", line.split("|")[4].strip(), "| A:", iv4(oh), "n=%s" % oh["n_finite"])
# official fire main row keys (to confirm the cells are absent)
print("official fire AW4_main_row keys:", sorted(OFF["fire"].keys()))

# B1 family table
FAM = ("own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal")
for line in REP:
    m = re.match(r"\| (fire|pm25|ndvi) \| (normal .+?) \| (.+?) \| (.+?) \|$", line)
    if not m:
        continue
    p = m.group(1)
    b = A["b1"][p]["variable"]
    t3 = ", ".join("%s %s" % (n, f3(s)) for n, s in b["top3"])
    fam = b["families"]
    sh = fam.get("shares", fam)
    fs = " / ".join(f3(sh[k]["value"]) for k in FAM)
    o = b["own_history_share"]
    os_ = "%s [%s, %s]" % (f3(o["value"]), f3(o["ci_low"]), f3(o["ci_high"]))
    for nm, e, g in (("top3", t3, m.group(2)), ("families", fs, m.group(3)), ("own", os_, m.group(4))):
        ok = e == g
        bad += not ok
        print("B1 %-5s %-9s %s" % (p, nm, "ok" if ok else "DIFF report=%s A=%s" % (g, e)))
print("differences:", bad)
