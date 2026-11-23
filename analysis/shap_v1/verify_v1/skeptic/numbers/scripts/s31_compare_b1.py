"""Skeptic (numbers lens): my B1 numbers beside A's and B's (no official B1 output exists)."""
import os, json
V = r"D:\treeroute\analysis\shap_v1\verify_v1"
OUT = os.path.join(V, "skeptic", "numbers", "work")
A = json.load(open(os.path.join(V, "A", "results.json"), encoding="utf-8"))["b1"]
B = json.load(open(os.path.join(V, "B", "results.json"), encoding="utf-8"))["b1"]
ME = json.load(open(os.path.join(OUT, "s20_b1.json"), encoding="utf-8"))
lines = []


def show(key, mine, a, b):
    flag = ""
    for x in (a, b):
        if isinstance(mine, (int, float)) and isinstance(x, (int, float)):
            if abs(mine - x) > 1e-9 * max(1.0, abs(mine)):
                flag = "  <-- DIFF"
        elif mine != x:
            flag = "  <-- DIFF"
    s = "%s | mine %r | A %r | B %r%s" % (key, mine, a, b, flag)
    lines.append(s)
    print(s)


di = ME["defo_identity"]
for X, nm in [(A, "A"), (B, "B")]:
    pass
ai, bi = A["defo"]["identity"], B["defo"]["identity"]
show("defo/identity/max_abs_diff_phi", di["max_abs_diff_phi"], ai.get("max_abs_diff_phi"), bi.get("max_abs_diff_phi"))
show("defo/identity/max_abs_diff_phiv", di["max_abs_diff_phiv"], ai.get("max_abs_diff_phiv"), bi.get("max_abs_diff_phiv"))
show("defo/identity/same_rows", di["same_rows"], ai.get("same_rows"), bi.get("same_rows"))
show("defo/identity/same_players", di["same_phi_names"], ai.get("same_players"), bi.get("same_players"))
show("defo/identity/same_variables", di["same_phiv_names"], ai.get("same_variables"), bi.get("same_variables"))
show("defo/identity/n_players", di["n_phi_main"], ai.get("n_players_main"), bi.get("n_players_main"))
show("defo/identity/n_variables", di["n_phiv_main"], ai.get("n_variables_main"), bi.get("n_variables_main"))
show("defo/identity/pairs_meta_b1", di["meta_treeroute_B1"]["pairs"], ai.get("pairs_meta"), bi.get("pairs_meta"))
show("defo/identity/tree_shap_seconds_meta", di["meta_treeroute_B1"]["tree_shap_seconds"], ai.get("tree_shap_seconds_meta"),
     bi.get("tree_shap_seconds_meta"))
show("defo/identity/as_expected", True, ai.get("as_expected"), bi.get("as_expected"))
for level in ["variable", "feature"]:
    me = ME["fire_b1_" + level]
    ap = A["fire"][level]["pair_main_b1"]
    bp = B["fire"][level]["pair_main_b1"]
    show("fire/%s/pair/n_J" % level, me["J_n"], ap["n_J"]["value"], bp["n_J"]["value"])
    show("fire/%s/pair/J_size_listed" % level, me["J_n"], len(ap["J"]), len(bp["J"]))
    for st in ["spearman_J", "tv_shares", "spearman_top20_union", "rbo_p090"]:
        for k in ["value", "ci_low", "ci_high", "n_finite"]:
            show("fire/%s/pair/%s/%s" % (level, st, k), me[st][k], ap[st][k], bp[st][k])
    at = [x[0] for x in A["fire"][level]["top10"]]
    bt = [x[0] for x in B["fire"][level]["top10"]]
    show("fire/%s/b1_top10/names" % level, [x[0] for x in me["b1_top10"]], at, bt)
    for i in range(10):
        show("fire/%s/b1_top10/share%d" % (level, i), me["b1_top10"][i][1], A["fire"][level]["top10"][i][1],
             B["fire"][level]["top10"][i][1])
    if level == "variable":
        for k in ["value", "ci_low", "ci_high", "n_finite"]:
            show("fire/variable/pair/tv_family_shares/" + k, me["tv_family_shares"][k], ap["tv_family_shares"][k],
                 bp["tv_family_shares"][k])
            show("fire/variable/own_history_share/" + k, me["b1_own_history_share"][k], A["fire"]["variable"]["own_history_share"][k],
                 B["fire"]["variable"]["own_history_share"][k])
        for f, v in me["b1_family_shares"].items():
            show("fire/variable/families/%s/value" % f, v, A["fire"]["variable"]["families"][f]["value"],
                 B["fire"]["variable"]["families"][f]["value"])
        show("fire/variable/top3/names", [x[0] for x in me["b1_top3"]], [x[0] for x in A["fire"]["variable"]["top3"]],
             [x[0] for x in B["fire"]["variable"]["top3"]])
open(os.path.join(OUT, "s31_compare_b1.out.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("differences:", sum(1 for s in lines if "DIFF" in s), "of", len(lines))
