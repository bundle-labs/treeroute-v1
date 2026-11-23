# Implementer B: print a compact view of my own work\problems.json (my numbers only; no official output is read).
import json
import sys

r = json.load(open(r"D:\treeroute\analysis\shap_v1\verify_v1\B\work\problems.json", encoding="utf-8"))


def iv(d):
    if d is None:
        return "null"
    f = lambda x: "None" if x is None else ("%.4g" % x)
    return "%s [%s, %s] n=%s" % (f(d["value"]), f(d["ci_low"]), f(d["ci_high"]), d["n_finite"])


for p in (sys.argv[1:] or list(r)):
    pr = r[p]
    print("=" * 20, p)
    for L in ("feature", "variable"):
        lv = pr["levels"][L]
        a = lv["active_set"]
        print(" [%s] nJ %d, zeros %s, extra %s" % (L, a["n_J"]["value"], a["structural_zeros"], a["extra"]))
        for m, e in lv["models"].items():
            print("   %-20s nnz %s meta %s | top3 %s" % (m, iv(e["n_nonzero"]), e["extra"]["meta_nonzero"],
                                                    [(t[0], round(t[1], 4)) for t in e["top10"][:3]]))
            if "family_shares" in e:
                print("       fam", {f: round(v["value"], 4) for f, v in e["family_shares"].items()})
        for k, e in lv["pairs"].items():
            print("   %-34s %-10s sJ %s | s20 %s | tau %s | rbo9 %s | tv %s | sign %s (%s/%s)" % (
                k, e["link_class"], iv(e["spearman_J"]), iv(e["spearman_top20_union"]), iv(e["kendall_tau_b"]),
                iv(e["rbo_p090"]), iv(e["tv_shares"]), iv(e["sign_agreement"]),
                e["sign_n_agree"]["value"], e["sign_n_determined"]["value"]))
        pp = lv["per_problem"]
        print("   W %s m=%s n=%s | mean sp %s | extra %s" % (iv(pp["kendall_w"]), pp["kendall_w_m"], pp["kendall_w_n"],
                                                      iv(pp["mean_pairwise_spearman"]),
                                                      {k: v for k, v in pp["extra"].items() if k != "stability_replicates"}))
        print("   stability", {m: round(v["value"], 4) for m, v in pp["stability"].items()})
    mr = pr["main_row"]
    print(" main row:", {k: (iv(v) if isinstance(v, dict) and "value" in v else v) for k, v in mr.items() if k != "consensus_shares"})
    nz = pr["nonzero_forecast"]
    print(" nonzero:", nz["models_covered"], {m: (e["rows_used"], e["regions_used"], [(t[0], round(t[1], 4)) for t in e["top10"][:3]]) for m, e in nz["models"].items()})
    if "families" in pr["levels"]["variable"]:
        print(" global indices:", pr["levels"]["variable"]["families"]["global_indices"])
