# Round 14, implementer A: print a short summary of V\A\work\items_<p>.json (own numbers only).
import json, os, sys

V_A = r"D:\treeroute\analysis\shap_v1\verify_v1\A"


def iv(o):
    if o is None:
        return "null"
    v = o["value"]
    s = "%.6g" % v if v is not None else "null"
    if o.get("ci_low") is not None:
        s += " [%.4g, %.4g] n=%d" % (o["ci_low"], o["ci_high"], o["n_finite"])
    return s


def main(p):
    with open(os.path.join(V_A, "work", "items_%s.json" % p), "r", encoding="utf-8") as fh:
        r = json.load(fh)
    print("==", p, "sha match", r["draws"]["sha256_match"], "G", len(r["draws"]["regions_in_draw_order"]))
    for L in ("feature", "variable"):
        lv = r["levels"][L]
        a = lv["active_set"]
        print(" ", L, "J", len(a["J"]), "structural zeros", a["structural_zeros"][:12], a["extra"]["n_J_if_recomputed_per_draw"])
        for m, e in lv["models"].items():
            x = e["extra"]
            print("    %-20s nz %s (meta %s/%s, own %d, overJ %d) det %d top3 %s" % (
                m, iv(e["n_nonzero"]), x["meta_players_nonzero"], x["meta_variables_nonzero"], x["own_columns"],
                x["n_nonzero_over_J"], x["sign_determined_count"], [(t[0], round(t[1], 4)) for t in e["top10"][:3]]))
            if L == "variable":
                print("        fam", {f: (iv(v) if v else None) for f, v in e["family_shares"].items() if not f.endswith("_why")})
        pp = lv["per_problem"]
        print("    W", iv(pp["kendall_w"]), "mps", iv(pp["mean_pairwise_spearman"]))
        print("    stability", {m: (round(v["value"], 4) if v and v["value"] is not None else None) for m, v in pp["stability"].items() if not m.endswith("_why")})
        for k, d in lv["pairs"].items():
            print("    %-36s %-10s rhoJ %s | u20 %s | tau %s | j5 %s j10 %s j20 %s | rbo9 %s | tv %s | tvf %s | sign %s n %s" % (
                k, d["link_class"], iv(d["spearman_J"]), iv(d["spearman_top20_union"]), iv(d["kendall_tau_b"]),
                iv(d["jaccard_top5"]), iv(d["jaccard_top10"]), iv(d["jaccard_top20"]), iv(d["rbo_p090"]),
                iv(d["tv_shares"]), iv(d["tv_family_shares"]), iv(d["sign_agreement"]), iv(d["sign_n_determined"])))
    mr = r["main_row"]
    print("  main row:", json.dumps({k: (iv(v) if isinstance(v, dict) and "value" in v else v) for k, v in mr.items() if k not in ("consensus_shares", "extra")})[:3000])
    nz = r["nonzero_forecast"]
    print("  nonzero_forecast covered", nz["models_covered"])
    for m, e in nz["models"].items():
        print("    ", m, "rows", e["rows_used"], "regions", e["regions_used"], "nz", iv(e["n_nonzero"]), "top3", [(t[0], round(t[1], 4)) for t in e["top10"][:3]])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
