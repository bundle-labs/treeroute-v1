# Implementer B: compact view of my own work\b1.json (my numbers only).
import json

r = json.load(open(r"D:\treeroute\analysis\shap_v1\verify_v1\B\work\b1.json", encoding="utf-8"))


def iv(d):
    if d is None:
        return "null"
    f = lambda x: "None" if x is None else ("%.4g" % x)
    return "%s [%s, %s] n=%s" % (f(d["value"]), f(d["ci_low"]), f(d["ci_high"]), d["n_finite"])


for p, e in r.items():
    print("=" * 10, p)
    s = dict(e["status"])
    print(" status:", {k: v for k, v in s.items() if k not in ("meta",)})
    print(" meta:", s.get("meta"))
    if "identity" in e:
        print(" identity:", {k: v for k, v in e["identity"].items()})
    if "run" in e:
        print(" run:", e["run"])
        for L in ("feature", "variable"):
            x = e[L]
            imp = x["importance"]
            print("  [%s] nnz %s before-merge %s extra %s" % (L, iv(imp["n_nonzero"]), iv(imp.get("n_nonzero_before_merge")), imp.get("extra")))
            print("   top10", [(t[0], round(t[1], 4)) for t in x["top10"]])
            pb = x["pair_main_b1"]
            print("   pair J", len(pb["J"]), "extra", pb["extra"])
            for k in ("spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "jaccard_top20",
                      "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement", "sign_n_determined", "sign_n_agree"):
                print("     %-22s %s" % (k, iv(pb[k]) if pb[k] is not None else "null: " + pb.get(k + "_why", "")))
            if L == "variable":
                print("   families", {f: iv(v) for f, v in x["families"].items()})
                print("   top3", x["top3"], "own", iv(x["own_history_share"]))
                print("   main families", x["extra"]["main_family_shares_full_sample"])
