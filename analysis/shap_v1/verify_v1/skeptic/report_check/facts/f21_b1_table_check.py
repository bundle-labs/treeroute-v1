import json, re
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))
B = json.load(open(V + r"\B\results.json", encoding="utf-8"))
lines = open(V + r"\reconcile\report.md", encoding="utf-8").read().splitlines()

def r3(x):
    s = "%.3f" % x
    return s

def ivs(o):
    return f"{r3(o['value'])} [{r3(o['ci_low'])}, {r3(o['ci_high'])}]"

bad = []
for ln_no in range(337, 343):  # report lines 338-343 (0-based 337..342)
    ln = lines[ln_no]
    cells = [c.strip() for c in ln.strip().strip("|").split("|")]
    pl = cells[0]
    p, lev = [x.strip() for x in pl.split(",")]
    pa = A["b1"][p][lev]["pair_main_b1"]
    exp = {
        1: str(int(pa["n_J"]["value"])),
        2: ivs(pa["spearman_J"]),
        3: ivs(pa["spearman_top20_union"]),
        4: ivs(pa["kendall_tau_b"]),
        6: f"{r3(pa['rbo_p090']['value'])} / {r3(pa['rbo_p095']['value'])}",
        7: ivs(pa["tv_shares"]),
    }
    j5 = f"{r3(pa['jaccard_top5']['value'])} / {r3(pa['jaccard_top10']['value'])}"
    if pa.get("jaccard_top20"):
        j5 += f" ({r3(pa['jaccard_top20']['value'])})"
    exp[5] = j5
    for i, e in exp.items():
        got = cells[i]
        if got != e:
            bad.append((ln_no + 1, p, lev, i, got, e))
    print(ln_no + 1, cells[0], "| fam:", cells[8], "| sign:", cells[9])
    # family-share distance and sign
    pb = B["b1"][p][lev]["pair_main_b1"]
    fa = pa.get("tv_family_shares"); fb = pb.get("tv_family_shares")
    print("    fam A", ivs(fa) if fa else None, "B", ivs(fb) if fb else None, "| sign A", ivs(pa["sign_agreement"]), "n_det", pa["sign_n_determined"]["value"])
for b in bad:
    print("MISMATCH line", b)
# second table lines 347-349
for ln_no in range(346, 349):
    ln = lines[ln_no]
    cells = [c.strip() for c in ln.strip().strip("|").split("|")]
    p = cells[0]
    va = A["b1"][p]["variable"]
    top = ", ".join(f"{n} {r3(s)}" for n, s in va["top3"])
    fams = " / ".join(r3(va["families"][f]["value"]) for f in ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"])
    oh = ivs(va["own_history_share"])
    for got, e, what in ((cells[1], top, "top3"), (cells[2], fams, "families"), (cells[3], oh, "own")):
        print(ln_no + 1, p, what, "OK" if got == e else f"MISMATCH got={got!r} exp={e!r}")
