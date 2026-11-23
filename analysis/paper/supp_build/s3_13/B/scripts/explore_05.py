# Exploration only (builder B): the results.json objects the spec names, compactly. Writes nothing.
import sys, json, os
sys.stdout.reconfigure(encoding="utf-8")

V = r"D:\treeroute\analysis\shap_v1\verify_v1"
with open(os.path.join(V, "A", "results.json"), "r", encoding="utf-8") as f:
    A = json.load(f)


def c(o, n=300):
    s = json.dumps(o, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + " ..."


mr = A["problems"]["fire"]["main_row"]
print("fire main_row keys", list(mr.keys()))
print("  treeroute_top3", c(mr.get("treeroute_top3")))
print("  own_history_share_treeroute", c(mr.get("own_history_share_treeroute")))
for k, v in mr.items():
    if k not in ("treeroute_top3", "own_history_share_treeroute"):
        print("  ", k, "=", c(v, 200))
for q in ["coral", "defo", "fire", "pm25", "ndvi"]:
    b = A["b1"][q]
    print("== b1", q, "keys", list(b.keys()))
    st = b["status"]
    print("   status keys", list(st.keys()) if isinstance(st, dict) else st)
    print("   status.numbers", st.get("numbers") if isinstance(st, dict) else None)
    if "run" in b:
        print("   run", c(b["run"], 600))
    if "identity" in b:
        print("   identity", c(b["identity"], 1500))
    for L in ("variable", "feature"):
        if L not in b:
            continue
        bl = b[L]
        print("   ", L, "keys", list(bl.keys()))
        if "pair_main_b1" in bl:
            print("      pair_main_b1 keys", list(bl["pair_main_b1"].keys()))
            for kk in ["n_J", "spearman_J", "spearman_top20_union", "kendall_tau_b", "jaccard_top5", "jaccard_top10", "jaccard_top20", "rbo_p090", "rbo_p095", "tv_shares", "tv_family_shares", "sign_agreement", "sign_n_determined", "sign_n_agree"]:
                print("        %s = %s" % (kk, c(bl["pair_main_b1"].get(kk, "<<MISSING>>"), 200)))
        if "importance" in bl:
            imp = bl["importance"]
            print("      importance keys", list(imp.keys())[:12])
            print("      importance.n_nonzero", c(imp.get("n_nonzero")))
        for kk in ["top10", "top3", "own_history_share"]:
            if kk in bl:
                print("      %s = %s" % (kk, c(bl[kk], 900)))
        if "families" in bl:
            print("      families keys", list(bl["families"].keys()))
            for fk, fv in bl["families"].items():
                print("        families.%s = %s" % (fk, c(fv, 200)))
