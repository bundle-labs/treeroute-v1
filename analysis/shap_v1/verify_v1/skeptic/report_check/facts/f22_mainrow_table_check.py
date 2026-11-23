import json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
SHAP = r"D:\treeroute\analysis\shap_v1"
lines = open(V + r"\reconcile\report.md", encoding="utf-8").read().splitlines()
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
f4 = lambda x: "%.4f" % x

def civ(o):
    return f"{f4(o['value'])} [{f4(o['ci'][0])}, {f4(o['ci'][1])}]"

def civ0(o):  # zero printed as 0
    v = [o['value'], o['ci'][0], o['ci'][1]]
    if all(x == 0 for x in v):
        return "0 [0, 0]"
    return civ(o)

out = []
for i in range(125, 148):  # report lines 126-148
    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    p, what, off = cells[0], cells[1], cells[2]
    O = json.load(open(SHAP + "\\out\\" + p + r"\lead_0\compare\AW4_main_row.json", encoding="utf-8"))
    if what == "Kendall's W":
        if p == "fire":
            exp = off
        else:
            exp = civ(O["kendall_w"])
    elif what.startswith("median top-20-union"):
        o = O["treeroute_vs_same_link_rivals_median_spearman_top20_union"]
        exp = f"{civ(o)} ({f4(o['range'][0])} to {f4(o['range'][1])})"
    elif what.startswith("RBO"):
        exp = civ(O["rbo_vs_consensus_p0.9"])
    elif what.startswith("treeroute top 3 / consensus"):
        exp = ", ".join(O["treeroute_top3"]) + " / " + ", ".join(O["consensus_top3"])
    elif what.startswith("own-history share, treeroute / median"):
        exp = civ0(O["own_history_share_treeroute"]) + " / " + civ0(O["own_history_share_median_rival"])
    else:
        exp = off
    out.append((i + 1, p, what, "OK" if off == exp else f"MISMATCH got={off!r} exp={exp!r}"))
for o in out:
    print(o)
# fire A values in the table
mr = A["problems"]["fire"]["main_row"]
print("fire top3 A:", [(n, f4(s)) for n, s in mr["treeroute_top3"]])
o = mr["own_history_share_treeroute"]
print("fire own-history A:", f4(o["value"]), f4(o["ci_low"]), f4(o["ci_high"]), o["n_finite"])
print("lines 137-138:", lines[136], "||", lines[137])
