"""n10: the reconciler's section-6 B1 tables against A's results.json at 3 decimals (single rounding), to confirm
that exactly the four cells named in A1 item 4 are wrong (lead's note: 'four cells'). Read-only; prints only."""
import json
import re
from decimal import Decimal, ROUND_HALF_EVEN

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
A = json.load(open(V + r"\A\results.json", encoding="utf-8"))["b1"]
rep = open(V + r"\reconcile\report.md", encoding="utf-8").read()
s6 = rep[rep.index("## 6. Treeroute's B1 sensitivity"):rep.index("## 7. Files written by the reconciler")]


def r3(x):
    return format(Decimal(x).quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN), "f")


def nums(s):
    return re.findall(r"-?\d+\.\d+|-?\d+", s)


rows = [l for l in s6.split("\n") if l.startswith("| fire,") or l.startswith("| pm25,") or l.startswith("| ndvi,")]
cols = ["pair J", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard", "rbo", "tv_shares",
        "tv_family_shares", "sign"]
wrong = []
checked = 0
for l in rows:
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    p, lev = [x.strip() for x in c[0].split(",")]
    pr = A[p][lev]["pair_main_b1"]
    got = dict(zip(cols, c[1:]))

    def iv(e):
        return "%s [%s, %s]" % (r3(e["value"]), r3(e["ci_low"]), r3(e["ci_high"]))

    exp = {"pair J": str(int(pr["n_J"]["value"])),
           "spearman_J": iv(pr["spearman_J"]),
           "spearman_top20_union": iv(pr["spearman_top20_union"]),
           "kendall_tau_b": iv(pr["kendall_tau_b"]),
           "jaccard": "%s / %s" % (r3(pr["jaccard_top5"]["value"]), r3(pr["jaccard_top10"]["value"])) + (
               " (%s)" % r3(pr["jaccard_top20"]["value"]) if pr.get("jaccard_top20") else ""),
           "rbo": "%s / %s" % (r3(pr["rbo_p090"]["value"]), r3(pr["rbo_p095"]["value"])),
           "tv_shares": iv(pr["tv_shares"])}
    for k, v in exp.items():
        checked += 1
        if got[k] != v:
            wrong.append((p, lev, k, got[k], v))
    # family-share distance and sign agreement, checked by numbers
    fam = got["tv_family_shares"]
    if lev == "variable":
        checked += 1
        if fam != iv(pr["tv_family_shares"]):
            wrong.append((p, lev, "tv_family_shares", fam, iv(pr["tv_family_shares"])))
    sg = got["sign"]
    sa = pr["sign_agreement"]
    n_det = int(pr["sign_n_determined"]["value"])
    checked += 1
    print("  %s %s sign cell %r | A %r [%r, %r] determined %d" % (p, lev, sg, sa["value"], sa["ci_low"], sa["ci_high"],
                                                                   n_det))
print("section-6 pair cells checked:", checked)
print("wrong cells:", len(wrong))
for w in wrong:
    print("  ", w)

# second table: top 3, family shares, own-history share
rows2 = [l for l in s6.split("\n") if re.match(r"^\| (fire|pm25|ndvi) \| normal", l)]
fam_keys = ["own_history", "global_indices", "local_drivers", "context_and_calendar", "seasonal_normal"]
wrong2 = []
for l in rows2:
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    p = c[0]
    t3 = ", ".join("%s %s" % (n, r3(s)) for n, s in A[p]["variable"]["top3"])
    fams = " / ".join(r3(A[p]["variable"]["families"][k]["value"]) for k in fam_keys)
    oh = A[p]["variable"]["own_history_share"]
    ohs = "%s [%s, %s]" % (r3(oh["value"]), r3(oh["ci_low"]), r3(oh["ci_high"]))
    for g, e, lab in ((c[1], t3, "top3"), (c[2], fams, "families"), (c[3], ohs, "own history")):
        if g != e:
            wrong2.append((p, lab, g, e))
print("second table rows:", len(rows2), "wrong:", wrong2)

# nonzero-count table vs A and meta (extra)
for p in ("fire", "pm25", "ndvi"):
    fi = A[p]["feature"]["importance"]
    vi = A[p]["variable"]["importance"]
    print(p, "n_nonzero_before_merge", fi["n_nonzero_before_merge"]["value"], "n_nonzero(feature)",
          fi["n_nonzero"]["value"], "meta players_nonzero", fi["extra"].get("meta_players_nonzero"),
          "variable n_nonzero", vi["n_nonzero"]["value"], "meta variables_nonzero",
          fi["extra"].get("meta_variables_nonzero"))
