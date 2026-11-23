# Round 14, implementer A: short summary of V\A\work\b1.json (own numbers only).
import json, os

V_A = r"D:\treeroute\analysis\shap_v1\verify_v1\A"


def iv(o):
    if o is None:
        return "null"
    v = o["value"]
    s = "%.6g" % v if v is not None else "null"
    if o.get("ci_low") is not None:
        s += " [%.4g, %.4g] n=%d" % (o["ci_low"], o["ci_high"], o["n_finite"])
    return s


with open(os.path.join(V_A, "work", "b1.json"), "r", encoding="utf-8") as fh:
    r = json.load(fh)
for p, d in r.items():
    st = d["status"]
    print("==", p, "numbers", st["numbers"], "| finished", st["finished"], "| meta", {k: st["meta"][k] for k in ("pass", "background", "pairs", "trees_used")} if st["meta"] else None)
    if "run" in d:
        print("   run", {k: v for k, v in d["run"].items() if k != "npz"})
        for L in ("feature", "variable"):
            lv = d[L]
            imp = lv["importance"]
            pr = lv["pair_main_b1"]
            print("  ", L, "nz", iv(imp["n_nonzero"]), "before", iv(imp.get("n_nonzero_before_merge")), "meta", imp["extra"]["meta_players_nonzero"], imp["extra"]["meta_variables_nonzero"])
            print("     top10", [(t[0], round(t[1], 4)) for t in lv["top10"]])
            print("     J", len(pr["J"]), "zero-in-main", pr["extra"]["J_players_exactly_zero_in_main"])
            for k in ("spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "jaccard_top20", "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement", "sign_n_determined", "sign_n_agree"):
                print("       %-22s %s" % (k, iv(pr.get(k))))
            if L == "variable":
                print("     families", {f: iv(v) for f, v in lv["families"].items() if not f.endswith("_why") and f != "extra"})
                print("     main fam", lv["families"]["extra"])
                print("     top3", lv["top3"], "own hist", iv(lv["own_history_share"]))
    if "identity" in d:
        print("   identity", {k: v for k, v in d["identity"].items() if k != "extra"})
