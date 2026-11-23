"""Read-only: print A's and B's B1 numbers (pair statistics with intervals, families, top 3, own-history share,
top 10 names) to check report.md section 6 against them. Compact output."""
import json

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
R = {}
for X in ("A", "B"):
    with open(V + "\\" + X + "\\results.json", encoding="utf-8") as f:
        R[X] = json.load(f)

STATS = ("n_J", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "jaccard_top20",
         "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement", "sign_n_determined", "sign_n_agree")


def fmt(x):
    if isinstance(x, float):
        return "%.4f" % x
    return str(x)


def iv(o):
    if isinstance(o, dict) and "value" in o:
        s = fmt(o.get("value"))
        if "ci_low" in o:
            s += " [%s, %s]" % (fmt(o.get("ci_low")), fmt(o.get("ci_high")))
        if "n_finite" in o:
            s += " n=%s" % o.get("n_finite")
        return s
    if o is None:
        return "None"
    return json.dumps(o)[:120]


for p in ("fire", "pm25", "ndvi"):
    for lev in ("feature", "variable"):
        for X in ("A", "B"):
            b = R[X]["b1"][p][lev]
            pr = b.get("pair_main_b1", {})
            print("==", X, p, lev)
            for k in STATS:
                if k in pr:
                    print("    %-22s %s" % (k, iv(pr[k])))
            if "jaccard_top20_why" in pr:
                print("    jaccard_top20_why", str(pr["jaccard_top20_why"])[:120])
            if lev == "variable":
                fam = b.get("families")
                if isinstance(fam, dict):
                    sh = fam.get("shares", fam)
                    if isinstance(sh, dict):
                        for kk, vv in sh.items():
                            print("    family %-22s %s" % (kk, iv(vv)))
                    else:
                        print("    families", json.dumps(fam)[:300])
                t3 = b.get("top3")
                print("    top3", json.dumps(t3)[:300])
                print("    own_history_share", iv(b.get("own_history_share")))
            t10 = b.get("top10")
            if isinstance(t10, dict):
                print("    top10 names", t10.get("names"))
                print("    top10 shares", [round(x, 4) if isinstance(x, float) else x for x in (t10.get("shares") or [])])
            else:
                print("    top10", json.dumps(t10)[:300])
            imp = b.get("importance", {})
            for k in ("n_nonzero", "n_nonzero_before_merge"):
                if k in imp:
                    print("    imp.%s %s" % (k, iv(imp[k])))
